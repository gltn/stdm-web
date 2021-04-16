from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from mobile.views import MobileView,MobileEntityDetailView,MobileViewSync
from django.contrib.auth import views as auth_views


urlpatterns = [  
    path('mobile/', MobileView, name='mobile'),
    path('mobile/sync', MobileViewSync, name='mobile_sync'),
    path('mobile/details/<profile_name>/<name>', MobileEntityDetailView, name='mobile_entity_detail'),
]