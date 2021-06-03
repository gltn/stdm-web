from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField, HStoreField
from app.storage import OverwriteStorage
from django.db import connection, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from stdm_config import StdmConfigurationReader, StdmConfiguration
import os
from django.conf import settings



def InitConfig():
	config = Configuration.objects.get(config_type='Web')
	CONFIG_PATH = os.path.join(settings.MEDIA_ROOT, str(config.config_file))
	reader = StdmConfigurationReader(CONFIG_PATH)
	reader.load()
	stdm_config = StdmConfiguration.instance()
	print(">>>>Config Path", CONFIG_PATH)
	# iterating over the ordereddict
	profiles = stdm_config.profiles
	run(profiles)

def run(profiles):
	for profile in profiles.values():
		initializeViews(profile)


def upload_logo(instance, filename):
   # return "title_images/%s" % (filename)
	return '/'.join(['stdm', str(instance.site_name), filename])


def upload_config(instance, filename):
	if instance.config_type == 'Web':
	   	return '/'.join(['config', 'configuration.stc'])
	return '/'.join(['config/mobile', 'configuration.xml'])

def STRSummaryQuery(profile):
	str = profile.social_tenure
	tenure_type = str.tenure_type_collection
	relation = profile.parent_relations(tenure_type)[0]	
	return 'select count(*) as count, ' + relation.parent.name + '.value from '+ relation.parent.name + ' join ' + relation.child.name + ' on ' + relation.child.name+'.'+relation.child_column + '='+ relation.parent.name+'.'+relation.parent_column+ ' group by '+ relation.parent.name + '.value ;'

def CursorExecuteCommit(query):
	with connection.cursor() as cursor:
		cursor.execute(query)

# def STRViews(profile):
# 	spatial_units = profile.social_tenure.spatial_units
# 	parties = proile.social_tenure.parties

# 	for sp_unit in spatial_units:
# 		CreateViewQueryString(sp_unit)
# 	for party in parties:
# 		CreateViewQueryString(sp_unit)

def CreateSTRSummaryView(profile):
	query = STRSummaryQuery(profile)
	print(query)
	view_name = profile.prefix+'_str_summary_view'
	create_materialized_view(view_name, query)

def create_materialized_view(view_name, query):
	create_view = "CREATE MATERIALIZED VIEW  IF NOT EXISTS public."+view_name+ " AS "
	finale_view_query = create_view + query
	print(finale_view_query)
	CursorExecuteCommit(finale_view_query)

def initializeViews(profile):
	for entity in profile.user_entities():
		view_name = entity.name+"_view"
		query = entity_records_query(profile, entity)
		create_materialized_view(view_name, query)
	CreateSTRSummaryView(profile)
	createEntityCountQuery(profile)
	social_tenure_relationship_view(profile)
	

def create_parent_joins(profile, entity):
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

def get_db_columns(entity):
	query="SELECT column_name FROM information_schema.columns WHERE table_name='{}';".format(entity.name)
	cols =[]
	result =[]
	with connection.cursor() as cursor:
		cursor.execute(query)
		cols = cursor.fetchall()
	for col in cols:
		result.append(col[0])
	return result

def social_tenure_relationship_view(profile):
	str_table_name = profile.prefix + "_social_tenure_relationship"
	str_entity = profile.entity_by_name(str_table_name)
	print("STR table", str_entity, str_entity.name)
	query_joins = create_parent_joins(profile, str_entity)
	print('JOINS', query_joins)

	columns = get_columns_for_str(profile, str_entity)
	print('Columns', columns)

	str_query = "select {} from {} {};".format(','.join(columns),str_table_name, query_joins)
	print('QUERY', str_query)

	create_materialized_view('str_table_name_view',str_query)

	
def append_parent_columns(profile ,entity, columns):
	for en in entity.parents():
		if en.TYPE_INFO == 'VALUE_LIST':
			for relation in profile.parent_relations(en):
				value = en.name + ".value as "+ relation.child_column
				columns.append(value)
	return columns

def get_columns(profile, entity):
	query_columns = []
	db_columns = get_db_columns(entity)
	for col in entity.columns.values():
		if col.name in db_columns and col.TYPE_INFO not in ['LOOKUP','FOREIGN_KEY']: #, 'SERIAL'
			query_columns.append(entity.name+'.'+ col.name)
	return append_parent_columns(profile ,entity, query_columns)

def get_columns_for_str(profile, entity):
	query_columns = []
	db_columns = get_db_columns(entity)
	for col in entity.columns.values():
		if col.name in db_columns and col.TYPE_INFO not in ['LOOKUP']: #, 'SERIAL'
			query_columns.append(entity.name+'.'+ col.name)

	return append_parent_columns(profile, entity, query_columns)

def entity_records_query(profile, entity):
	query_joins = create_parent_joins(profile, entity)

	query_join_columns = get_columns(profile, entity)
	# using set()
	# to remove duplicated 
	# from list 
	query_join_columns = list(set(query_join_columns))

	query = "SELECT {0} FROM {1} {2}".format(','.join(query_join_columns), entity.name, query_joins)
	print(">>>>>>Entity Querey", query)
	return query
		
def createEntityCountQuery(profile):
	view_name = profile.prefix+"_entities_summary_view"
	query = "select table_name,"+\
	   " (xpath('/row/cnt/text()', xml_count))[1]::text::int as count"+\
		" from ("+\
		 "select table_name, table_schema,"+\
				"query_to_xml(format('select count(*) as cnt from %I.%I', table_schema, table_name), false, true, '') as xml_count"+\
		 " from information_schema.tables"+\
		 " where table_schema = 'public' and table_name like '{0}%' and table_type ='BASE TABLE') t;".format(profile.prefix)
	create_materialized_view(view_name, query)


# Create your models here.
class Profile(models.Model):
	name = models.CharField(max_length = 100, unique = True)
	description = models.TextField()

	def __str__(self):
		return self.name
	class Meta:
		verbose_name_plural = 'Profiles'

config_types = (
	('Web','Web'),
	('Mobile','Mobile')
)
class Configuration(models.Model):
	config_file = models.FileField(upload_to=upload_config)
	config_type = models.CharField(max_length=10, choices=config_types)
	complete  = models.BooleanField(default=False)

	class Meta:
		verbose_name_plural = 'Configuration'

@receiver(post_save, sender=Configuration)
#@transaction.atomic
def create_views(sender, instance, **kwargs):
	if instance.config_type == 'Web':
		print('Hii inarudiwa')
		InitConfig()			
		Configuration.objects.filter(config_type="Web").update(complete=True)

class Setting(models.Model):
	site_name = models.CharField(max_length=20, default='STDM Web')
	logo = models.ImageField(upload_to=upload_logo, default='static/dashboard/dist/img/logo.png')
	header_color = models.CharField(max_length=7, default='#fff')
	background_color = models.CharField(max_length=7, default='#fff')
	sidebar_color = models.CharField(max_length=7, default='#343a40')
	footer_color = models.CharField(max_length=7,default='#fff')
	default_profile = models.CharField(max_length=50)

	def save(self, *args, **kwargs):
		if self.__class__.objects.count():
			self.pk = self.__class__.objects.first().pk
		super().save(*args, **kwargs)

	def __str__(self):
		return self.site_name
	class Meta:
		verbose_name_plural = 'Site Settings'








