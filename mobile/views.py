import os
from stdm_config import StdmConfigurationReader, StdmConfiguration
from app.models import Setting,Configuration
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
import json
from django.conf import settings
from app.config_reader import GetStdmConfig, GetConfig
from stdm_config.mobile_reader import FindEntitySubmissions
from koboextractor import KoboExtractor


#Mobile Component
BASE_DIR_MOBILE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#config = GetConfig("Mobile")
#MOBILE_CONFIG_PATH = os.path.join(settings.MEDIA_ROOT, str(config.config_file))
#mobile_reader = StdmConfigurationReader(MOBILE_CONFIG_PATH)
#mobile_reader.load()
#mobile_stdm_config = GetStdmConfig("Mobile")
#print('Value of complete',config.complete, config.config_type)
#Mobile instances detail
instance_path = os.path.join(BASE_DIR_MOBILE, 'config/mobile_instances')
#mobile_xml_files = [path.join(instance_path, f) for f in listdir(instance_path) if f.endswith('.xml')]


def EntityData(profile_name, entity_name,entity_short_name):
	print(profile_name, entity_name, entity_short_name)
	mobile_stdm_config = GetStdmConfig("Mobile")
	datas=[]
	spatial_data = []
	for file in FindEntitySubmissions(profile_name):
		submission_xml = ET.parse(file)
		submission_root = submission_xml.getroot()
		if (submission_root.tag == profile_name ):
			entity_data ={}
			spatial_item ={}
			for entity in submission_root:
				if entity.tag == entity_name:
					columns = [elem.tag for elem in entity.iter() if elem is not entity]
					for elem in entity.iter():
						if elem is not entity:							
							spatial_item[elem.tag] = elem.text
							if elem.tag != 'spatial_geometry':
								entity_data[toHeader(elem.tag)] = elem.text
					datas.append(entity_data)
					spatial_data.append(spatial_item)
	prof = mobile_stdm_config.profile(profile_name)
	entity_object = prof.entity(entity_short_name)
	geojson = None
	if entity_object.has_geometry_column():	
		geojson = {'type':'FeatureCollection', 'features':[]}	
		for row in spatial_data:
			feature = {'type':'Feature','properties':{},'geometry':{'coordinates':[]}}
			feature['geometry']['coordinates'] = json.dumps(row['spatial_geometry'])
			for prop in row:
				if prop != 'spatial_geometry':
					feature['properties'][prop] = row[prop]
			geojson['features'].append(feature)

	return [datas,json.dumps(geojson)]

@login_required
def MobileView(request):
	config = GetConfig("Mobile")
	if config is None or not config.complete:
		return render(request, 'dashboard/no_config.html',)
	mobile_stdm_config = GetStdmConfig("Mobile")
	profiles_list = []
	entities = []
	config_entities = []
	default_profile = None
	configs = None
	for profile in mobile_stdm_config.profiles.values(): 
		profiles_list.append(profile.name)
	if profiles_list:
		default_profile = profiles_list[0]
		if Setting.objects.exists():
			configs =Setting.objects.all().first()
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
	for file in FindEntitySubmissions(default_profile):
		tree = ET.parse(file)
		root =  tree.getroot()
		if root.tag == default_profile:
			for child in root:
				for en in entities:
					if child.tag != 'meta' and child.tag != 'social_tenure':
						if child.tag == en.name:
							summaries.append(en.short_name)
	dict_summaries = Counter(summaries)
	actual_summaries = {'name':[],'count':[]}
	for i in Counter(summaries):
		actual_summaries["name"].append(i)
		actual_summaries["count"].append(dict_summaries[i])
	zipped_summaries = zip(actual_summaries["name"][:4],actual_summaries["count"][:4])
	print('Zipped',actual_summaries)
	return render(request, 'dashboard/mobile.html', {'configs':configs,'default_profile':default_profile,'profiles':profiles_list,'m_entities':entities, 'summaries':zipped_summaries,'charts':actual_summaries})

@login_required
def MobileViewSync(request):
	
	config = GetConfig("Mobile")
	if config is None or not config.complete:
		return render(request, 'dashboard/no_config.html',)
	mobile_stdm_config = GetStdmConfig("Mobile")
	profiles_list = []
	entities = []
	config_entities = []
	default_profile = None
	configs = None

	for profile in mobile_stdm_config.profiles.values(): 
		profiles_list.append(profile.name)
	if profiles_list:
		default_profile = profiles_list[0]
		if Setting.objects.exists():
			configs =Setting.objects.all().first()
	
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
	for file in FindEntitySubmissions(default_profile):
		tree = ET.parse(file)
		root =  tree.getroot()
		if root.tag == default_profile:
			for child in root:
				for en in entities:
					if child.tag != 'meta' and child.tag != 'social_tenure':
						if child.tag == en.name:
							summaries.append(en.short_name)
	dict_summaries = Counter(summaries)
	actual_summaries = {'name':[],'count':[]}
	for i in Counter(summaries):
		actual_summaries["name"].append(i)
		actual_summaries["count"].append(dict_summaries[i])
	zipped_summaries = zip(actual_summaries["name"][:4],actual_summaries["count"][:4])
	print('Zipped',actual_summaries)
	return render(request, 'dashboard/mobile_sync.html', {'configs':configs,'default_profile':default_profile,'profiles':profiles_list,'m_entities':entities, 'summaries':zipped_summaries,'charts':actual_summaries})

def entity_columns_with_type_given_entity_object(entity):
	entity_columns =[]
	for column in entity.columns.values():
		column_data ={}
		print('Columns:', column.name, column.TYPE_INFO)
		if column not in entity.geometry_columns():
			column_data['column_name']=column.name
			column_data['data_type'] =column.TYPE_INFO
			entity_columns.append(column_data)
	return entity_columns

def entity_columns_given_entity_object(entity):
	entity_columns =[]
	for column in entity.columns.values():
		if column not in entity.geometry_columns():
			entity_columns.append(column.name)
	return entity_columns


def entity_columns_with_type_given_entity_object(entity):
	entity_columns =[]
	for column in entity.columns.values():
		column_data ={}
		print('Columns:', column.name, column.TYPE_INFO)
		if column not in entity.geometry_columns():
			column_data['column_name']=column.name
			column_data['data_type'] =column.TYPE_INFO
			entity_columns.append(column_data)
	return entity_columns

@csrf_exempt
def MobileEntityDetailView(request, profile_name,name):
	config = GetConfig("Mobile")
	if config is None or not config.complete:
		return render(request, 'dashboard/no_config.html',)
	mobile_stdm_config = GetStdmConfig("Mobile")
	entity_name = None
	entities = []
	query_columns = []
	columns = []
	has_spatial_column = None
	is_str_entity = None

	prof = mobile_stdm_config.profile(profile_name)
	entity = prof.entity(name)
	social_tenure = prof.social_tenure       
	entity_name = entity.name
	entity_short_name = entity.short_name
	entities.append(entity)

	entity_columns = entity_columns_given_entity_object(entity)

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
	returned_data = EntityData(profile_name, entity_name, entity_short_name)
	return render(request,'dashboard/mobile_entity.html', {'default_entity':default_entity,'profile':profile_name,'entity_name':entity_name,'columns':columns,'has_spatial_column':has_spatial_column,'is_str_entity':is_str_entity, 'data':returned_data[0], 'spatial_dataset': returned_data[1] })

@csrf_exempt
def entity_columns(request, profile_name, entity_name):
	print(profile_name,entity_name)
	mobile_stdm_config = GetStdmConfig("Mobile")
	profile = mobile_stdm_config.profile(profile_name)
	entity = profile.entity(entity_name)
	print('Tunacheki entities', entity, entity_name)
	entity_columns_list = entity_columns_with_type_given_entity_object(entity)
	print(entity_columns_list)
	return render(request,'dashboard/mobile_entity_columns.html', {'entity_columns_list':entity_columns_list,})

KOBO_TOKEN = "69f8b59f361147bf8f2f454d8d0e618e9135c404"
def KoboView(request):
	kobo = KoboExtractor(KOBO_TOKEN, 'https://kf.omdtz.xyz/api/v2',debug=True)
	assets = kobo.list_assets()
	# asset_uid = assets['results'][0]['uid']
	asset_uid ="acoHCC2EZBjpjYZfDYZdFE"
	asset = kobo.get_asset(asset_uid)
	choice_lists = kobo.get_choices(asset)
	questions = kobo.get_questions(asset=asset, unpack_multiples=True)
	new_data = kobo.get_data(asset_uid, submitted_after='2020-05-20T17:29:30') #Get data submitted after a certain time
	new_results = kobo.sort_results_by_time(new_data['results']) #Sort list by time
	labeled_results = []
	for result in new_results: # new_results is a list of list of dicts
		labeled_results.append(kobo.label_result(unlabeled_result=result, choice_lists=choice_lists, questions=questions, unpack_multiples=True))
	# print(labeled_results)
	return render(request,'dashboard/kobo_data.html', {'new_results':labeled_results})
