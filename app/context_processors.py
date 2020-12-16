
import os
from datetime import timedelta,datetime
from django.db import connection
from .models import Setting
from django.shortcuts import get_object_or_404 
from stdm_config import StdmConfigurationReader, StdmConfiguration
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from stdm_config.create_model import create_model
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
today = datetime.now().date()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, 'config/default_configuration.xml')

def settings(request):
    reader = StdmConfigurationReader(CONFIG_PATH)
    reader.load()
    stdm_config = StdmConfiguration.instance()
    profiles = []       
    for profile in stdm_config.profiles.values():
        profiles.append(profile.name)
    if Setting.objects.exists():
        configs =Setting.objects.all().first()
        if configs:
            default_profile = configs.default_profile
    else:
        configs = Setting.objects.create(default_profile=profiles[0])
        configs.save()
        default_profile = configs.default_profile
    return {'configs': configs,'default_profile':default_profile}
