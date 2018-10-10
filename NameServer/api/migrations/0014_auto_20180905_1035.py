# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2018-09-05 10:35
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0013_auto_20180904_1349'),
    ]

    operations = [
        migrations.AlterField(
            model_name='authentication',
            name='client',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='client', to=settings.AUTH_USER_MODEL, to_field='namespace'),
        ),
        migrations.AlterField(
            model_name='authentication',
            name='expiration',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, editable=False),
        ),
    ]