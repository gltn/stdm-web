# Generated by Django 2.2 on 2020-12-14 19:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='setting',
            name='site_name',
            field=models.CharField(default='STDM Web', max_length=20),
        ),
    ]