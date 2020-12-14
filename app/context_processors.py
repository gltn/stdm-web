
from datetime import timedelta,datetime
from django.db import connection
from .models import Profile, Setting, Entity, ValueList
today = datetime.now().date()


def profiler(request):
    profile = Profile.objects.all()
    return {'profile': profile,}

def settings(request):
    configs = Setting.objects.get(id=1)
    default_profile = configs.default_profile
    return {'configs': configs,'default_profile':default_profile}
