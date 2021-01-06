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
CONFIG_PATH = os.path.join(BASE_DIR, 'config/configuration.stc')
reader = StdmConfigurationReader(CONFIG_PATH)
reader.load()
stdm_config = StdmConfiguration.instance()

def toHeader(s):
	"""
	:return: Returns the column name formatted with the first character
	for each word in uppercase. Underscores are replaced with a space and
	'_id' is removed if it exists.
	:rtype: str
	"""
	id_text = '_id'
	if id_text in s:
		display_name = s.title()
		display_name = display_name.replace('Id', 'ID')

	else:
		display_name = s.title()

	return display_name.replace('_', ' ')

def checkColumns(table_name):
	db_columns = []	
	with connection.cursor() as cursor:
		query="SELECT column_name FROM information_schema.columns WHERE table_name="+ "'" +table_name + "';"
		cursor.execute(query)
		result = cursor.fetchall()
		for field_name in result:			
			db_columns.append(field_name[0])	
	return db_columns

def checkEntity(prefix):
	db_entity_list = []
	with connection.cursor() as cursor:
		query="SELECT table_name FROM information_schema.tables WHERE table_schema='public' and table_name like " + "'" +prefix + "_%" +"';"
		print(query)
		cursor.execute(query)
		result = cursor.fetchall()
		for entity_name in result:
			db_entity_list.append(entity_name[0])	
	return db_entity_list


@login_required
def STDMReader(request):	
	profiles_list = []
	entities = []
	config_entities = []
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
	other_columns = []
	for profile in stdm_config.profiles.values():
		if profile.name == default_profile:
			profiler= profile 
			party = profiler.social_tenure.parties[0]
			spatial_unit = profiler.social_tenure.spatial_units[0]
			config_entities.append(party)
			config_entities.append(spatial_unit)            
			for entity in profiler.entities.values():
				if entity.TYPE_INFO == 'ENTITY':
					if entity.user_editable == True:
						if entity is not party and 	entity is not spatial_unit:
							config_entities.append(entity)
						for column in entity.columns.values():
							if column.TYPE_INFO == 'GEOMETRY':
								spatial_entity.append(entity.name)
								spatial_columns.append(column.name)
								for col in entity.columns.values():
									if col.name != 'id' and col.name not in spatial_columns:
										other_columns.append(col.name)
	default_profile_object = [prof.prefix for prof in stdm_config.profiles.values() if prof.name==default_profile]
	db_entities = checkEntity(','.join(default_profile_object))
	for entity in config_entities:
		if entity.name in db_entities:
			entities.append(entity)

	print('Spatial Entity', spatial_entity)
	# print('Entities', entities)
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
			items = [zip([key[0] for key in cursor.description if key[0]  != 'id'], row[1:]) for row in rsot]
			
		summaries = {'name':[],'count':[]}
		with connection.cursor() as cursor:
			for en in entities:
				query = "SELECT * FROM {0}".format(en.name)
				cursor.execute(query)
				records = cursor.fetchall()
				summaries["name"].append(en.ui_display())
				summaries["count"].append(len(records))
		zipped_summaries = zip(summaries["name"][:4],summaries["count"][:4])

	print(spatial_columns)
	columns_to_query = []
	if spatial_entity:		
		db_columns = checkColumns(spatial_entity[0])
		print('Db Columns',db_columns)
		print(other_columns)
		for col in other_columns:
			if col in db_columns:
				columns_to_query.append(col)
		print(columns_to_query)

		with connection.cursor() as cursor:
			query="SELECT row_to_json(fc) \
				FROM \
				( SELECT 'FeatureCollection' AS TYPE, \
						array_to_json(array_agg(f)) AS features \
				FROM \
					(SELECT 'Feature' AS TYPE, \
							ST_AsGeoJSON(g.{},4326)::JSON AS geometry, \
							row_to_json( (SELECT p FROM ( SELECT {}) AS p)) AS properties \
					FROM {} AS g ) AS f) AS fc;	".format(spatial_columns[0], ','.join(columns_to_query),spatial_entity[0])
			# query = "SELECT * FROM {0}".format(spatial_entity_query)
			cursor.execute(query)
			spatial_result = cursor.fetchone()
			map_data = spatial_result[0]
			spatial_results = json.dumps(map_data)
			
			# serialize('geojson',dataset,geometry_field="spatial_geometery",srid=4326,fields=('name',))
			# print(spatial_results)		
	return render(request, 'dashboard/index.html', {'configs': configs,'default_profile':default_profile,'profiles':profiles_list,'columns':columns,'entities':entities,'default_entity':default_entity,'data':items,'summaries':zipped_summaries,'spatial_result':spatial_results,'charts':summaries})

@csrf_exempt
def ProfileUpdatingView(request, profile):
	entities = []
	entity_columns = []
	query_columns = []
	columns = []
	items = []
	for profiles in stdm_config.profiles.values():
		if profile == profiles.name:
			profiler= profiles         
			for entity in profiler.entities.values():
				if entity.TYPE_INFO == 'ENTITY':
					if entity.user_editable == True:					
						entities.append(entity)
	default_entity = entities[0]
	print(default_entity)
	with connection.cursor() as cursor:
		query = "SELECT * FROM {0}".format(default_entity.name)	
		cursor.execute(query)
		rsot = cursor.fetchall()
		print(rsot)
		for col in cursor.description:
				query_columns.append(col.name)
		for column in default_entity.columns.values():
			entity_columns.append(column.name)
			if column.name in query_columns:
				if column.name != 'id':
					columns.append(column.header())
		items = [zip([key[0] for key in cursor.description if key[0]  != 'id'], row[1:]) for row in rsot]
	return render(request,'dashboard/records.html', {'entities':entities,'default_entity':default_entity,'data':items,'columns':columns})

@csrf_exempt
def EntityListingUpdatingView(request, profile):  
	entity_list = []
	for profiles in stdm_config.profiles.values():
		if profiles.name == profile: 			
			profiler= profiles
			for entity in profiler.entities.values():
				if entity.TYPE_INFO == 'ENTITY':
					if entity.user_editable == True:
						entity_list.append(entity)
	print('Entities for profile', entity_list)					
	return render(request,'dashboard/profile_detail.html', { 'entity_list':entity_list,})

@csrf_exempt
def EntityDetailView(request, profile,entity_name):
	entity_detail = None
	entities = []
	entity_columns = []
	query_columns = []
	columns = []
	has_spatial_column = None 
	for prof in stdm_config.profiles.values():
		if profile == prof.name:       
			for entity in prof.entities.values():
				if entity.TYPE_INFO == 'ENTITY':					
					if entity_name == entity.ui_display():
						entity_detail = entity.name
						entities.append(entity)
						query_columns = checkColumns(entity_detail)
						for column in entity.columns.values():
							if column not in entity.geometry_columns():
								entity_columns.append(column.name)
						if entity.has_geometry_column():
							has_spatial_column = 'true'
						else:
							has_spatial_column = 'false'
	default_entity = entities[0]
	format_query_columns = []
	

	for col in query_columns:
		if col in entity_columns:
			columns.append(toHeader(col))
			format_query_columns.append(col)
	print('Query columns',query_columns)
	print('entity columns',entity_columns)
	print('final Columns', columns)
	print('Entitity Detail',entity_detail)
	with connection.cursor() as cursor:
		query = "SELECT {0} FROM {1}".format(','.join(format_query_columns), entity_detail)
		cursor.execute(query)
		data1 = cursor.fetchall()
		
		# for col in cursor.description:
		# 		query_columns.append(col.name)
		# for column in default_entity.columns.values():
		# 	entity_columns.append(column.name)
		# 	if column.name in query_columns:
		# 		if column.name != 'id':
		# 			columns.append(column.header())
		items = [zip([key[0] for key in cursor.description], row) for row in data1]
			
	return render(request,'dashboard/records.html', {'default_entity':default_entity,'entity_name':entity_name,'data':items,'columns':columns,'has_spatial_column':has_spatial_column })

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


def createView(query):
	with connection.cursor as cursor:
		cursor.execute(query)


def createViews(request):
   for profile in stdm_config.profiles.values():
	   str = profile.social_tenure
	   prefix =  profile.prefix
	
	   """ str_spatial_unit_entities = str.spatial_units
	   str_party_entities = str.parties
	   str_table_name = prefix + "_social_tenure_relationship child" """

	   for entity in profile.entities.values():
		   all_columns =[]
		   parent_columns = entity.columns.values()
		   all_columns.extend(parent_columns)
		   view_name = entity.name + '_view'
		   query_string_list = []
		   
		   for relation in entity.parent_relations:
			   parent_columns.extend(relation.parent.columns.values())
			   query_string_list.append(' inner join '+ relation.parent.name + 'on' + relation.parent.name +'.'+ relation.parent_column + '=' + relation.child.name + '.' + child_column)
			   all_columns.extend(relation.parent.columns.values())
		   all_columns.remove('id')
		   query_string_list.append('CREATE OR REPLACE VIEW '+ view_name + 'AS')
		   query_string_list.append('SELECT '+ ",".join(all_columns) +' from ' + entity.name)
		   query = ''.join(query_string_list)
		   print(query)
		   ##createView(query)