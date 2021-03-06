# Generated by Django 2.2 on 2020-12-14 11:39

import app.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CodeValue',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(blank=True, max_length=25, null=True)),
                ('value', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Entity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('shortName', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('associative', models.BooleanField()),
                ('supportsDocuments', models.BooleanField()),
            ],
            options={
                'verbose_name_plural': 'Entity',
            },
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField()),
            ],
            options={
                'verbose_name_plural': 'Profiles',
            },
        ),
        migrations.CreateModel(
            name='Validity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('startMinimum', models.DateField()),
                ('startMaximum', models.DateField()),
                ('endMinimum', models.DateField()),
                ('endMaximum', models.DateField()),
            ],
        ),
        migrations.CreateModel(
            name='ValueList',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to='app.Profile')),
            ],
            options={
                'verbose_name_plural': 'ValueLists',
                'unique_together': {('name', 'profile')},
            },
        ),
        migrations.CreateModel(
            name='UserConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'User Config',
            },
        ),
        migrations.CreateModel(
            name='SocialTenure',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('supportsMultipleParties', models.BooleanField()),
                ('party', models.ManyToManyField(related_name='parties', to='app.Entity')),
                ('spatialUnit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.Entity')),
                ('tenureTypeList', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='social_tenure', to='app.CodeValue')),
                ('validity', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='app.Validity')),
            ],
        ),
        migrations.CreateModel(
            name='Setting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('site_name', models.CharField(max_length=20)),
                ('logo', models.ImageField(default='static/dashboard/dist/img/logo.png', upload_to=app.models.upload_logo)),
                ('header_color', models.CharField(default='#fff', max_length=7)),
                ('background_color', models.CharField(default='#fff', max_length=7)),
                ('sidebar_color', models.CharField(default='#343a40', max_length=7)),
                ('footer_color', models.CharField(default='#fff', max_length=7)),
                ('default_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.Profile')),
            ],
            options={
                'verbose_name_plural': 'Site Settings',
            },
        ),
        migrations.CreateModel(
            name='EntityRelation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('child', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='child', to='app.Entity')),
                ('parent', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='parent', to='app.Entity')),
            ],
            options={
                'verbose_name_plural': 'Entity Relation',
            },
        ),
        migrations.AddField(
            model_name='entity',
            name='documentTypeLookup',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='app.ValueList'),
        ),
        migrations.AddField(
            model_name='entity',
            name='profile',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='profiles', to='app.Profile'),
        ),
        migrations.CreateModel(
            name='Column',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('unique', models.BooleanField()),
                ('tip', models.CharField(max_length=255)),
                ('rowindex', models.IntegerField()),
                ('minimum', models.BigIntegerField()),
                ('maximum', models.BigIntegerField()),
                ('index', models.BooleanField()),
                ('searchable', models.BooleanField()),
                ('typeInfo', models.CharField(max_length=255)),
                ('label', models.CharField(max_length=255)),
                ('mandatory', models.BooleanField()),
                ('entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='columns', to='app.Entity')),
            ],
            options={
                'verbose_name_plural': 'Columns',
            },
        ),
        migrations.AddField(
            model_name='codevalue',
            name='valueList',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='codeValue', to='app.ValueList'),
        ),
        migrations.AlterUniqueTogether(
            name='entity',
            unique_together={('name', 'profile')},
        ),
        migrations.AlterUniqueTogether(
            name='codevalue',
            unique_together={('value', 'valueList')},
        ),
    ]
