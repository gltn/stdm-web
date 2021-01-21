import os
from django.shortcuts import render
from django.views.generic import FormView, CreateView, DetailView, ListView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render_to_response, HttpResponseRedirect, render, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy, reverse
from django.template.context_processors import csrf
from django.contrib import messages
from rest_framework import generics
from .models import Profile,Setting, Entity, CodeValue
from django.urls import reverse_lazy
from .serializers import ProfileSerializer
from .forms import SettingForm
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.db import connection
from stdm_config import StdmConfigurationReader, StdmConfiguration
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
# Create your views here.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, 'config/configuration_unicode.xml')
reader = StdmConfigurationReader(CONFIG_PATH)
reader.load()
stdm_config = StdmConfiguration.instance()

class ProfileListView(generics.ListAPIView):
	queryset = Profile.objects.all()
	serializer_class = ProfileSerializer

class DashboardView(LoginRequiredMixin,TemplateView):
	template_name = 'dashboard/index.html'

	def profiletype(self):
		return Profile.objects.all()

class MapView(LoginRequiredMixin,TemplateView):
	template_name = 'dashboard/map.html'

class ImportView(LoginRequiredMixin,TemplateView):
	template_name = 'dashboard/data.html'

@login_required
def SettingsView(request):
	profiles_list = []
	default_profile = None
	configs = None      
	for profile in stdm_config.profiles.values():
		profiles_list.append(profile.name)
	if profiles_list:
		if Setting.objects.exists():
			configs =Setting.objects.all().first()
			if configs:
				if configs.default_profile in profiles_list:
					default_profile = configs.default_profile
				else:
					default_profile = profiles_list[0]
		else:
			configs = Setting.objects.create(default_profile=profiles_list[0])
			configs.save()
			default_profile = configs.default_profile
	return render(request,'dashboard/settings/settings.html', { 'configs':configs,'default_profile':default_profile,'profiles':profiles_list})

class SettingsUpdateView(LoginRequiredMixin,UpdateView):
	form_class = SettingForm
	model = Setting
	template_name = 'dashboard/settings/settings_update.html'
	success_url = reverse_lazy('settings')

	def get_initial(self):
		initial = super(SettingsUpdateView, self).get_initial()
		if self.request.user.is_authenticated:
			setting = Setting.objects.all().first()
			initial.update({'site_name': setting.site_name, 'logo': setting.logo,'header_color': setting.header_color,'background_color': setting.background_color,'sidebar_color': setting.sidebar_color,'footer_color': setting.footer_color,'default_profile': setting.default_profile,})
		return {'initial': initial,'configs':self.object}

	def form_valid(self, form):
		form.save()
		return super(SettingsUpdateView, self).form_valid(form)

	def profileList(self):
		profiles_list = []
		for profile in stdm_config.profiles.values():
			profiles_list.append(profile.name)
		return profiles_list
	def defaultProfile(self):
		configs =Setting.objects.all().first()
		return configs.default_profile


def user_login(request):
	args = {}
	args.update(csrf(request))
	next_page = request.GET.get('next', '/')
	if request.user.is_authenticated:
		return HttpResponseRedirect(next_page)
	if request.method == 'POST':
		username = request.POST.get('username')
		password = request.POST.get('password')
		user = authenticate(username=username, password=password)
		if user:
			if user.is_active:
				if user.is_staff:
					login(request, user)
					# return HttpResponseRedirect('/admin/')
					return HttpResponseRedirect(reverse("dashboard"))
				else:
					login(request, user)
					return HttpResponseRedirect(reverse("dashboard"))
			else:
				# return HttpResponseRedirect(reverse("login"))
				messages.error(request, "Error")        
		else:
			messages.error(request, "Invalid username and password.Try again!")
			return render(request, 'profiles/login.html')

	else:
		return render(request, 'profiles/login.html', {})

@login_required
def user_logout(request):
	logout(request)
	return HttpResponseRedirect('/')

@csrf_exempt
def EntityUpdatingView(request, profile):
	print(profile)
	entity_list = Entity.objects.filter(profile__name=profile)
	print(entity_list)
	return render(request,'dashboard/profile_detail.html', { 'entity_list':entity_list,})


@csrf_exempt
def SummaryUpdatingView(request, profile):
	entity_list = Entity.objects.filter(profile__name=profile)
	# valuelists = Entity.objects.select_related('documentTypeLookup')
	for entity in entity_list:
		data = CodeValue.objects.filter(valueList=entity.documentTypeLookup)
		print(data)
	return render(request,'dashboard/records.html', { 'entity_list':entity_list,'data':data})