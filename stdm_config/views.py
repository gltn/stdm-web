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
CONFIG_PATH = os.path.join(BASE_DIR, 'config/configuration.xml')
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
	other_columns = []
	profiler = stdm_config.profile(default_profile)
	str_summary = str_summaries(profiler)
	party = profiler.social_tenure.parties[0]
	spatial_unit = profiler.social_tenure.spatial_units[0]
	config_entities.append(party)
	config_entities.append(spatial_unit)            
	for entity in profiler.entities.values():
		if entity.TYPE_INFO == 'ENTITY':
			if entity.user_editable == True:
				if entity is not party and 	entity is not spatial_unit:
					config_entities.append(entity)
	default_profile_object = [prof.prefix for prof in stdm_config.profiles.values() if prof.name==default_profile]
	db_entities = checkEntity(','.join(default_profile_object))
	for entity in config_entities:
		if entity.name in db_entities:
			entities.append(entity)
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
				summaries["name"].append(en.short_name)
				summaries["count"].append(len(records))
		zipped_summaries = zip(summaries["name"][:4],summaries["count"][:4])	
	return render(request, 'dashboard/index.html', {'configs': configs,'default_profile':default_profile,'profiles':profiles_list,'columns':columns,'entities':entities,'default_entity':default_entity,'data':items,'summaries':zipped_summaries,'charts':summaries,'str_summary':str_summary})

def str_summaries(profile):
	str = profile.social_tenure
	tenure_type = str.tenure_type_collection
	relation = profile.parent_relations(tenure_type)[0]	
	query = 'select count(*), ' + relation.parent.name + '.value from '+ relation.parent.name + ' join ' + relation.child.name + ' on ' + relation.child.name+'.'+relation.child_column + '='+ relation.parent.name+'.'+relation.parent_column+ ' group by '+ relation.parent.name + '.value ;'
	return queryStrDetailsSTR(query)

@csrf_exempt
def ProfileUpdatingView(request, profile):
	entities = []
	profiler = stdm_config.profile(profile)
	str_summary = str_summaries(profiler)
	entity_list = profiler.user_entities()
	print('This is the str summary')
	print(str_summary)
	for entity in entity_list:
		entities.append(entity)
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
	return render(request,'dashboard/profile_changes.html', {'entities':entities, 'str_summary':str_summary, 'summaries':zipped_summaries,'charts':summaries})

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
	return render(request,'dashboard/profile_detail.html', { 'entity_list':entity_list,})

def EntityLookupSummaries(profile, entity):
	lookup_columns = entity.columns_by_type_info('LOOKUP')
	results = {}
	for col in lookup_columns:
		ers = col.child_entity_relations()
		results[col.header()]=LooukupSummary(entity, ers)
	return results

def LooukupSummary(child_entity, ers):
	parent_entity = ers[0].parent
	#select count(*), cg.value from ko_farmer f left join ko_check_gender cg on cg.id = f.gender group by cg.value;
	query = 'select count(*), ' + parent_entity.name + '.value from '+ child_entity.name + ' join ' + parent_entity.name + ' on ' + parent_entity.name+'.'+ers[0].parent_column + '='+ child_entity.name+'.'+ers[0].child_column+ ' group by '+ parent_entity.name + '.value;'
	return queryStrDetailsSTR(query)

@csrf_exempt
def EntityDetailView(request, profile_name,short_name):
	entity_name = None
	entities = []
	entity_columns = []
	query_columns = []
	columns = []
	has_spatial_column = None
	is_party_entity = None
	prof = stdm_config.profile(profile_name)
	entity = prof.entity(short_name)
	social_tenure = prof.social_tenure       
	entity_name = entity.name
	entities.append(entity)
	query_columns = checkColumns(entity_name)

	for column in entity.columns.values():
		if column not in entity.geometry_columns():
			entity_columns.append(column.name)

	if entity.has_geometry_column():
		has_spatial_column = True
	else:
		has_spatial_column = False
	
	if social_tenure.is_str_party_entity(entity):
		is_party_entity = True	

	default_entity = entities[0]
	format_query_columns = []
	for col in query_columns:
		if col in entity_columns:
			columns.append(toHeader(col))
			format_query_columns.append(col)
	with connection.cursor() as cursor:
		query = "SELECT {0} FROM {1}".format(','.join(format_query_columns), entity_name)
		cursor.execute(query)
		data1 = cursor.fetchall()
		items = [zip([key[0] for key in cursor.description], row) for row in data1]
	
	# str_data = fetchPartySTR('KOPGT','Farmer',10)
	lookup_summaries = EntityLookupSummaries(prof, entity)

	# Fetch Spatial Data
	spatial_results = None
	if entity.has_geometry_column():
		other_columns = []
		columns_to_query = []
		spatial_columns = entity.geometry_columns()
		for sp in spatial_columns:
			spatial_column = sp.name
			break
		db_columns = checkColumns(entity.name)
		for colu in entity.columns.values():
			other_columns.append(colu.name)
		for colm in other_columns:
			if colm in db_columns:
				columns_to_query.append(colm)
		
		columns_to_query.remove('id')
		columns_to_query.remove(str(spatial_column))
		with connection.cursor() as cursor:
			query="SELECT row_to_json(fc) \
				FROM \
				( SELECT 'FeatureCollection' AS TYPE, \
						array_to_json(array_agg(f)) AS features \
				FROM \
					(SELECT 'Feature' AS TYPE, \
							ST_AsGeoJSON(g.{},4326)::JSON AS geometry, \
							row_to_json( (SELECT p FROM ( SELECT {}) AS p)) AS properties \
					FROM {} AS g ) AS f) AS fc;	".format(spatial_column, ','.join(columns_to_query),entity.name)
			# query = "SELECT * FROM {0}".format(spatial_entity_query)
			cursor.execute(query)
			spatial_result = cursor.fetchone()
			map_data = spatial_result[0]
			spatial_results = json.dumps(map_data)
			
	return render(request,'dashboard/entity.html', {'default_entity':default_entity,'profile':profile_name,'entity_name':entity_name,'data':items,'columns':columns,'has_spatial_column':has_spatial_column,'is_party_entity':is_party_entity,'lookup_summaries':lookup_summaries, 'spatial_result':spatial_results })

@csrf_exempt
def SummaryUpdatingView(request, profile):
	entities = []
	for profiles in stdm_config.profiles.values():
		if profiles.name == profile:
			profiler= profiles
			str_summary = str_summaries(profiler)        
			for entity in profiler.entities.values():
				if entity.TYPE_INFO == 'ENTITY':					
					entities.append(entity)
					columns = []
					for column in entity.columns.values():
						columns.append(column.name)
	
	return render(request,'dashboard/summarsy.html', {'entities':entities,'str_summary':str_summary})


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

def fetchPartySTR(profile_name, entity_short_name, id):
	# print(profile_name, entity_short_name,id)
	profile =stdm_config.profile(profile_name)
	str = profile.social_tenure
	prefix =  profile.prefix
	primary_entity = profile.entity(entity_short_name)
	secondary_entity = None
	str_primary_relation = None 
	str_secondary_relation = None 
	if(str.is_str_party_entity(primary_entity)):
		print(entity_short_name +' is Party '+ primary_entity.short_name)
		secondary_entity = str.spatial_units[0]
	if (str.is_str_spatial_unit_entity(primary_entity)):
		print(entity_short_name+ ' is SP Units '+ primary_entity.short_name)
		secondary_entity = str.parties[0]

	str_table_name = prefix + "_social_tenure_relationship"
	
	str_primary_relation = getStrRelation(profile, primary_entity, str_table_name)
	str_secondary_relation = getStrRelation(profile, secondary_entity, str_table_name)

	columns = getColumns(profile, secondary_entity)
	strQuery = 'select '+ ",".join(columns)+ ' from '+ str_primary_relation.child.name +' '+ str_primary_relation.child.name +' join '+ secondary_entity.name +' '+ secondary_entity.name +' on ' +secondary_entity.name+'.'+str_primary_relation.parent_column +' = '+str_primary_relation.child.name+'.'+str_primary_relation.child_column+ ' or '+ str_primary_relation.child.name+'.spatial_unit_id ='+ secondary_entity.name+'.id '
	
	queryWithJoin = strQuery + createParentJoins(profile, secondary_entity)
	whereClause = ' where'+' '+ str_primary_relation.child.name+'.party_id ={} or '.format(id) + str_primary_relation.child.name+'.'+ str_primary_relation.child_column +'={};'.format(id)
	fullQuery = queryWithJoin + whereClause

	data = queryStrDetails(fullQuery)
	#return render(request, 'dashboard/str.html', {'strdata':data})
	return data

def getStrRelation(profile, entity, str_table_name):
	STR_relation = None 
	for relation in profile.parent_relations(entity):
		if relation.child.name == str_table_name:
			return relation

def getColumns(profile, entity):
	q_columns = []
	for col in entity.columns.values():
		if col.TYPE_INFO not in ['LOOKUP', 'GEOMETRY', 'SERIAL']:
			print(col.name + ' '+ col.TYPE_INFO)
			q_columns.append(entity.name+'.'+col.name)
	
	for en in entity.parents():
		for relation in profile.parent_relations(en):
			value = en.name + ".value as "+ relation.child_column
			q_columns.append(value)

	return q_columns

def createParentJoins(profile, entity):
	joins = ''
	for en in entity.parents():
		for relation in profile.parent_relations(en):
		
			if (entity.name == relation.child.name and relation.parent.TYPE_INFO == 'VALUE_LIST'):
				join = 'join '+ en.name + ' '+ en.name+' on ' + en.name+'.'+relation.parent_column +'= '+ relation.child.name+'.'+ relation.child_column
				joins += " "
				joins += join

	return joins

def queryStrDetails(queryString):
	with connection.cursor() as cursor:
		cursor.execute(queryString)
		data = cursor.fetchall()
		print(data)
		return [zip([key[0] for key in cursor.description], row) for row in data]

def queryStrDetailsSTR(queryString):
	with connection.cursor() as cursor:
		cursor.execute(queryString)
		data = cursor.fetchall()
		sorted_str = sorted(data, key=lambda x: x[0], reverse=True)
		return sorted_str