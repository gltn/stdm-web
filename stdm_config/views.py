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
from .serializer import MobileDataSerializer
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

@csrf_exempt
@api_view(['POST'])
def upload_mobile_data(request):
	data = None
	if request.method =='POST':
		mobile_data = JSONParser().parse(request)
		serializer = MobileDataSerializer(mobile_data)
		data = serializer.data

	for key, value in data:
		table_name = key
		table_data = value
		columns = []
		
		for row in table_data:
			columns = row.keys()
			values = row.values()

		query = "INSERT INTO public.{0} ({1}) VALUES {2}".format(table_name, ','.join(columns), "','".join(values))
		print("Sync Query", query)

class RowData:
	data = {}
	def add_column(self, key, value):
		self.data[key] = value

class TableData:
	data = []
	def add_row_data(self, row_data):
		self.data.append(row_data.data)

class MobileData:
	data = {}
	def add_table(self, table_name, table_data):
		self.data[table_name] = table_data

def test_data():
	row_data = RowData()
	row_data.add_column("name","Sameul Kibui")
	row_data.add_column("age","20")
	row_data.add_column("parcel","KXVRT567788")
	row_data.add_column("phone","07192456789")
	print("Row", row_data.data)
	table_data= TableData()
	table_data.add_row_data(row_data)
	table_data.add_row_data(row_data)

	print("Table", table_data.data)

	mobile = MobileData()
	mobile.add_table("person", table_data.data)
	mobile.add_table("farmer", table_data.data)
	print("Full Data", mobile.data)

def table_columns(request, table_name):
	columns = GetDatabaseColumnsForEntity(table_name)
	return JsonResponse(columns, safe=False)

def tables(request, profile_name):
	stdm_config = GetStdmConfig("Web")
	profile = stdm_config.profile(profile_name)	
	entity_list = checkEntity(profile.prefix)
	return JsonResponse(entity_list, safe=False)