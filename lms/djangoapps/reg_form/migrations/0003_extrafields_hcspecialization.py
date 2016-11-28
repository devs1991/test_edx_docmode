# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hcspecialization', '0001_initial'),
        ('reg_form', '0002_extrafields_user_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='extrafields',
            name='hcspecialization',
            field=models.ForeignKey(to='hcspecialization.hcspecializations', null=True),
        ),
    ]
