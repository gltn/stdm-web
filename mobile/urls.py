from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from mobile.views import MobileView, MobileEntityDetailView, MobileViewSync, KoboFormView, entity_columns, KoboView, VisualizationView
from django.contrib.auth import views as auth_views
from stdm_config.views import tables


urlpatterns = [
    path('mobile/', MobileView, name='mobile'),
    path('mobile/sync', MobileViewSync, name='mobile_sync'),
    path('mobile/details/<profile_name>/<name>',
         MobileEntityDetailView, name='mobile_entity_detail'),
    path('mobile/entities/<profile_name>/<entity_name>',
         entity_columns, name='mobile_entities'),
    path('mobile/entities/<profile_name>/', tables, name='tables'),
    path('mobile/kobo/', KoboFormView, name='kobo'),
    path('mobile/kobo/submissions/data', KoboView, name='kobodata'),
    path('mobile/kobo/submissions/visualization',
         VisualizationView, name='visuals'),


]
