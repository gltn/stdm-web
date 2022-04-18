from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import *
from django.contrib.auth import views as auth_views


urlpatterns = [  
    path('api/<profile>', ProfileUpdatingView, name='profile_detail'),
    path('profile/api/<profile>', EntityListingUpdatingView, name='profiles_detail'),
    path('<profile_name>/entity/<entity_short_name>', EntityDetailView, name='entity_detail'),
    path('summary/<profile>', SummaryUpdatingView, name='summary_detail'),
    path('<profile_name>/<entity_short_name>/<id>', EntityRecordViewMore, name='fetchstr'),
    path('tables/<table_name>',get_table_columns, name='db_table_columns'),
    path('mobile/data/sync/', MobileSyncDataView, name='mobile_data_sync'),
    path('geojson/profile/<profile_name>/entity/<entity_short_name>/<row_id>', sp_unit_geojson, name='get_entity_geojson_by_id')
   
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)