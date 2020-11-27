
from datetime import timedelta,datetime
from django.db import connection
from .models import Profile
today = datetime.now().date()


def profiler(request):
    profile = Profile.objects.all()
    return {'profile': profile,}
