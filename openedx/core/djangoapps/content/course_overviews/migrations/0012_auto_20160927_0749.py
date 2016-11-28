# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('course_overviews', '0011_courseoverview_course_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='courseoverview',
            name='course_type',
            field=models.IntegerField(null=True),
        ),
    ]
