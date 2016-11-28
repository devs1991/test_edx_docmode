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
from student.models import User,UserProfile,CourseAccessRole
from openedx.core.djangoapps.user_api.errors import UserNotFound, UserNotAuthorized

from opaque_keys.edx.keys import CourseKey, UsageKey
from opaque_keys import InvalidKeyError

from courseware.courses import (
    get_courses,
    get_course,
    get_course_by_id,
    get_permission_for_course_about,
    get_studio_url,
    get_course_overview_with_access,
    get_course_with_access,
    sort_by_announcement,
    sort_by_start_date,
    UserNotEnrolled
)

from openedx.core.djangoapps.theming import helpers as theming_helpers

#from edx_rest_framework_extensions.authentication import JwtAuthentication
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework_oauth.authentication import OAuth2Authentication

# from organizations.models import Organization
# from organizations import serializers

from lang_pref import LANGUAGE_KEY

log = logging.getLogger("edx.courseware")

template_imports = {'urllib': urllib}

# Create your views here.

def index(request):
    from organizations.api import get_organizations

    # org_list = []
    course_discovery_meanings = getattr(settings, 'COURSE_DISCOVERY_MEANINGS', {})

    org_list = get_organizations()

    sorted_assoc_list = sorted(org_list, key=lambda organizations: organizations['name'])

    return render_to_response(
      "associations/associations.html",
      {'organizations': sorted_assoc_list, 'course_discovery_meanings': course_discovery_meanings}
    )

@ensure_csrf_cookie
@cache_if_anonymous()
def association_about(request, organization_id):
    """
    Display the association's about page.
    """
    from organizations.models import Organization, OrganizationCourse, OrganizationSlider
    # from courseware.courses import get_course
    from django.core.exceptions import ObjectDoesNotExist

    data = Organization.objects.get(id=organization_id)

    courses = OrganizationCourse.objects.all().filter(organization_id=organization_id)

    try:
        slider_images = OrganizationSlider.objects.get(organization_id=organization_id)
    except ObjectDoesNotExist:
        slider_images = None

    if slider_images is None:
        sep_images = 'http://www.gettyimages.pt/gi-resources/images/Homepage/Hero/PT/PT_hero_42_153645159.jpg'
    else:
        sep_images = slider_images.image_s3_urls

    imgs = sep_images.split(',')
    no_of_slides = len(imgs)
    
    context = {
        'association_id': data.id,
        'assoc_name': data.name,
        'assoc_short_name': data.short_name,
        'assoc_description': data.description,
        'courses': courses,
        'slider_images': imgs,
        'no_of_slides': no_of_slides
    }

    return render_to_response('associations/association_about.html', context)

def course_det(courseId):

    course_key = CourseKey.from_string(courseId)

    from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

    course_details = CourseOverview.objects.all().filter(id=course_key).values()

    return course_details

@require_http_methods(['GET'])
def instructor(request, username):
    """Render the profile page for the specified username.

    Args:
        request (HttpRequest)
        username (str): username of user whose profile is requested.

    Returns:
        HttpResponse: 200 if the page was sent successfully
        HttpResponse: 302 if not logged in (redirect to login page)
        HttpResponse: 405 if using an unsupported HTTP method
    Raises:
        Http404: 404 if the specified user is not authorized or does not exist

    Example usage:
        GET /account/profile
    """
    instructor = User.objects.get(username=username)
    
    course_key = CourseAccessRole.objects.all().filter(user_id=instructor.id,role='instructor')
    
    context = {
        'fname': instructor.first_name,
        'lname': instructor.last_name
    }

    return render_to_response('inst_bio/association_about.html', context)