# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0003_userprofile_specialization'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='specialization',
        ),
    ]
