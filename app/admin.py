from django.contrib import admin
from .models import *

# Register your models here.
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    pass

@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    pass


@admin.register(UserConfig)
class UserConfigAdmin(admin.ModelAdmin):
    pass

class CodeValueInline(admin.TabularInline):
    model = CodeValue

@admin.register(ValueList)
class ValueListAdmin(admin.ModelAdmin):
    inlines = [
        CodeValueInline,
    ]

@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    pass

@admin.register(EntityRelation)
class EntityRelationAdmin(admin.ModelAdmin):
    pass

@admin.register(Column)
class ColumnAdmin(admin.ModelAdmin):
    pass

@admin.register(SocialTenure)
class SocialTenureAdmin(admin.ModelAdmin):
    pass

@admin.register(Validity)
class ValidityAdmin(admin.ModelAdmin):
    pass

@admin.register(CodeValue)
class CodeValueAdmin(admin.ModelAdmin):
    pass
