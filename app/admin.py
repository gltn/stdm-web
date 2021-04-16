from django.contrib import admin
from .models import *

# Register your models here.
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    pass

@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    pass

    def has_add_permission(self, *args, **kwargs):
        return not Setting.objects.exists()

@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    list_display = ('config_type','config_file','complete')

