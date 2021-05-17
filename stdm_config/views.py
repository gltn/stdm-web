from app.models import Setting,Configuration
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from stdm_config.create_model import create_model
from django.http import HttpResponse,JsonResponse
from django.shortcuts import render
from django.db import connection
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json
from django.core.serializers import serialize
from app.config_reader import GetConfig, GetStdmConfig
###Added for Sync mObile data
from rest_framework.parsers import JSONParser
from rest_framework.decorators import api_view
from .mobile_reader import FindEntitySubmissions
import xml.etree.ElementTree as ET
from collections import OrderedDict
##End


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

def entity_database_columns(table_name):
	db_columns = []	
	with connection.cursor() as cursor:
		query="SELECT column_name FROM information_schema.columns WHERE table_name='{0}';".format(table_name)
		cursor.execute(query)
		result = cursor.fetchall()
		for field_name in result:			
			db_columns.append(field_name[0])	
	return db_columns
		
def checkEntity(prefix):
	db_entity_list = []
	with connection.cursor() as cursor:
		query="SELECT table_name FROM information_schema.tables WHERE table_schema='public' and table_name like '{0}_%';".format(prefix)
		print(query)
		cursor.execute(query)
		result = cursor.fetchall()
		for entity_name in result:
			db_entity_list.append(entity_name[0])	
	return db_entity_list


@login_required
def STDMReader(request):
	config = GetConfig("Web")
	if config is None or not config.complete:
		return render(request, 'dashboard/no_config.html',)
	stdm_config = GetStdmConfig("Web")
	profiles_list = []
	entities = []
	default_profile = None
	configs = None
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
			configs = Setting.objects.create(default_profile = profiles_list[0])
			configs.save()
			default_profile = configs.default_profile	

	profiler = stdm_config.profile(default_profile)
	print("Target Profile", profiler)
	str_summary = str_summaries(profiler)

	entities = GetProfileEntities(profiler)
	
	zipped_summaries = None
	summaries = None
	if entities:	
		summaries =  EntitiesCount(profiler,entities)
		zipped_summaries = zip(summaries["name"][:4],summaries["count"][:4])
	return render(request, 'dashboard/index.html', {'configs': configs,'default_profile':default_profile,'profiles':profiles_list,'columns':columns,'entities':entities,'summaries':zipped_summaries,'charts':summaries,'str_summary':str_summary})

def GetProfileEntities(profile):
	entities = []
	config_entities = []
	for party in profile.social_tenure.parties:
		config_entities.append(party)
	for spatial_unit in profile.social_tenure.spatial_units:
		config_entities.append(spatial_unit)    
			
	for entity in profile.user_entities():
		if entity not in config_entities:
			config_entities.append(entity)

	#default_profile_object = [prof.prefix for prof in stdm_config.profiles.values() if prof.name == profile.name]
	#print("PREFIX", default_profile_object)
	db_entities = checkEntity(profile.prefix)
	for entity in config_entities:
		if entity.name in db_entities:
			entities.append(entity)
	return entities
def entity_summary_from_view(profile, entities):
	query ="SELECT table_name, count FROM {0}_entities_summary_view;".format(profile.prefix)
	with connection.cursor() as cursor:
		cursor.execute(query)
		result = cursor.fetchall()
	return [([toHeader(key[0]) for key in cursor.description], row) for row in result]	
			
def EntitiesCount(profile, entities):
	summaries = {'name':[],'count':[]}
	with connection.cursor() as cursor:
		for en in entities:	
			query = "SELECT count(*) FROM {0}_view".format(en.name)
			cursor.execute(query)
			counts = cursor.fetchall()
			if en in profile.social_tenure.parties:
				summaries["name"].append(en.short_name +" (Party)")
			elif en in profile.social_tenure.spatial_units:
				summaries["name"].append(en.short_name +" (Spatial Unit)")
			else:
				summaries["name"].append(en.short_name)
			summaries["count"].append(counts[0][0])
	return summaries

def str_summaries(profile):
	entity_summary_from_view(profile, profile.user_entities)
	query = 'select value, count from {0}_str_summary_view;'.format(profile.prefix)
	return queryStrDetailsSTR(query)

@csrf_exempt
def ProfileUpdatingView(request, profile):
	config = GetConfig("Web")
	if config is None or not config.complete:
		return render(request, 'dashboard/no_config.html',)
	stdm_config = GetStdmConfig("Web")
	entities = []
	profiler = stdm_config.profile(profile)
	str_summary = str_summaries(profiler)

	entities = GetProfileEntities(profiler)

	zipped_summaries = None
	summaries = None
	if entities:	
		summaries =  EntitiesCount(profiler,entities)
		zipped_summaries = zip(summaries["name"][:4],summaries["count"][:4])
	return render(request,'dashboard/profile_changes.html', {'entities':entities, 'str_summary':str_summary, 'summaries':zipped_summaries,'charts':summaries})
	
@csrf_exempt
def EntityListingUpdatingView(request, profile):  
	config = GetConfig("Web")
	if config is None or not config.complete:
		return render(request, 'dashboard/no_config.html',)
	stdm_config = GetStdmConfig("Web")
	profiler = stdm_config.profile(profile)	
	entity_list = GetProfileEntities(profiler)				
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

def EntityRecordsQuery(profile, entity):
	return "SELECT * FROM {0}_view".format(entity.name)

@csrf_exempt
def EntityDetailView(request, profile_name,short_name):
	config = GetConfig("Web")
	if config is None or not config.complete:
		return render(request, 'dashboard/no_config.html',)
	stdm_config = GetStdmConfig("Web")
	entity_name = None
	entity_columns = []
	columns = []
	has_spatial_column = None
	is_str_entity = None
	prof = stdm_config.profile(profile_name)
	entity = prof.entity(short_name)
	social_tenure = prof.social_tenure       
	default_entity = prof.entity(short_name)
	entity_name = default_entity.name

	for column in default_entity.columns.values():
		if column not in default_entity.geometry_columns():
			entity_columns.append(column.name)

	if default_entity.has_geometry_column():
		has_spatial_column = True
	else:
		has_spatial_column = False
	
	if social_tenure.is_str_entity(default_entity):
		is_str_entity = True	
	
	query_joins = createParentJoins(prof, default_entity)

	query_join_columns = GetColumns(prof, default_entity)

	with connection.cursor() as cursor:
		
		query = EntityRecordsQuery(prof, entity)
		cursor.execute(query)
		data1 = cursor.fetchall()
		items = [zip([key[0] for key in cursor.description], row) for row in data1]
		print('Entity data loaded',data1)
		print('Entity data descriptions',items)
		
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
		db_columns = entity_database_columns(default_entity.name)
		for colu in entity.columns.values():
			other_columns.append(colu.name)
		for colm in other_columns:
			if colm in db_columns:
				columns_to_query.append(colm)
		
		columns_to_query.remove('id')
		columns_to_query.remove(str(spatial_column))
		query="SELECT row_to_json(fc) \
				FROM \
				( SELECT 'FeatureCollection' AS TYPE, \
						array_to_json(array_agg(f)) AS features \
				FROM \
					(SELECT 'Feature' AS TYPE, \
							ST_AsGeoJSON({}.{},4326)::JSON AS geometry, \
							row_to_json( (SELECT p FROM ( SELECT {}) AS p)) AS properties \
					FROM {} {}) AS f) AS fc;	".format(default_entity.name,spatial_column, ','.join(query_join_columns),default_entity.name, query_joins)
		print("SPATIAL QUERY",query)
		with connection.cursor() as cursor:
			# query = "SELECT * FROM {0}".format(spatial_entity_query)
			cursor.execute(query)
			spatial_result = cursor.fetchone()
			map_data = spatial_result[0]
			spatial_results = json.dumps(map_data)	
	return render(request,'dashboard/entity.html', {'default_entity':default_entity,'profile':profile_name,'entity_name':entity_name,'data':items,'columns':columns,'has_spatial_column':has_spatial_column,'is_str_entity':is_str_entity,'lookup_summaries':lookup_summaries, 'spatial_result':spatial_results })

@csrf_exempt
def SummaryUpdatingView(request, profile):
	config = GetConfig("Web")
	if config is None or not config.complete:
		return render(request, 'dashboard/no_config.html',)
	stdm_config = GetStdmConfig("Web")
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
	config = GetConfig("Web")
	if config is None or not config.complete:
		return render(request, 'dashboard/no_config.html',)
	stdm_config = GetStdmConfig("Web")
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
def table_columns_data_types(table_name):
	with connection.cursor() as cursor:
		query =  "select array_to_json(array_agg(row_to_json(t))) from (select column_name, data_type from information_schema.columns WHERE table_name= '{0}') t;".format(table_name)
		cursor.execute(query)
		return cursor.fetchall()

def get_table_columns(request, table_name):
	columns = table_columns_data_types(table_name)[0][0]
	print('These columns with their data types', columns)
	return JsonResponse(columns, safe=False)

def tables(request, profile_name):
	stdm_config = GetStdmConfig("Web")
	profile = stdm_config.profile(profile_name)	
	user_editable_entity_list = profile.user_entities()
	names = [user.name for user in user_editable_entity_list]
	table_list = checkEntity(profile.prefix)
	user_tables = []
	for table in table_list:
		if table in names:
			user_tables.append(table)
	return JsonResponse(user_tables, safe=False)

@csrf_exempt
def MobileSyncDataView(request):
	mobile_stdm_config = GetStdmConfig("Mobile")
	profile_name =request.POST.get('mobile_profile', None)
	source_entity =request.POST.get('source_table', None)
	target_table = request.POST.get('target_table', None)
	column_mapping = json.loads(request.POST.get('data_fields')) 
	print('verify the details',source_entity, target_table, column_mapping)
	# profile_name ='Informal_Settlement'
	# mobile_entity_name = 'in_person'
	prof = mobile_stdm_config.profile(profile_name)
	print('Profile Name', prof.name)
	mobile_entity_name = prof.entity(source_entity)
	response  = upload_mobile_data(profile_name, mobile_entity_name.name,target_table, column_mapping)
	return  JsonResponse(response, safe=False)


def table_columns_data_types(table_name):
	with connection.cursor() as cursor:
		query =  "select array_to_json(array_agg(row_to_json(t))) from (select column_name, data_type from information_schema.columns WHERE table_name= '{0}') t;".format(table_name)
		cursor.execute(query)
		return cursor.fetchall()

def table_columns(table_name):
	with connection.cursor() as cursor:
		query =  "select array_to_json(array_agg(row_to_json(t))) from (select column_name from information_schema.columns WHERE table_name= '{0}') t;".format(table_name)
		cursor.execute(query)
		return cursor.fetchall()

def upload_mobile_data(profile_name, mobile_entity_name, table_name, column_map):
	column_data_mapping = OrderedDict()
		
	submissions = read_mobile_submissions(profile_name, mobile_entity_name)
	values_clause = []
	
	for submission in submissions:
		for key, value in submission.items():
			print(key ," ", value)
		
			value_map = {}
			if key in column_map.keys():
				db_column = column_map[key]
				data_type = column_data_type(table_name, db_column)
				value_map[value] = data_type
				column_data_mapping[db_column] = value_map

		value_clause = prepare_values(table_name, column_data_mapping)
		values_clause.append(value_clause)
	columns = column_data_mapping.keys()
	query = "INSERT INTO public.{0} ({1}) VALUES {2};".format(table_name, ','.join(columns), ','.join(values_clause))
	print('QUERY', query)
	try:
		return write_to_db(query)
	except Exception as e:
		print(e)
		return ("Ooops ", str(e.__class__ )," ocurred")

def write_to_db(query):
	with connection.cursor() as cursor:
		cursor.execute(query)
	
		
def column_data_type(table_name, column_name):
	columns_with_data_types = table_columns_data_types(table_name)
	# print("column with data types", columns_with_data_types)
	for col in columns_with_data_types[0][0]: #[{"column_name":"id","data_type":"integer"},{"column_name":"household_number","data_type":"character varying"},{"column_name":"number_of_male","data_type":"integer"},{"column_name":"number_of_female","data_type":"integer"},{"column_name":"household_vicinity","data_type":"integer"},{"column_name":"house_use_type","data_type":"integer"},{"column_name":"house_type","data_type":"integer"},{"column_name":"tenure_type","data_type":"integer"},{"column_name":"written_tenure_agreement","data_type":"integer"},{"column_name":"form_of_agreement","data_type":"integer"},{"column_name":"house_eastings","data_type":"character varying"},{"column_name":"house_northings","data_type":"character varying"}]
		print(">>>", col)
		if column_name in col.values(): #{"column_name":"id","data_type":"integer"}
			return col["data_type"] # integer

def prepare_values(table_name, col_data_map):
	print("col_data_map", col_data_map)
	values_with_data_type = col_data_map.values()

	insert_value = '('
	for item in values_with_data_type:
		for value, data_type in item.items():
			if data_type in ["integer", 'numeric', 'bigint']:
				if value:
					insert_value = insert_value + " ".join(str(value).split()) +", "
				else:
					insert_value = insert_value + "0, "
			elif data_type in ["character varying", "date",'datetime','timestamp without time zone', 'text']:
				if value:
					insert_value = insert_value + "'"+ " ".join(str(value).split())+"',"
				else:
					insert_value = insert_value + "' ', "
	print('Insert value', insert_value)		
	insert_value = insert_value.rstrip(insert_value[-1])
	# insert_value = insert_value.rstrip(insert_value[-1])
	insert_value = insert_value  + ")"
	print('Insert value', insert_value)	
	return insert_value

def read_mobile_submissions(profile_name, entity_name):
	datas=[]
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
								entity_data[elem.tag] = elem.text
					datas.append(entity_data)
	return datas