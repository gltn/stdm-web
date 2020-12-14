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
# Create your views here.

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

class SettingsView(LoginRequiredMixin,TemplateView):
	template_name = 'dashboard/settings.html'

class SettingsUpdateView(LoginRequiredMixin,UpdateView):
	form_class = SettingForm
	model = Setting
	template_name = 'dashboard/settings_update.html'
	success_url = reverse_lazy('settings')

	def get_initial(self):
		initial = super(SettingsUpdateView, self).get_initial()
		if self.request.user.is_authenticated:
			setting = Setting.objects.get(id=1)
			initial.update({'site_name': setting.site_name, 'logo': setting.logo,'header_color': setting.header_color,'background_color': setting.background_color,'sidebar_color': setting.sidebar_color,'footer_color': setting.footer_color,'default_profile': setting.default_profile,})
		return initial

	def form_valid(self, form):
		form.save()
		return super(SettingsUpdateView, self).form_valid(form)

# def SettingsUpdateView(request):
# 	setting = Setting.objects.get(id=1) # just an example
# 	data = {'site_name': setting.site_name, 'logo': setting.logo,'header_color': setting.header_color}
# 	form = SettingForm(initial=data)
# 	return render_to_response('dashboard/settings_update.html', {'form': form})

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