from stdm_config import StdmConfigurationReader, StdmConfiguration
from app.models import Profile, Entity, ValueList, CodeValue, SocialTenure
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from stdm_config.create_model import create_model

CONFIG_PATH = '/home/sam/blackbox/STDM/Project Docs/samplestcfiles/default_configuration.xml'
reader = StdmConfigurationReader(CONFIG_PATH)
reader.load()
stdm_config = StdmConfiguration.instance()
for profile in stdm_config.profiles.values():
	# for relations in profile.relations.values():
	#     print(relations) 
	print(profile.name)
	
	if Profile.objects.filter(name=profile.name).exists():
		# raise ValidationError('Profile already exists')
		pass
	else:   
		profil = Profile.objects.create(name=profile.name,description=profile.description)
		profil.save()
		print('created profile', profile.name)    
	for entity in profile.entities.values():
		# print(entity)	
		if entity.TYPE_INFO == 'VALUE_LIST':			
			#print(entity)
			profile_instance = Profile.objects.get(name=profile.name)
			if ValueList.objects.filter(name=entity.name,profile=profile_instance).exists():
				 # raise ValidationError('Valuelist already exists')
				pass
			else:
				value_list = ValueList.objects.create(name=entity.name,profile=profile_instance)
				value_list.save()
				valuelist = ValueList.objects.get(name=entity.name, profile=profile_instance)
				if valuelist:
					for value in entity.values.values():
						print(entity.name)
						print(value.value)
						code_values = CodeValue.objects.create(code=value.code, value=value.value,valueList=valuelist)
						code_values.save()
				# create_model(entity.name, fields=None, app_label=entity.name, module='', options=None, admin_opts=None)
		if entity.TYPE_INFO == 'ENTITY_SUPPORTING_DOCUMENT':
			print(entity._doc_types_value_list.name)
			doc_reference = entity._doc_types_value_list.name
		if entity.TYPE_INFO == 'ENTITY':
			valuelist = ValueList.objects.get(name=doc_reference, profile=profile_instance)
			entity_list = Entity.objects.create(name=entity.name,shortName=entity.short_name,description=entity.description,associative=entity.is_associative,supportsDocuments=entity.supports_documents,documentTypeLookup=valuelist,profile=profile_instance)
			entity_list.save()
		if entity.TYPE_INFO == 'SOCIAL_TENURE':
			print('Social Tenure', entity.name)
		# print(entity.val)