from django.conf import settings
from django.db import models

# Backwards compatible settings.AUTH_USER_MODEL
USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


class ExtraInfo(models.Model):
    """
    This model contains two extra fields that will be saved when a user registers.
    The form that wraps this model is in the forms.py file.
    """
    user = models.OneToOneField(USER_MODEL, null=True)
    
    specialization = models.CharField(
        verbose_name="Specialization",
        max_length=30,
        null=False
    )

    reg_num = models.CharField(
        verbose_name="Regt. Num",
        blank=False, 
        max_length=15,
        null=False
    )