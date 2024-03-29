# Generated by Django 2.2 on 2022-08-12 07:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0009_user_is_web_user'),
    ]

    operations = [
        migrations.CreateModel(
            name='EntityError',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entity', models.CharField(max_length=250)),
                ('error_description', models.TextField()),
                ('date', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name_plural': 'Entity Error Logs',
            },
        ),
        migrations.AlterModelOptions(
            name='configuration',
            options={'verbose_name_plural': 'System Configuration'},
        ),
        migrations.AlterModelOptions(
            name='koboconfiguration',
            options={'verbose_name_plural': 'Kobo Configurations'},
        ),
    ]
