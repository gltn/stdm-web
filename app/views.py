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
from .models import Profile
from .serializers import ProfileSerializer
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
