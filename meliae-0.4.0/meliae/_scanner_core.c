/* Copyright (C) 2009, 2010 Canonical Ltd
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 3 as
 * published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

/* The core of parsing is split into a pure C module, so that we can guarantee
 * that we won't be creating objects in the internal loops.
 */

#include "_scanner_core.h"

#ifndef Py_TYPE
#  define Py_TYPE(o) ((o)->ob_type)
#endif

// %zd is the gcc convention for defining that we are formatting a size_t
// object, windows seems to prefer %ld, though perhaps we need to first check
// sizeof(size_t) ?
#ifdef _WIN32
#  if defined(_M_X64) || defined(__amd64__)
#    define SSIZET_FMT "%ld"
#  else
#    define SSIZET_FMT "%d"
#  endif
#  define snprintf _snprintf
#else
#  define SSIZET_FMT "%zd"
#endif

#if defined(__GNUC__)
#   define inline __inline__
#elif defined(_MSC_VER)
#   define inline __inline
#else
#   define inline
#endif

struct ref_info {
    write_callback write;
    void *data;
    int first;
    PyObject *nodump;
};

void _dump_object_to_ref_info(struct ref_info *info, PyObject *c_obj,
                              int recurse);
#ifdef __GNUC__
static void _write_to_ref_info(struct ref_info *info, const char *fmt_string, ...)
    __attribute__((format(printf, 2, 3)));
#else
static void _write_to_ref_info(struct ref_info *info, const char *fmt_string, ...);
#endif
static PyObject * _get_specials();

/* The address of the last thing we dumped. Stuff like dumping the string
 * interned dictionary will dump the same string 2x in a row. This helps
 * prevent that.
 */
static PyObject *_last_dumped = NULL;
static PyObject *_special_case_dict = NULL;

void
_clear_last_dumped()
{
    _last_dumped = NULL;
}

static Py_ssize_t
_basic_object_size(PyObject *c_obj)
{
    Py_ssize_t size;
    size = c_obj->ob_type->tp_basicsize;
    if (PyType_HasFeature(c_obj->ob_type, Py_TPFLAGS_HAVE_GC)) {
        size += sizeof(PyGC_Head);
    }
    return size;
}


static Py_ssize_t
_var_object_size(PyVarObject *c_obj)
{
    Py_ssize_t num_entries;
    num_entries = PyObject_Size((PyObject *)c_obj);
    if (num_entries < 0) {
        /* This object doesn't support len() */
        num_entries = 0;
        PyErr_Clear();
    }
    return _basic_object_size((PyObject *)c_obj)
            + num_entries * c_obj->ob_type->tp_itemsize;
}

static Py_ssize_t
_object_to_size_with_gc(PyObject *size_obj, PyObject *c_obj)
{
    Py_ssize_t size = -1;

    size = PyInt_AsSsize_t(size_obj);
    if (size == -1) {
        // Probably an error occurred, we don't know for sure, but we might as
        // well just claim that we don't know the size. We *could* check
        // PyErr_Occurred(), but if we are just clearing it anyway...
        PyErr_Clear();
        return -1;
    }
    // There is one trick left. Namely, __sizeof__ doesn't include the
    // GC overhead, so let's add that back in
    if (PyType_HasFeature(Py_TYPE(c_obj), Py_TPFLAGS_HAVE_GC)) {
        size += sizeof(PyGC_Head);
    }
    return size;
}

static Py_ssize_t
_size_of_from__sizeof__(PyObject *c_obj)
{
    PyObject *size_obj = NULL;
    Py_ssize_t size = -1;

    if (PyType_CheckExact(c_obj)) {
        // Types themselves may have a __sizeof__ attribute, but it is the
        // unbound method, which takes an instance
        return -1;
    }
    size_obj = PyObject_CallMethod(c_obj, "__sizeof__", NULL);
    if (size_obj == NULL) {
        // Not sure what happened, but this won't work, it could be a simple
        // attribute error, or it could be something else.
        PyErr_Clear();
        return -1;
    }
    size = _object_to_size_with_gc(size_obj, c_obj);
    Py_DECREF(size_obj);
    return size;
}


static Py_ssize_t
_size_of_list(PyListObject *c_obj)
{
    Py_ssize_t size;
    size = _basic_object_size((PyObject *)c_obj);
    size += sizeof(PyObject*) * c_obj->allocated;
    return size;
}


static Py_ssize_t
_size_of_set(PySetObject *c_obj)
{
    Py_ssize_t size;
    size = _basic_object_size((PyObject *)c_obj);
    if (c_obj->table != c_obj->smalltable) {
        size += sizeof(setentry) * (c_obj->mask + 1);
    }
    return size;
}


static Py_ssize_t
_size_of_dict(PyDictObject *c_obj)
{
    Py_ssize_t size;
    size = _basic_object_size((PyObject *)c_obj);
    if (c_obj->ma_table != c_obj->ma_smalltable) {
        size += sizeof(PyDictEntry) * (c_obj->ma_mask + 1);
    }
    return size;
}


static Py_ssize_t
_size_of_unicode(PyUnicodeObject *c_obj)
{
    Py_ssize_t size;
    size = _basic_object_size((PyObject *)c_obj);
    size += Py_UNICODE_SIZE * c_obj->length;
    return size;
}

static Py_ssize_t
_size_of_from_specials(PyObject *c_obj)
{
    PyObject *special_dict;
    PyObject *special_size_of;
    PyObject *val;
    Py_ssize_t size;

    special_dict = _get_specials();
    if (special_dict == NULL) {
        PyErr_Clear(); // Not sure what happened, but don't propogate it
        return -1;
    }
    special_size_of = PyDict_GetItemString(special_dict,
                                           Py_TYPE(c_obj)->tp_name);
    if (special_size_of == NULL) {
        // if special_size_of is NULL, an exception is *not* set
        return -1;
    } 
    // special_size_of is a *borrowed referenced*
    val = PyObject_CallFunction(special_size_of, "O", c_obj);
    if (val == NULL) {
        return -1;
    }
    size = _object_to_size_with_gc(val, c_obj);
    Py_DECREF(val);
    return size;
}

static Py_ssize_t
_size_of_from_var_or_basic_size(PyObject *c_obj)
{
    /* There are a bunch of types that we know we can check directly, without
     * having to go through the __sizeof__ abstraction. This allows us to avoid
     * the extra intermediate allocations. It is also our final fallback
     * method.
     */

    if (c_obj->ob_type->tp_itemsize != 0) {
        // Variable length object with inline storage
        // total size is tp_itemsize * ob_size
        return _var_object_size((PyVarObject *)c_obj);
    }
    return _basic_object_size(c_obj);
}

Py_ssize_t
_size_of(PyObject *c_obj)
{
    Py_ssize_t size;

    if PyList_Check(c_obj) {
        return _size_of_list((PyListObject *)c_obj);
    } else if PyAnySet_Check(c_obj) {
        return _size_of_set((PySetObject *)c_obj);
    } else if PyDict_Check(c_obj) {
        return _size_of_dict((PyDictObject *)c_obj);
    } else if PyUnicode_Check(c_obj) {
        return _size_of_unicode((PyUnicodeObject *)c_obj);
    } else if (PyTuple_CheckExact(c_obj)
            || PyString_CheckExact(c_obj)
            || PyInt_CheckExact(c_obj)
            || PyBool_Check(c_obj)
            || c_obj == Py_None
            || PyModule_CheckExact(c_obj))
    {
        // All of these implement __sizeof__, but we don't need to use it
        return _size_of_from_var_or_basic_size(c_obj);
    }

    // object implements __sizeof__ so we have to specials first
    size = _size_of_from_specials(c_obj);
    if (size != -1) {
        return size;
    }
    size = _size_of_from__sizeof__(c_obj);
    if (size != -1) {
        return size;
    }
    return _size_of_from_var_or_basic_size(c_obj);
}


static void
_write_to_ref_info(struct ref_info *info, const char *fmt_string, ...)
{
    char temp_buf[1024] = {0};
    va_list args;
    size_t n_bytes;

    va_start(args, fmt_string);
    n_bytes = vsnprintf(temp_buf, 1024, fmt_string, args);
    va_end(args);
    info->write(info->data, temp_buf, n_bytes);
}


static inline void
_write_static_to_info(struct ref_info *info, const char data[])
{
    /* These are static strings, do we need to do strlen() each time? */
    info->write(info->data, data, strlen(data));
}

int
_dump_reference(PyObject *c_obj, void* val)
{
    struct ref_info *info;
    size_t n_bytes;
    char buf[24] = {0}; /* it seems that 64-bit long fits in 20 decimals */

    info = (struct ref_info*)val;
    /* TODO: This is casting a pointer into an unsigned long, which we assume
     *       is 'long enough'. We probably should really be using uintptr_t or
     *       something like that.
     */
    if (info->first) {
        info->first = 0;
        n_bytes = snprintf(buf, 24, "%lu", (unsigned long)c_obj);
    } else {
        n_bytes = snprintf(buf, 24, ", %lu", (unsigned long)c_obj);
    }
    info->write(info->data, buf, n_bytes);
    return 0;
}


int
_dump_child(PyObject *c_obj, void *val)
{
    struct ref_info *info;
    info = (struct ref_info *)val;
    // The caller has asked us to dump self, but no recursive children
    _dump_object_to_ref_info(info, c_obj, 0);
    return 0;
}


int
_dump_if_no_traverse(PyObject *c_obj, void *val)
{
    struct ref_info *info;
    info = (struct ref_info *)val;
    /* Objects without traverse are simple things without refs, and built-in
     * types have a traverse, but they won't be part of gc.get_objects().
     */
    if (Py_TYPE(c_obj)->tp_traverse == NULL
               || (PyType_Check(c_obj)
               && !PyType_HasFeature((PyTypeObject*)c_obj, Py_TPFLAGS_HEAPTYPE)))
    {
        _dump_object_to_ref_info(info, c_obj, 0);
    } else if (!PyType_HasFeature(Py_TYPE(c_obj), Py_TPFLAGS_HAVE_GC)) {
        /* This object is not considered part of the garbage collector, even
         * if it does [not] have a tp_traverse function.
         */
        _dump_object_to_ref_info(info, c_obj, 1);
    }
    return 0;
}


static inline void
_dump_json_c_string(struct ref_info *info, const char *buf, Py_ssize_t len)
{
    Py_ssize_t i;
    char c, *ptr, *end;
    char out_buf[1024] = {0};

    // Never try to dump more than 100 chars
    if (len == -1) {
        len = strlen(buf);
    }
    if (len > 100) {
        len = 100;
    }
    ptr = out_buf;
    end = out_buf + 1024;
    *ptr++ = '"';
    for (i = 0; i < len; ++i) {
        c = buf[i];
        if (c <= 0x1f || c > 0x7e) { // use the unicode escape sequence
            ptr += snprintf(ptr, end-ptr, "\\u00%02x",
                            ((unsigned short)c & 0xFF));
        } else if (c == '\\' || c == '/' || c == '"') {
            *ptr++ = '\\';
            *ptr++ = c;
        } else {
            *ptr++ = c;
        }
    }
    *ptr++ = '"';
    if (ptr >= end) {
        /* Abort somehow */
    }
    info->write(info->data, out_buf, ptr-out_buf);
}

void
_dump_string(struct ref_info *info, PyObject *c_obj)
{
    Py_ssize_t str_size;
    char *str_buf;

    str_buf = PyString_AS_STRING(c_obj);
    str_size = PyString_GET_SIZE(c_obj);

    _dump_json_c_string(info, str_buf, str_size);
}


void
_dump_unicode(struct ref_info *info, PyObject *c_obj)
{
    // TODO: consider writing to a small memory buffer, before writing to disk
    Py_ssize_t uni_size;
    Py_UNICODE *uni_buf, c;
    Py_ssize_t i;
    char out_buf[1024] = {0}, *ptr, *end;

    uni_buf = PyUnicode_AS_UNICODE(c_obj);
    uni_size = PyUnicode_GET_SIZE(c_obj);

    // Never try to dump more than this many chars
    if (uni_size > 100) {
        uni_size = 100;
    }
    ptr = out_buf;
    end = out_buf + 1024;
    *ptr++ = '"';
    for (i = 0; i < uni_size; ++i) {
        c = uni_buf[i];
        if (c <= 0x1f || c > 0x7e) {
            ptr += snprintf(ptr, end-ptr, "\\u%04x",
                            ((unsigned short)c & 0xFFFF));
        } else if (c == '\\' || c == '/' || c == '"') {
            *ptr++ = '\\';
            *ptr++ = (char)c;
        } else {
            *ptr++ = (char)c;
        }
    }
    *ptr++ = '"';
    if (ptr >= end) {
        /* We should fail here */
    }
    info->write(info->data, out_buf, ptr-out_buf);
}


void 
_dump_object_info(write_callback write, void *callee_data,
                  PyObject *c_obj, PyObject *nodump, int recurse)
{
    struct ref_info info;

    info.write = write;
    info.data = callee_data;
    info.first = 1;
    info.nodump = nodump;
    if (nodump != NULL) {
        Py_INCREF(nodump);
    }
    _dump_object_to_ref_info(&info, c_obj, recurse);
    if (info.nodump != NULL) {
        Py_DECREF(nodump);
    }
}

void
_dump_object_to_ref_info(struct ref_info *info, PyObject *c_obj, int recurse)
{
    Py_ssize_t size;
    int retval;
    int do_traverse;

    if (info->nodump != NULL && 
        info->nodump != Py_None
        && PyAnySet_Check(info->nodump))
    {
        if (c_obj == info->nodump) {
            /* Don't dump the 'nodump' set. */
            return;
        }
        /* note this isn't exactly what we want. It checks for equality, not
         * the exact object. However, for what it is used for, it is often
         * 'close enough'.
         */
        retval = PySet_Contains(info->nodump, c_obj);
        if (retval == 1) {
            /* This object is part of the no-dump set, don't dump the object */
            return;
        } else if (retval == -1) {
            /* An error was raised, but we don't care, ignore it */
            PyErr_Clear();
        }
    }

    if (c_obj == _last_dumped) {
        /* We just dumped this object, no need to do it again. */
        return;
    }
    _last_dumped = c_obj;
    size = _size_of(c_obj);
    _write_to_ref_info(info, "{\"address\": %lu, \"type\": ",
                       (unsigned long)c_obj);
    _dump_json_c_string(info, c_obj->ob_type->tp_name, -1);
    _write_to_ref_info(info, ", \"size\": " SSIZET_FMT, _size_of(c_obj));
    //  HANDLE __name__
    if (PyModule_Check(c_obj)) {
        _write_static_to_info(info, ", \"name\": ");
        _dump_json_c_string(info, PyModule_GetName(c_obj), -1);
    } else if (PyFunction_Check(c_obj)) {
        _write_static_to_info(info, ", \"name\": ");
        _dump_string(info, ((PyFunctionObject *)c_obj)->func_name);
    } else if (PyType_Check(c_obj)) {
        _write_static_to_info(info, ", \"name\": ");
        _dump_json_c_string(info, ((PyTypeObject *)c_obj)->tp_name, -1);
    } else if (PyClass_Check(c_obj)) {
        /* Old style class */
        _write_static_to_info(info, ", \"name\": ");
        _dump_string(info, ((PyClassObject *)c_obj)->cl_name);
    }
    if (PyString_Check(c_obj)) {
        _write_to_ref_info(info, ", \"len\": " SSIZET_FMT, PyString_GET_SIZE(c_obj));
        _write_static_to_info(info, ", \"value\": ");
        _dump_string(info, c_obj);
    } else if (PyUnicode_Check(c_obj)) {
        _write_to_ref_info(info, ", \"len\": " SSIZET_FMT, PyUnicode_GET_SIZE(c_obj));
        _write_static_to_info(info, ", \"value\": ");
        _dump_unicode(info, c_obj);
    } else if (PyBool_Check(c_obj)) {
        if (c_obj == Py_True) {
            _write_static_to_info(info, ", \"value\": \"True\"");
        } else if (c_obj == Py_False) {
            _write_static_to_info(info, ", \"value\": \"False\"");
        } else {
            _write_to_ref_info(info, ", \"value\": %ld", PyInt_AS_LONG(c_obj));
        }
    } else if (PyInt_CheckExact(c_obj)) {
        _write_to_ref_info(info, ", \"value\": %ld", PyInt_AS_LONG(c_obj));
    } else if (PyTuple_Check(c_obj)) {
        _write_to_ref_info(info, ", \"len\": " SSIZET_FMT, PyTuple_GET_SIZE(c_obj));
    } else if (PyList_Check(c_obj)) {
        _write_to_ref_info(info, ", \"len\": " SSIZET_FMT, PyList_GET_SIZE(c_obj));
    } else if (PyAnySet_Check(c_obj)) {
        _write_to_ref_info(info, ", \"len\": " SSIZET_FMT, PySet_GET_SIZE(c_obj));
    } else if (PyDict_Check(c_obj)) {
        _write_to_ref_info(info, ", \"len\": " SSIZET_FMT, PyDict_Size(c_obj));
    } else if (PyFrame_Check(c_obj)) {
    	PyCodeObject *co = ((PyFrameObject*)c_obj)->f_code;
        if (co) {
            _write_static_to_info(info, ", \"value\": ");
            _dump_string(info, co->co_name);
        }
    }
    _write_static_to_info(info, ", \"refs\": [");
    do_traverse = 1;
    if (Py_TYPE(c_obj)->tp_traverse == NULL
        || (Py_TYPE(c_obj)->tp_traverse == PyType_Type.tp_traverse
            && !PyType_HasFeature((PyTypeObject*)c_obj, Py_TPFLAGS_HEAPTYPE)))
    {
        /* Obviously we don't traverse if there is no traverse function. But
         * also, if this is a 'Type' (class definition), then
         * PyTypeObject.tp_traverse has an assertion about whether this type is
         * a HEAPTYPE. In debug builds, this can trip and cause failures, even
         * though it doesn't seem to hurt anything.
         *  See: https://bugs.launchpad.net/bugs/586122
         */
        do_traverse = 0;
    }
    if (do_traverse) {
        info->first = 1;
        Py_TYPE(c_obj)->tp_traverse(c_obj, _dump_reference, info);
    }
    _write_static_to_info(info, "]}\n");
    if (do_traverse && recurse != 0) {
        if (recurse == 2) { /* Always dump one layer deeper */
            Py_TYPE(c_obj)->tp_traverse(c_obj, _dump_child, info);
        } else if (recurse == 1) {
            /* strings and such aren't in gc.get_objects, so we need to dump
             * them when they are referenced.
             */
            Py_TYPE(c_obj)->tp_traverse(c_obj, _dump_if_no_traverse, info);
        }
    }
}

static int
_append_object(PyObject *visiting, void* data)
{
    PyObject *lst;
    lst = (PyObject *)data;
    if (lst == NULL) {
        return -1;
    }
    if (PyList_Append(data, visiting) == -1) {
        return -1;
    }
    return 0;
}
/**
 * Return a PyList of all objects referenced via tp_traverse.
 */
PyObject *
_get_referents(PyObject *c_obj)
{
    PyObject *lst;

    lst = PyList_New(0);
    if (lst == NULL) {
        return NULL;
    }
    if (Py_TYPE(c_obj)->tp_traverse != NULL
        && (Py_TYPE(c_obj)->tp_traverse != PyType_Type.tp_traverse
            || PyType_HasFeature((PyTypeObject *)c_obj, Py_TPFLAGS_HEAPTYPE)))
    {
        Py_TYPE(c_obj)->tp_traverse(c_obj, _append_object, lst);
    }
    return lst;
}

static PyObject *
_get_specials()
{
    if (_special_case_dict == NULL) {
        _special_case_dict = PyDict_New();
    }
    return _special_case_dict;
}

PyObject *
_get_special_case_dict()
{
    PyObject *ret;

    ret = _get_specials();
    Py_XINCREF(ret);
    return ret;
}
