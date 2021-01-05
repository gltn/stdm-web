from django.contrib import admin
from .models import Chart

# Register your models here.
@admin.register(Chart)
class ChartAdmin(admin.ModelAdmin):
    pass
