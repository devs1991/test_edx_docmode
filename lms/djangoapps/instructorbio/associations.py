"""
Functions for accessing and displaying associations
"""
from datetime import datetime
from collections import defaultdict
from fs.errors import ResourceNotFoundError
import logging

from path import Path as path
import pytz
from django.http import Http404
from django.conf import settings

from edxmako.shortcuts import render_to_response, render_to_string, marketing_link

from organizations import *

from organizations import models as internal

def fetch_organization(organization_id):
    """
    Retrieves a specific organization from app/local state
    Returns a dictionary representation of the object
    """
    organization = {'id': organization_id}
    if not organization_id:
        exceptions.raise_exception("organization", organization, exceptions.InvalidOrganizationException)
    organizations = serializers.serialize_organizations(internal.Organization.objects.filter(active=True))
    if not len(organizations):
        exceptions.raise_exception("organization", organization, exceptions.InvalidOrganizationException)
    return organizations