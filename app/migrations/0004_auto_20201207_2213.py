# Generated by Django 2.2 on 2020-12-07 19:13

from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('app', '0003_auto_20201207_2048'),
    ]

    operations = [
        migrations.CreateModel(
            name='Configuration',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Entity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('shortName', models.CharField(max_length=100)),
                ('editable', models.BooleanField()),
                ('description', models.TextField(verbose_name=255)),
                ('associative', models.BooleanField()),
                ('supportsDocuments', models.BooleanField()),
            ],
            options={
                'verbose_name_plural': 'Entity',
            },
        ),
        migrations.CreateModel(
            name='ValueList',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField(max_length=255)),
                ('displayName', models.TextField(max_length=255)),
                ('codeValues', django.contrib.postgres.fields.jsonb.JSONField()),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to='app.Profile')),
            ],
            options={
                'verbose_name_plural': 'ValueLists',
            },
        ),
        migrations.CreateModel(
            name='UserConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('config', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='app.Configuration')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='EntityRelation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('parentColumn', models.CharField(max_length=100)),
                ('childColumn', models.CharField(max_length=100)),
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
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.ValueList'),
        ),
        migrations.AddField(
            model_name='entity',
            name='profile',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='profiles', to='app.Profile'),
        ),
        migrations.AddField(
            model_name='profile',
            name='configuration',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='configuration', to='app.Configuration'),
        ),
    ]
