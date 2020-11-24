from django.shortcuts import render
from django.views.generic import FormView, CreateView, DetailView, ListView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
# Create your views here.
class DashboardView(LoginRequiredMixin,TemplateView):
    template_name = 'dashboard/index.html'
