"""
A plugin for setuptools to find files under the Mercurial version control
system which uses the Python library by default and falls back to use the
command line programm hg(1).
"""
__version__ = '0.4'
__author__ = 'Jannis Leidel'
__all__ = ['hg_file_finder']

import os
import subprocess
import sys

try:
    from mercurial.__version__ import version
    from mercurial import hg, ui, cmdutil
except:
    hg = None

try:
    from mercurial.repo import RepoError
except:
    try:
        from mercurial.error import RepoError
    except:
        pass

try:
    from distutils import log
except ImportError:
    log = None

OLD_VERSIONS = ('1.0', '1.0.1', '1.0.2')

PY3 = sys.version[0] == "3"

if os.environ.get('HG_SETUPTOOLS_FORCE_CMD', False):
    hg = None


def find_files_with_cmd(dirname="."):
    """
    Use the hg command to recursively find versioned files in dirname.
    """
    try:
        mydir = os.path.abspath(dirname)
        if not os.path.exists(os.path.join(mydir, '.hg')):
            raise Exception('not a mercurial repo')
        proc = subprocess.Popen(['hg', 'locate', '-I', mydir],
                                stdin=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                cwd=dirname)
        stdout, stderr = proc.communicate()
    except:
        # Let's behave a bit nicer and return nothing if something fails.
        return []
    if not PY3:
        output = stdout.splitlines()
    else:
        output = (x.decode('utf-8') for x in stdout.splitlines())
    return output


def find_files_with_lib(dirname):
    """
    Use the Mercurial library to recursively find versioned files in dirname.
    """
    try:
        try:
            repo = hg.repository(ui.ui(), path=dirname)
        except RepoError:
            return
        # tuple of (modified, added, removed, deleted, unknown, ignored, clean)
        modified, added, removed, deleted, unknown = repo.status()[:5]

        # exclude all files that hg knows about, but haven't been added,
        # or have been deleted, removed, or have an unknown status
        excluded = removed + deleted + unknown

        if version in OLD_VERSIONS:
            from mercurial import util
            node = None
            for src, abs, rel, exact in cmdutil.walk(repo, [], {}, node=node,
                                    badmatch=util.always, default='relglob'):
                if src == 'b':
                    continue
                if not node and abs not in repo.dirstate:
                    continue
                if abs in excluded:
                    continue
                yield abs
        else:
            rev = None
            try:
                match = cmdutil.match(repo, [], {}, default='relglob')
            except:
                # Probably mercurial 1.8+
                from mercurial import scmutil
                match = scmutil.match(repo[None], [], {}, default='relglob')

            match.bad = lambda x, y: False
            for abs in repo[rev].walk(match):
                if not rev and abs not in repo.dirstate:
                    continue
                if abs in excluded:
                    continue
                yield abs
    except Exception:
        if log:
            log.warn("Error in setuptools_hg: %s" % sys.exc_info()[1])
        # try calling hg command as a last resort
        find_files_with_cmd(dirname)


def hg_file_finder(dirname="."):
    """
    Find the files in ``dirname`` under Mercurial version control.
    """
    if not dirname:
        dirname = "."
    if hg is None:
        return find_files_with_cmd(dirname)
    return find_files_with_lib(dirname)


if __name__ == "__main__":
    from pprint import pprint

    if len(sys.argv) != 2:
        print("USAGE: %s DIRNAME" % sys.argv[0])
        sys.exit(1)

    pprint(hg_file_finder(sys.argv[1]))
