# Generated by Django 2.2 on 2020-12-14 19:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_auto_20201214_2217'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='setting',
            name='default_profile',
        ),
    ]
