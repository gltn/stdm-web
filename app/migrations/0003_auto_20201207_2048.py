# Generated by Django 2.2 on 2020-12-07 17:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_setting'),
    ]

    operations = [
        migrations.AlterField(
            model_name='setting',
            name='background_color',
            field=models.CharField(default='#fff', max_length=7),
        ),
        migrations.AlterField(
            model_name='setting',
            name='footer_color',
            field=models.CharField(default='#fff', max_length=7),
        ),
        migrations.AlterField(
            model_name='setting',
            name='header_color',
            field=models.CharField(default='#fff', max_length=7),
        ),
        migrations.AlterField(
            model_name='setting',
            name='sidebar_color',
            field=models.CharField(default='#343a40', max_length=7),
        ),
    ]
