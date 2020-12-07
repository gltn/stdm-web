from django.contrib import admin
from .models import *

# Register your models here.
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    pass

@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    pass

@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    pass

@admin.register(UserConfig)
class UserConfigAdmin(admin.ModelAdmin):
    pass

@admin.register(ValueList)
class ValueListAdmin(admin.ModelAdmin):
    pass

@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    pass

@admin.register(EntityRelation)
class EntityRelationAdmin(admin.ModelAdmin):
    pass