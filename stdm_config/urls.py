from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import *
from stdm_config.views import STDMReader
from django.contrib.auth import views as auth_views


urlpatterns = [  
    path('api/<profile>', ProfileUpdatingView, name='profile_detail'),
    path('profile/api/<profile>', EntityListingUpdatingView, name='profiles_detail'),
    path('<profile>/entity/<entity_name>', EntityDetailView, name='entity_detail'),
    path('summary/<profile>', SummaryUpdatingView, name='summary_detail'),
    
   
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)