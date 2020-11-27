from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import *
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard/map/', MapView.as_view(), name='map'),
    path('', LandingView.as_view(), name='landing'),
    path('profiles/', ProfileListView.as_view(), name='profiles'),
    path('accounts/login/', user_login, name='login'),
    path('accounts/logout/', user_logout, name='logout'),
    path('password_change/',auth_views.PasswordChangeView.as_view(), {'post_change_redirect' : '/password_change/done/'}, name="password_change"), 
    path('password_change/done/',auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    path('password_reset/',  auth_views.PasswordResetView.as_view(), {'post_reset_redirect' : '/password_reset/mailed/'},name="password_reset"),
    path('password_reset/mailed/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password_reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), {'post_reset_redirect' : '/password_reset/complete/'}, name='password_reset_confirm'),
    path('password_reset/complete/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete')
      
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)