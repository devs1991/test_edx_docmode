"""
Apache WSGI file for LMS

This module contains the WSGI application used for Apache deployment.
It exposes a module-level variable named ``application``.
"""

# Patch the xml libs before anything else.
from safe_lxml import defuse_xml_libs
defuse_xml_libs()

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lms.envs.aws")
os.environ.setdefault("SERVICE_VARIANT", "lms")
os.chdir('/home/docmode/edx-20160414-2/apps/edx/edx-platform')
os.environ.setdefault("MYSQL_UNIX_PORT", "/home/docmode/edx-20160414-2/mysql/tmp/mysql.sock")
os.environ.setdefault("CONFIG_ROOT", "/home/docmode/edx-20160414-2/apps/edx/conf")
os.environ.setdefault("TMPDIR", "/home/docmode/edx-20160414-2/.tmp/")

import lms.startup as startup
startup.run()

# This application object is used by the development server
# as well as any WSGI server configured to use this file.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()  # pylint: disable=invalid-name
