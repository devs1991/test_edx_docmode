"""
Associations views functions
"""

import json
import logging
import urllib
from collections import OrderedDict

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, AnonymousUser
from django.core.context_processors import csrf
from django.db import transaction
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import redirect
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from rest_framework import status
from edxmako.shortcuts import render_to_response, render_to_string, marketing_link
from util.cache import cache, cache_if_anonymous

from openedx.core.djangoapps.theming import helpers as theming_helpers

#from edx_rest_framework_extensions.authentication import JwtAuthentication
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework_oauth.authentication import OAuth2Authentication
from lang_pref import LANGUAGE_KEY

log = logging.getLogger("edx.courseware")

template_imports = {'urllib': urllib}

# Create your views here.

def index(request):
	from associations import get_organizations
	org_list = []
	course_discovery_meanings = getattr(settings, 'COURSE_DISCOVERY_MEANINGS', {})
	    
	org_list = get_organizations()

	return render_to_response(
		"associations/associations.html",
		{'organizations': org_list, 'course_discovery_meanings': course_discovery_meanings}
	)

def association_about(request, organization_id):
   """
   Display the association's about page.
   """
   from organizations.models import Organization

   data = Organization.objects.get(id=organization_id)

   context = {
       'association_id': data.id,
       'assoc_name': data.name,
       'assoc_short_name': data.short_name,
       'assoc_description': data.description
   }

   return render_to_response('associations/association_about.html', context)