# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reg_form', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='extrafields',
            name='user_type',
            field=models.CharField(default=b'dr', max_length=2, db_index=True, choices=[(b'dr', b'Doctor'), (b'u', b'User'), (b'ms', b'Medical Student'), (b'hc', b'Health Care Proffessional')]),
        ),
    ]
