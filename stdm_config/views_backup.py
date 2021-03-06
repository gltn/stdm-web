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

def GetDatabaseColumnsForEntity(table_name):
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

	profiler = stdm_config.profile(default_profile)
	str_summary = str_summaries(profiler)
	for party in profiler.social_tenure.parties:
		config_entities.append(party)
	for spatial_unit in profiler.social_tenure.spatial_units:
		config_entities.append(spatial_unit)    
	        
	for entity in profiler.entities.values():
		if entity.TYPE_INFO == 'ENTITY':
			if entity.user_editable == True:
				if entity not in config_entities:
					config_entities.append(entity)
	default_profile_object = [prof.prefix for prof in stdm_config.profiles.values() if prof.name == default_profile]
	db_entities = checkEntity(','.join(default_profile_object))
	for entity in config_entities:
		if entity.name in db_entities:
			entities.append(entity)
	
	if entities:			
		summaries = {'name':[],'count':[]}
		with connection.cursor() as cursor:
			for en in entities:	
				query = "SELECT count(*) FROM {0}".format(en.name)
				cursor.execute(query)
				counts = cursor.fetchall()
				if en in profiler.social_tenure.parties:
					summaries["name"].append(en.short_name +" (Party)")
				elif en in profiler.social_tenure.spatial_units:
					summaries["name"].append(en.short_name +" (Spatial Unit)")
				else:
					summaries["name"].append(en.short_name)
				summaries["count"].append(counts[0][0])
		zipped_summaries = zip(summaries["name"][:4],summaries["count"][:4])	
	return render(request, 'dashboard/index.html', {'configs': configs,'default_profile':default_profile,'profiles':profiles_list,'columns':columns,'entities':entities,'summaries':zipped_summaries,'charts':summaries,'str_summary':str_summary})

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
	entity_columns = []
	query_columns = []
	columns = []
	has_spatial_column = None
	is_str_entity = None
	prof = stdm_config.profile(profile_name)
	entity = prof.entity(short_name)
	social_tenure = prof.social_tenure       
	default_entity = prof.entity(short_name)
	entity_name = default_entity.name

	query_columns = GetDatabaseColumnsForEntity(entity_name)

	for column in default_entity.columns.values():
		if column not in default_entity.geometry_columns():
			entity_columns.append(column.name)

	if default_entity.has_geometry_column():
		has_spatial_column = True
	else:
		has_spatial_column = False
	
	if social_tenure.is_str_entity(default_entity):
		is_str_entity = True	


	# format_query_columns = []
	# for col in query_columns:
	# 	if col in entity_columns:
	# 		columns.append(toHeader(col))
	# 		format_query_columns.append(col)
	
	query_joins = createParentJoins(prof, default_entity)

	query_join_columns = GetColumns(prof, default_entity)

	with connection.cursor() as cursor:

		query = "SELECT {0} FROM {1} {2}".format(','.join(query_join_columns), entity_name, query_joins)
		cursor.execute(query)
		data1 = cursor.fetchall()
		items = [zip([key[0] for key in cursor.description], row) for row in data1]
		
		for key in cursor.description:
			columns.append(toHeader(key[0]))

	lookup_summaries = EntityLookupSummaries(prof, entity)

	# Fetch Spatial Data
	spatial_results = None
	if default_entity.has_geometry_column():
		other_columns = []
		columns_to_query = []
		spatial_columns = default_entity.geometry_columns()
		for sp in spatial_columns:
			spatial_column = sp.name
			break
		db_columns = GetDatabaseColumnsForEntity(default_entity.name)
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
					FROM {} AS g ) AS f) AS fc;	".format(spatial_column, ','.join(columns_to_query),default_entity.name)
			# query = "SELECT * FROM {0}".format(spatial_entity_query)
			cursor.execute(query)
			spatial_result = cursor.fetchone()
			map_data = spatial_result[0]
			spatial_results = json.dumps(map_data)	
	return render(request,'dashboard/entity.html', {'default_entity':default_entity,'profile':profile_name,'entity_name':entity_name,'data':items,'columns':columns,'has_spatial_column':has_spatial_column,'is_str_entity':is_str_entity,'lookup_summaries':lookup_summaries, 'spatial_result':spatial_results })

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


def CheckColumnInDB(entity):
	# SELECT column_name FROM information_schema.columns WHERE table_name='be_household';
	query="SELECT column_name FROM information_schema.columns WHERE table_name='{}';".format(entity.name)
	cols =[]
	result =[]
	with connection.cursor() as cursor:
		cursor.execute(query)
		cols = cursor.fetchall()
	for col in cols:
		result.append(col[0])
	return result

@csrf_exempt
def EntityRecordViewMore(request, profile_name, entity_short_name, id):
	result = None
	profile = stdm_config.profile(profile_name)
	current_entity = profile.entity(entity_short_name)
	current_social_tenure = profile.social_tenure
	if(current_social_tenure.is_str_party_entity(current_entity)):
		result = FetchPartySTR(profile, current_entity, id)
	if (current_social_tenure.is_str_spatial_unit_entity(current_entity)):
		result  = FetchSpUnitSTR(profile, current_entity, id)
	print('Final Result',result)
	return render(request,'dashboard/view_more.html', {'result':result,'entity':entity_short_name, 'id':id})



def FetchSpUnitSTR(profile, spu_entity, record_id):
	current_social_tenure = profile.social_tenure
	parties  = current_social_tenure.parties
	str_table_name = profile.prefix + "_social_tenure_relationship"
	tenure_type_entity =  current_social_tenure.spatial_units_tenure[spu_entity.short_name]
	tenure_type_relation = profile.parent_relations(tenure_type_entity)[0]
	tenure_type_join = 'left join '+ tenure_type_relation.parent.name +' on '+ tenure_type_relation.parent.name+'.'+tenure_type_relation.parent_column +' = ' + tenure_type_relation.child.name+'.'+tenure_type_relation.child_column+' '
	tenure_type_column = tenure_type_entity.name + '.value as ' + tenure_type_relation.child_column+','
	spu_relation = getStrRelation(profile, spu_entity, str_table_name)

	result = {}
	for party in parties:
		full_query = ''
		str_relation = getStrRelation(profile, party, str_table_name)
		joins = createParentJoins(profile, party)
		columns = GetColumns(profile, party)
		str_query = 'select '+tenure_type_column+ ",".join(columns)+ ' from '+ str_table_name+' join '+ party.name +' on ' +party.name+'.'+ str_relation.parent_column+' ='+ str_table_name+'.'+str_relation.child_column +' '+ tenure_type_join
		str_query+=joins
		full_query+=str_query
		where_clause = ' where '+ str_table_name+'.'+ spu_relation.child_column +'={};'.format(record_id)
		full_query+=where_clause
		data = queryWithColumnNames(full_query)
		print('Mambo')
		print(full_query)
		if data:
			result[party.short_name]=data
	print('Mwisho')
	return result


def FetchPartySTR(profile, party_entity, record_id):
	current_social_tenure = profile.social_tenure
	spatial_units = current_social_tenure.spatial_units
	str_table_name = profile.prefix + "_social_tenure_relationship"
	party_entity_str_relation = getStrRelation(profile, party_entity, str_table_name)
	result = {}
	for spu_unit in spatial_units:
		full_query =''
		#select * from b  bstr join be_household bh on household_id = bh.id where land_id = 45;
		str_relation = getStrRelation(profile, spu_unit, str_table_name)
		joins = createParentJoins(profile, spu_unit)
		columns = GetColumns(profile, spu_unit)
		str_query = 'select '+",".join(columns)+ ' from '+ str_table_name+' join '+ spu_unit.name +' on ' +spu_unit.name+'.'+ str_relation.parent_column+' ='+ str_table_name+'.'+str_relation.child_column
		str_query+=joins
		full_query+=str_query
		where_clause = ' where '+ str_table_name+'.'+ party_entity_str_relation.child_column +'={};'.format(record_id)
		full_query+=where_clause
		data = queryWithColumnNames(full_query)
		print('Mambo')
		print(data)
		if data:
			result[spu_unit.short_name]=data
	return result

def getStrRelation(profile, entity, str_table_name):
	for relation in profile.parent_relations(entity):
		if relation.child.name == str_table_name:
			return relation

def GetColumns(profile, entity):
	query_columns = []
	db_columns = CheckColumnInDB(entity)
	for col in entity.columns.values():
		if col.name in db_columns and col.TYPE_INFO not in ['LOOKUP', 'GEOMETRY','FOREIGN_KEY']: #, 'SERIAL'
			query_columns.append(entity.name+'.'+col.name)
	
	for en in entity.parents():
		if en.TYPE_INFO == 'VALUE_LIST':
			for relation in profile.parent_relations(en):
				value = en.name + ".value as "+ relation.child_column
				query_columns.append(value)
	return query_columns

def createParentJoins(profile, entity):
	joins = ''
	for en in entity.parents():
		en_parent_relations = profile.parent_relations(en)
		for relation in en_parent_relations:
			str_join = ''
			if (relation.parent.name == profile.prefix+'_social_tenure_relationship'):
				en_parent_relations.remove(relation)
			if (entity.name == relation.child.name and relation.parent.TYPE_INFO == 'VALUE_LIST'):
				join = 'left join '+ en.name + ' '+ en.name+' on ' + en.name+'.'+relation.parent_column +'= '+ relation.child.name+'.'+ relation.child_column
				joins += " "
				joins += join

	return joins

def queryWithColumnNames(query):
	with connection.cursor() as cursor:
		cursor.execute(query)
		data = cursor.fetchall()
		print('This is data my fren')
		print(data)
		print('Imagine')
		return [([toHeader(key[0]) for key in cursor.description], row) for row in data]


def queryStrDetails(queryString):
	with connection.cursor() as cursor:
		cursor.execute(queryString)
		data = cursor.fetchall()
		return [zip([key[0] for key in cursor.description], row) for row in data]

def queryStrDetailsSTR(queryString):
	with connection.cursor() as cursor:
		cursor.execute(queryString)
		data = cursor.fetchall()
		sorted_str = sorted(data, key=lambda x: x[0], reverse=True)
		return sorted_str

