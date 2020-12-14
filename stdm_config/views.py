from stdm_config import StdmConfigurationReader, StdmConfiguration
from app.models import Profile, Entity, ValueList, CodeValue, SocialTenure
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from stdm_config.create_model import create_model
from django.shortcuts import render
from django.db import connection
# from psycopg2 import connect, sql
# from psycopg2.extras import RealDictCursor

CONFIG_PATH = '/home/sam/blackbox/STDM/Project Docs/samplestcfiles/default_configuration.xml'
def STDMReader(request):
    reader = StdmConfigurationReader(CONFIG_PATH)
    reader.load()
    stdm_config = StdmConfiguration.instance()
    profiles = []    
    for profile in stdm_config.profiles.values(): 
        entities = []
        profiles.append(profile)          
        for entity in profile.entities.values():
            if entity.TYPE_INFO == 'ENTITY':
                entities.append(entity)
                columns = []
                for column in entity.columns.values():
                    columns.append(column.name)
                default_entity = entities[0]
                
    with connection.cursor() as cursor:
        query = "SELECT * FROM {0}".format(default_entity.name)
        cursor.execute(query)
        col_name = [col[0] for col in cursor.description]
        data = cursor.fetchall()
    print(entities)    
    print(default_entity.name)
    print(data)
                 

    return render(request, 'dashboard/index.html', {'profiles':profiles,'entities':entities,'default_entity':default_entity,'data':data})

