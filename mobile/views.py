import os
from stdm_config import StdmConfigurationReader, StdmConfiguration
from app.models import Setting
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from stdm_config.create_model import create_model
from django.http import HttpResponse,JsonResponse
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from os import listdir, path
import xml.etree.ElementTree as ET
from collections import Counter
from stdm_config.views import toHeader

#Mobile Component
StdmConfiguration.cleanUp()
BASE_DIR_MOBILE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOBILE_CONFIG_PATH = os.path.join(BASE_DIR_MOBILE, 'config/mobile_configuration.xml')
mobile_reader = StdmConfigurationReader(MOBILE_CONFIG_PATH)
mobile_reader.load()
mobile_stdm_config = StdmConfiguration.instance()

#Mobile instances detail
instance_path = os.path.join(BASE_DIR_MOBILE, 'config/mobile_instances')
mobile_xml_files = [path.join(instance_path, f) for f in listdir(instance_path) if f.endswith('.xml')]



def ListSubmissions():
	MOBILE_PATH = os.path.join(BASE_DIR, 'config/instances/Informal_Settlement_2021-01-22_13-48-05')
	for subdir, dirs, files in os.walk(MOBILE_PATH):
		for file in files:
			file_name = os.path.join(subdir, file)
			xml = ET.parse(file_name)
			if (Path(file_name).suffix == '.xml'):
				print(file_name)

@login_required
def MobileView(request):	
	profiles_list = []
	entities = []
	config_entities = []
	default_profile = None
	configs = None
	entity_columns = []
	query_columns = []
	columns = []
	for profile in mobile_stdm_config.profiles.values(): 
		profiles_list.append(profile.name)
	if profiles_list:
		default_profile = profiles_list[0]
		if Setting.objects.exists():
			configs =Setting.objects.all().first()

	other_columns = []	
	profiler = mobile_stdm_config.profile(default_profile)
	party = profiler.social_tenure.parties[0]
	spatial_unit = profiler.social_tenure.spatial_units[0]
	config_entities.append(party)
	config_entities.append(spatial_unit)            
	for entity in profiler.entities.values():
		if entity.TYPE_INFO == 'ENTITY':
			if entity.user_editable == True:
				entities.append(entity)
				if entity is not party and 	entity is not spatial_unit:
					config_entities.append(entity)
	#Reading xml files
	summaries = []
	table_data = []
	values = {}
	for file in mobile_xml_files:
		tree = ET.parse(file)
		root =  tree.getroot()
		if root.tag == default_profile:
			for child in root:
				print(child.tag)
				table_data[child.tag]
				for en in entities:
					if child.tag != 'meta' and child.tag != 'social_tenure':
						if child.tag == en.name:
							# if en.short_name not in summaries["name"]:
							summaries.append(en.short_name)
				for data in root.iter(child.tag):
					print(data.text)
					for dt in data:
						table_data[child.tag] = {dt.tag:dt.text}
	print(table_data)
	dict_summaries = Counter(summaries)
	actual_summaries = {'name':[],'count':[]}
	for i in Counter(summaries):
		actual_summaries["name"].append(i)
		actual_summaries["count"].append(dict_summaries[i])
	zipped_summaries = zip(actual_summaries["name"][:4],actual_summaries["count"][:4])
	return render(request, 'dashboard/mobile.html', {'configs':configs,'default_profile':default_profile,'profiles':profiles_list,'m_entities':entities, 'summaries':zipped_summaries,'charts':actual_summaries})

@csrf_exempt
def MobileEntityDetailView(request, profile_name,name):
	entity_name = None
	entities = []
	entity_columns = []
	query_columns = []
	columns = []
	has_spatial_column = None
	is_str_entity = None
	prof = mobile_stdm_config.profile(profile_name)
	entity = prof.entity(name)
	print('ENTITY',entity)
	social_tenure = prof.social_tenure       
	entity_name = entity.name
	entities.append(entity)

	for column in entity.columns.values():
		if column not in entity.geometry_columns():
			entity_columns.append(column.name)

	if entity.has_geometry_column():
		has_spatial_column = True
	else:
		has_spatial_column = False
	
	if social_tenure.is_str_entity(entity):
		is_str_entity = True	

	default_entity = entities[0]
	format_query_columns = []
	for col in query_columns:
		if col in entity_columns:
			columns.append(toHeader(col))
			format_query_columns.append(col)
	return render(request,'dashboard/mobile_entity.html', {'default_entity':default_entity,'profile':profile_name,'entity_name':entity_name,'columns':columns,'has_spatial_column':has_spatial_column,'is_str_entity':is_str_entity })
