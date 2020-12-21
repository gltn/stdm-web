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
import json
from django.core.serializers import serialize
# from psycopg2 import connect, sql
# from psycopg2.extras import RealDictCursor
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, 'config/default_configuration.xml')
reader = StdmConfigurationReader(CONFIG_PATH)
reader.load()
stdm_config = StdmConfiguration.instance()
@login_required
def STDMReader(request):	
	profiles_list = []
	entities = []
	default_profile = None
	configs = None
	entity_columns = []
	query_columns = []
	columns = []
	for profile in stdm_config.profiles.values(): 
		profiles_list.append(profile.name)
	if profiles_list:
		# Get settings details and retrieve default settings
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
	# Loop through profiles and get entities
	spatial_entity = []
	spatial_columns = []
	for profile in stdm_config.profiles.values(): 
		if profile.name == default_profile:
			profiler= profile          
			for entity in profiler.entities.values():
				if entity.TYPE_INFO == 'ENTITY':
					entities.append(entity)
					for column in entity.columns.values():
						if column.TYPE_INFO == 'GEOMETRY':
							spatial_entity.append(entity.name)
							spatial_columns.append(column.name)
							spatial_columns.append('name')

	print('Spatial Entity', spatial_entity)
	dataset = []
	default_entity =  None
	data = []
	if entities:
		default_entity = entities[0]			
		with connection.cursor() as cursor:
			# query = "CREATE OR REPLACE VIEW default_entities_ko AS SELECT * FROM {0}".format(default_entity.name)			
			# cursor.execute(query)
			query1 = "SELECT * FROM {0}".format(default_entity.name)
			cursor.execute(query1)
					
			for col in cursor.description:
				query_columns.append(col.name)
			for column in default_entity.columns.values():
				entity_columns.append(column.name)
				if column.name in query_columns:
					if column.name != 'id':
						columns.append(column.header())				
			rsot = cursor.fetchall()
			for row in rsot:
				datas = row[1:]
			items = [zip([key[0] for key in cursor.description if key[0]  != 'id'], datas) for row in rsot]
			
		summaries = {'name':[],'count':[]}
		with connection.cursor() as cursor:
			for en in entities:
				query = "SELECT * FROM {0}".format(en.name)
				cursor.execute(query)
				datas = cursor.fetchall()
				summaries["name"].append(en.short_name)
				summaries["count"].append(len(datas))
		zipped_summaries = zip(summaries["name"][:4],summaries["count"][:4])

	print(spatial_columns)
	if spatial_entity:
		spatial_entity_query = spatial_entity[0]
		with connection.cursor() as cursor:
			query="SELECT row_to_json(fc) \
				FROM \
				( SELECT 'FeatureCollection' AS TYPE, \
						array_to_json(array_agg(f)) AS features \
				FROM \
					(SELECT 'Feature' AS TYPE, \
							ST_AsGeoJSON(g.spatial_geometery,4326)::JSON AS geometry, \
							row_to_json( (SELECT p FROM ( SELECT code,area,value) AS p)) AS properties \
					FROM {0} AS g ) AS f) AS fc;	".format(spatial_entity_query)
			# query = "SELECT * FROM {0}".format(spatial_entity_query)
			cursor.execute(query)
			spatial_result = cursor.fetchone()
			map_data = spatial_result[0]
			spatial_results = json.dumps(map_data)
			# serialize('geojson',dataset,geometry_field="spatial_geometery",srid=4326,fields=('name',))
			print(spatial_results)		
		

	return render(request, 'dashboard/index.html', {'configs': configs,'default_profile':default_profile,'profiles':profiles_list,'columns':columns,'entities':entities,'default_entity':default_entity,'data':items,'summaries':zipped_summaries,'spatial_result':spatial_results})

@csrf_exempt
def ProfileUpdatingView(request, profile):
	entities = []
	entity_columns = []
	query_columns = []
	columns = []
	items = []
	for profiles in stdm_config.profiles.values():
		if profiles.name == profile:
			profiler= profiles         
			for entity in profiler.entities.values():
				if entity.TYPE_INFO == 'ENTITY':					
					entities.append(entity)
	default_entity = entities[0]
	print(default_entity)
	with connection.cursor() as cursor:
		query = "SELECT * FROM {0}".format(default_entity.name)	
		results = cursor.execute(query)
		rsot = cursor.fetchall()
		for col in cursor.description:
				query_columns.append(col.name)
		for column in default_entity.columns.values():
			entity_columns.append(column.name)
			if column.name in query_columns:
				if column.name != 'id':
					columns.append(column.header())
		# print(query_columns)
		# print(entity_columns)
		for row in rsot:
			data = row[1:]
		items = [zip([key[0] for key in cursor.description if key[0]  != 'id'], data) for row in rsot]
	return render(request,'dashboard/records.html', {'entities':entities,'default_entity':default_entity,'data_items':items,'columns':columns})

@csrf_exempt
def EntityListingUpdatingView(request, profile):  
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
	entity_detail = None
	entities = []
	entity_columns = []
	query_columns = []
	columns = [] 
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
		for col in cursor.description:
				query_columns.append(col.name)
		for column in default_entity.columns.values():
			entity_columns.append(column.name)
			if column.name in query_columns:
				if column.name != 'id':
					columns.append(column.header())	
	return render(request,'dashboard/records.html', {'default_entity':default_entity,'entity_name':entity_name,'data':data,'columns':columns})

@csrf_exempt
def SummaryUpdatingView(request, profile):
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
	summaries = {'name':[],'count':[]}
	with connection.cursor() as cursor:
		for en in entities:
			# query = "SELECT count(*) FROM {0}".format(en.name)			
			query = "SELECT * FROM {0}".format(en.name)
			cursor.execute(query)
			data = cursor.fetchall()			
			summaries["name"].append(en.short_name)
			summaries["count"].append(len(data))
	zipped_summaries = zip(summaries["name"][:4],summaries["count"][:4])
	return render(request,'dashboard/summary.html', {'entities':entities,'summaries':zipped_summaries})