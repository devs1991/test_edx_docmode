# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('course_overviews', '0012_auto_20160927_0749'),
    ]

    operations = [
        migrations.AlterField(
            model_name='courseoverview',
            name='course_type',
            field=models.IntegerField(default=b'1'),
        ),
    ]
