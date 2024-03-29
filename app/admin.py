from django.contrib import admin
from .models import *
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import User


class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('content_type', 'user', 'action_time')

admin.site.register(LogEntry, LogEntryAdmin)

@admin.register(EntityError)
class EntityErrorAdmin(admin.ModelAdmin):
    list_display = ('entity', 'date')

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
    # actions = None
    # list_display_links = None
# Register your models here.


# @admin.register(Profile)
# class ProfileAdmin(admin.ModelAdmin):
#     pass


# @admin.register(Setting)
# class SettingAdmin(admin.ModelAdmin):
#     pass

#     def has_add_permission(self, *args, **kwargs):
#         return not Setting.objects.exists()


@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    list_display = ('config_type', 'config_file', 'complete')


@admin.register(KoboConfiguration)
class KoboConfigurationAdmin(admin.ModelAdmin):
    pass


# @admin.register(User)
# class UserAdmin(admin.ModelAdmin):
#     pass
