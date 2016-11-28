from django.conf import settings
from django.db import models
from lms.djangoapps.specialization.models import specializations
from lms.djangoapps.hcspecialization.models import hcspecializations
from django.utils.translation import ugettext_noop
# Backwards compatible settings.AUTH_USER_MODEL
USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


class extrafields(models.Model):
    """
    This model contains two extra fields that will be saved when a user registers.
    The form that wraps this model is in the forms.py file.
    """
    user = models.OneToOneField(USER_MODEL, null=True)

    specialization = models.ForeignKey(specializations)

    hcspecialization = models.ForeignKey(hcspecializations, null=True)

    reg_num = models.CharField(
        verbose_name="Reg Num",
        max_length=100,
    )

    address = models.CharField(
        verbose_name="address",
        max_length=200,null=True
    )

    USER_TYPE = (
        ('dr', 'Doctor'),
        ('u', 'User'),
        # Translators: 'Other' refers to the student's gender
        ('ms', 'Medical Student'),
        ('hc', 'Health Care Proffessional')
    )
    user_type = models.CharField(
        default='dr', null=False, max_length=2, db_index=True, choices=USER_TYPE
    )
