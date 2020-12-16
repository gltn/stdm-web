import os
from stdm_config import StdmConfigurationReader, StdmConfiguration
from app.models import Setting
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from stdm_config.create_model import create_model
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
# from psycopg2 import connect, sql
# from psycopg2.extras import RealDictCursor
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, 'config/default_configuration.xml')
@login_required
def STDMReader(request):
	reader = StdmConfigurationReader(CONFIG_PATH)
	reader.load()
	stdm_config = StdmConfiguration.instance()
	profiles_list = []
	entities = []
	default_profile = None
	configs = None
	for profile in stdm_config.profiles.values(): 
		profiles_list.append(profile.name)

	print('Profile List', profiles_list)
	if profiles_list:
		# Get settings details and retrieve default settings
		if Setting.objects.exists():
			configs =Setting.objects.all().first()
			if configs:
				print(configs.default_profile)
				if configs.default_profile in profiles_list:
					print('yes yes')
					default_profile = configs.default_profile
				else:
					default_profile = profiles_list[0]
		else:
			configs = Setting.objects.create(default_profile=profiles_list[0])
			configs.save()
			default_profile = configs.default_profile	
	# Loop through profiles and get entities
	for profile in stdm_config.profiles.values(): 
		if profile.name == default_profile:
			profiler= profile          
			for entity in profiler.entities.values():
				if entity.TYPE_INFO == 'ENTITY':
					entities.append(entity)
					columns = []
					for column in entity.columns.values():
						columns.append(column.name)
	print('default', default_profile)
	default_entity =  None
	data = []
	if entities:
		default_entity = entities[0]			
		with connection.cursor() as cursor:
			query = "SELECT * FROM {0}".format(default_entity.name)
			cursor.execute(query)
			col_name = [col[0] for col in cursor.description]
			data = cursor.fetchall()
	return render(request, 'dashboard/index.html', {'configs': configs,'default_profile':default_profile,'profiles':profiles_list,'entities':entities,'default_entity':default_entity,'data':data})

@csrf_exempt
def ProfileUpdatingView(request, profile):
	reader = StdmConfigurationReader(CONFIG_PATH)
	reader.load()
	stdm_config = StdmConfiguration.instance() 
	entities = []
	for profiles in stdm_config.profiles.values():
		if profiles.name == profile:
			profiler= profiles         
			for entity in profiler.entities.values():
				if entity.TYPE_INFO == 'ENTITY':					
					entities.append(entity)
					columns = []
					for column in entity.columns.values():
						columns.append(column.name)
	default_entity = entities[0]
	print(default_entity)
	with connection.cursor() as cursor:
		query = "SELECT * FROM {0}".format(default_entity.name)
		cursor.execute(query)
		col_name = [col[0] for col in cursor.description]
		data = cursor.fetchall()
		print(data)
	return render(request,'dashboard/records.html', {'entities':entities,'default_entity':default_entity,'data':data})

@csrf_exempt
def EntityListingUpdatingView(request, profile):
	reader = StdmConfigurationReader(CONFIG_PATH)
	reader.load()
	stdm_config = StdmConfiguration.instance()      
	entity_list = []
	for profiles in stdm_config.profiles.values():
		if profiles.name == profile: 			
			profiler= profiles
			for entity in profiler.entities.values():
				if entity.TYPE_INFO == 'ENTITY':
					entity_list.append(entity)
	print('Entities for profile', entity_list)					
	return render(request,'dashboard/profile_detail.html', { 'entity_list':entity_list,})

@csrf_exempt
def EntityDetailView(request, entity_name):
	reader = StdmConfigurationReader(CONFIG_PATH)
	reader.load()
	stdm_config = StdmConfiguration.instance()
	entity_detail = None
	entities = [] 
	for profiles in stdm_config.profiles.values():      
		for entity in profiles.entities.values():
			if entity.TYPE_INFO == 'ENTITY':
				if entity.short_name == entity_name:
					entity_detail = entity.name
					entities.append(entity)
	default_entity = entities[0]
	print(entity_name)
	with connection.cursor() as cursor:
		query = "SELECT * FROM {0}".format(entity_detail)
		cursor.execute(query)
		col_name = [col[0] for col in cursor.description]
		data = cursor.fetchall()
		print(data)
	return render(request,'dashboard/records.html', {'default_entity':default_entity,'entity_name':entity_name,'data':data,'col_name':col_name})