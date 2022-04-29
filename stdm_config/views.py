from app.models import Setting
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json
from app.config_reader import GetConfig, GetStdmConfig
from .mobile_reader import FindEntitySubmissions
import xml.etree.ElementTree as ET
from collections import OrderedDict
import logging as LOGGER
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse_lazy


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
        query = "SELECT column_name FROM information_schema.columns WHERE table_name='{0}';".format(
            table_name)
        cursor.execute(query)
        result = cursor.fetchall()
        for field_name in result:
            db_columns.append(field_name[0])
    return db_columns


def checkEntity(prefix):
    db_entity_list = []
    with connection.cursor() as cursor:
        query = "SELECT table_name FROM information_schema.tables WHERE table_schema='public' and table_name like '{0}_%';".format(
            prefix)
        cursor.execute(query)
        result = cursor.fetchall()
        for entity_name in result:
            db_entity_list.append(entity_name[0])
    return db_entity_list


@login_required
# @user_passes_test(lambda u: u.is_web_user)
def STDMReader(request):
    if request.user.is_web_user:
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
                configs = Setting.objects.all().first()
                if configs:
                    if configs.default_profile in profiles_list:
                        default_profile = configs.default_profile
                    else:
                        default_profile = profiles_list[0]
            else:
                configs = Setting.objects.create(
                    default_profile=profiles_list[0])
                configs.save()
                default_profile = configs.default_profile

        profiler = stdm_config.profile(default_profile)
        LOGGER.info("Target Profile", profiler)
        str_summary = str_summaries(profiler)
        entities = GetProfileEntities(profiler)
        zipped_summaries = None
        summaries = None
        if entities:
            summaries = EntitiesCount(profiler, entities)
            zipped_summaries = zip(
                summaries["name"][:4], summaries["count"][:4], summaries["type"][:4])
        return render(request, 'dashboard/index.html', {'configs': configs, 'default_profile': default_profile, 'profiles': profiles_list, 'columns': columns, 'entities': entities, 'summaries': zipped_summaries, 'charts': summaries, 'str_summary': str_summary})
    else:
        messages.error(
            request, 'Not allowed to view this dashboard. Contact the administrator!')
        return render(request, 'dashboard/forbiden.html')


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

    # default_profile_object = [prof.prefix for prof in stdm_config.profiles.values() if prof.name == profile.name]
    # print("PREFIX", default_profile_object)
    db_entities = checkEntity(profile.prefix)
    for entity in config_entities:
        if entity.name in db_entities:
            entities.append(entity)
    return entities


def entity_summary_from_view(profile, entities):
    query = "SELECT table_name, count FROM {0}_entities_summary_view;".format(
        profile.prefix)
    with connection.cursor() as cursor:
        cursor.execute(query)
        result = cursor.fetchall()
    return [([toHeader(key[0]) for key in cursor.description], row) for row in result]


def EntitiesCount(profile, entities):
    summaries = {'name': [], 'count': [], 'type': []}
    with connection.cursor() as cursor:
        for en in entities:
            query = "SELECT count(*) FROM {0}_view".format(en.name)
            cursor.execute(query)
            counts = cursor.fetchall()
            if en in profile.social_tenure.parties:
                summaries["name"].append(en.short_name + " (Party)")
                summaries["type"].append(en.short_name)
            elif en in profile.social_tenure.spatial_units:
                summaries["name"].append(en.short_name + " (Spatial Unit)")
                summaries["type"].append(en.short_name)
            else:
                summaries["name"].append(en.short_name)
                summaries["type"].append(en.short_name)
            summaries["count"].append(counts[0][0])
    return summaries


def str_summaries(profile):
    entity_summary_from_view(profile, profile.user_entities)
    query = 'select value, count from {0}_str_summary_view;'.format(
        profile.prefix)
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
        summaries = EntitiesCount(profiler, entities)
        zipped_summaries = zip(
            summaries["name"][:4], summaries["count"][:4], summaries["type"][:4])
    return render(request, 'dashboard/profile_changes.html', {'entities': entities, 'str_summary': str_summary, 'summaries': zipped_summaries, 'charts': summaries})


@csrf_exempt
def EntityListingUpdatingView(request, profile):
    config = GetConfig("Web")
    if config is None or not config.complete:
        return render(request, 'dashboard/no_config.html',)
    stdm_config = GetStdmConfig("Web")
    profiler = stdm_config.profile(profile)
    entity_list = GetProfileEntities(profiler)
    return render(request, 'dashboard/profile_detail.html', {'entity_list': entity_list, })


def EntityLookupSummaries(profile, entity):
    lookup_columns = entity.columns_by_type_info('LOOKUP')
    results = {}
    for col in lookup_columns:
        ers = col.child_entity_relations()
        results[col.header()] = LooukupSummary(entity, ers)
    return results


def LooukupSummary(child_entity, ers):
    parent_entity = ers[0].parent
    query = 'select count(*), ' + parent_entity.name + '.value from ' + child_entity.name + ' join ' + parent_entity.name + ' on ' + \
        parent_entity.name+'.'+ers[0].parent_column + '=' + child_entity.name + \
        '.'+ers[0].child_column + ' group by ' + \
        parent_entity.name + '.value;'
    return queryStrDetailsSTR(query)


def entity_columns_to_query(entity):
    columns = []
    LOGGER.info("Entity columns %s", entity.columns.values())
    for column in entity.columns.values():
        if column not in entity.geometry_columns() and column not in entity.foreign_key_columns():
            columns.append(column.name)
    return columns


def fetch_entity_records(entity):
    columns = entity_columns_to_query(entity)
    LOGGER.info("%s columns to fetch %s", entity.name, columns)
    joined_columns = ','.join(columns)
    return "SELECT {} FROM {}_view".format(joined_columns, entity.name)


@csrf_exempt
def EntityDetailView(request, profile_name, entity_short_name):
    config = GetConfig("Web")
    if config is None or not config.complete:
        return render(request, 'dashboard/no_config.html',)
    stdm_config = GetStdmConfig("Web")
    prof = stdm_config.profile(profile_name)
    columns = []
    has_spatial_column = False
    is_str_entity = False
    errors = None
    items = None
    entity_name = None
    columns = []
    lookup_summaries = {}
    spatial_results = None

    entity = prof.entity(entity_short_name)
    try:
        if not entity:
            raise Exception(
                "{} entity was not found in {} profile".format(
                    entity_short_name, profile_name)
            )
        social_tenure = prof.social_tenure
        entity_name = entity.name

        if entity.has_geometry_column():
            has_spatial_column = True

        if social_tenure.is_str_entity(entity):
            is_str_entity = True

        with connection.cursor() as cursor:
            query = fetch_entity_records(entity)
            LOGGER.info("%s entity details full query %s",
                        entity_short_name, query)
            cursor.execute(query)
            data1 = cursor.fetchall()
            items = [zip([key[0] for key in cursor.description], row)
                     for row in data1]

            for key in cursor.description:
                columns.append(toHeader(key[0]))

        lookup_summaries = EntityLookupSummaries(prof, entity)
        spatial_results = None
        if has_spatial_column:
            spatial_results = entity_geojson(entity)
    except Exception as e:
        errors = "An exception has occured. Cause: {}".format(str(e.args))
        LOGGER.info(errors)
    LOGGER.info(items)

    return render(request, 'dashboard/entity.html', {'entity': entity, 'profile': profile_name, 'entity_name': entity_name, 'data': items, 'columns': columns, 'has_spatial_column': has_spatial_column, 'is_str_entity': is_str_entity, 'lookup_summaries': lookup_summaries, 'spatial_result': spatial_results, "errors": errors})


def entity_geojson(entity):
    """Return geosjson represantion of all rows as feature Collection if the entity supports geometry.
    Keyword arguments
    entity -- a STDM entity object
    """
    spatial_columns = entity.geometry_columns()
    for sp in spatial_columns:
        spatial_column = sp.name
        break

    query_join_columns = entity_columns_to_query(entity)

    query = "SELECT row_to_json(fc) \
			FROM \
			( SELECT 'FeatureCollection' AS TYPE, \
					array_to_json(array_agg(f)) AS features \
			FROM \
				(SELECT 'Feature' AS TYPE, \
						ST_AsGeoJSON({0}_view.{1},4326)::JSON AS geometry, \
						row_to_json( (SELECT p FROM ( SELECT {2}) AS p)) AS properties \
				FROM {0}_view) AS f) AS fc;	".format(entity.name, spatial_column, ','.join(query_join_columns))
    spatial_results = None
    with connection.cursor() as cursor:
        cursor.execute(query)
        result = cursor.fetchone()
        spatial_results = json.dumps(result[0])
    return spatial_results


@csrf_exempt
def sp_unit_geojson(request, profile_name, entity_short_name, row_id):
    """Returns a geojson representation of a single entity row as Feature if the entity has geometrycolumn.

    Keyword arguments
    profile_name-- the STDM contec=xt profile name for example KOPGT
    entity_short_name -- the config short name for the entity to query for examle Garden
    row_id-- the id of the row
    """
    config = GetConfig("Web")
    if config is None or not config.complete:
        return render(request, 'dashboard/no_config.html',)
    stdm_config = GetStdmConfig("Web")
    prof = stdm_config.profile(profile_name)
    entity = prof.entity(entity_short_name)
    if not entity.has_geometry_column():
        return None
    spatial_columns = entity.geometry_columns()
    for sp in spatial_columns:
        geometry_column = sp.name
        break
    id_column = "id"
    query = "SELECT jsonb_build_object(\
			   'type',       'Feature',\
			   'id',         {0},\
			   'geometry',   ST_AsGeoJSON({1})::jsonb,\
			   'properties', to_jsonb(row) - '{0}' - '{1}'\
		   ) FROM (SELECT * FROM {2}) row where id = {3};".format(id_column, geometry_column, entity.name, row_id)
    LOGGER.info("Geojson request query: %s", query)
    spatial_results = None
    with connection.cursor() as cursor:
        cursor.execute(query)
        result = cursor.fetchone()
        spatial_results = json.dumps(result[0])
    return render(request, 'dashboard/view_more_location.html', {'spatial_results': spatial_results})

# return JsonResponse(spatial_results, safe=False)


@csrf_exempt
def fetch_spatial_data(request, profile_name, entity_short_name):
    config = GetConfig("Web")
    if config is None or not config.complete:
        return render(request, 'dashboard/no_config.html',)
    stdm_config = GetStdmConfig("Web")
    prof = stdm_config.profile(profile_name)
    entity = prof.entity(entity_short_name)
    if not entity.has_geometry_column():
        return None
    spatial_results = entity_geojson(entity)

    return JsonResponse(spatial_results, safe=False)


@csrf_exempt
def fetch_spatial_data(request, profile_name, entity_short_name):
    config = GetConfig("Web")
    if config is None or not config.complete:
        return render(request, 'dashboard/no_config.html',)
    stdm_config = GetStdmConfig("Web")
    prof = stdm_config.profile(profile_name)
    entity = prof.entity(entity_short_name)
    if not entity.has_geometry_column():
        return None
    spatial_results = entity_geojson(entity)

    return JsonResponse(spatial_results, safe=False)


@csrf_exempt
def SummaryUpdatingView(request, profile):
    config = GetConfig("Web")
    if config is None or not config.complete:
        return render(request, 'dashboard/no_config.html',)
    stdm_config = GetStdmConfig("Web")
    entities = []
    for profiles in stdm_config.profiles.values():
        if profiles.name == profile:
            profiler = profiles
            str_summary = str_summaries(profiler)
            for entity in profiler.entities.values():
                if entity.TYPE_INFO == 'ENTITY':
                    entities.append(entity)
                    columns = []
                    for column in entity.columns.values():
                        columns.append(column.name)

    return render(request, 'dashboard/summarsy.html', {'entities': entities, 'str_summary': str_summary})


def CheckColumnInDB(entity):
    # SELECT column_name FROM information_schema.columns WHERE table_name='be_household';
    query = "SELECT column_name FROM information_schema.columns WHERE table_name='{}';".format(
        entity.name)
    cols = []
    result = []
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
        result = FetchSpUnitSTR(profile, current_entity, id)
    print('Final Result', result)
    return render(request, 'dashboard/view_more.html', {'result': result, 'entity': entity_short_name, 'id': id})


def FetchSpUnitSTR(profile, spu_entity, record_id):
    current_social_tenure = profile.social_tenure
    parties = current_social_tenure.parties
    str_table_name = profile.prefix + "_social_tenure_relationship"
    str_entity = profile.entity_by_name(str_table_name)

    spu_relation = getStrRelation(profile, spu_entity, str_table_name)

    str_columns = get_entity_columns(profile, str_entity)
    result = {}
    for party in parties:
        str_relation = getStrRelation(profile, party, str_table_name)

        party_view = party.name+'_view'
        str_query = "select {}, {}.* from {}_view left join {} on {}.{} = {}_view.{} WHERE {}_view.{}={};".format(','.join(
            str_columns), party_view, str_table_name, party_view, party_view, str_relation.parent_column, str_table_name, str_relation.child_column, str_table_name, spu_relation.child_column, record_id)

        # str_query = 'select '+tenure_type_column+ ",".join(str_columns)+ ' from '+ str_table_name+' join '+ party.name +' on ' +party.name+'.'+ str_relation.parent_column+' ='+ str_table_name+'.'+str_relation.child_column +' '+ tenure_type_join

        print("FULL QUERY", str_query)

        data = queryWithColumnNames(str_query)
        print(data)
        if data:
            result[party.short_name] = data
    return result


def FetchPartySTR(profile, party_entity, record_id):
    current_social_tenure = profile.social_tenure
    spatial_units = current_social_tenure.spatial_units
    str_table_name = profile.prefix + "_social_tenure_relationship"
    str_entity = profile.entity_by_name(str_table_name)
    party_entity_str_relation = getStrRelation(
        profile, party_entity, str_table_name)
    result = {}
    str_columns = get_entity_columns(profile, str_entity)
    for spu_unit in spatial_units:
        str_relation = getStrRelation(profile, spu_unit, str_table_name)

        spu_unit_view = spu_unit.name+'_view'
        str_query = "select {}, {}.* from {}_view left join {} on {}.{} = {}_view.{} WHERE {}_view.{}={};".format(','.join(
            str_columns), spu_unit_view, str_table_name, spu_unit_view, spu_unit_view, str_relation.parent_column, str_table_name, str_relation.child_column, str_table_name, party_entity_str_relation.child_column, record_id)

        data = queryWithColumnNames(str_query)
        print(data)
        if data:
            result[spu_unit.short_name] = data
    return result


def getStrRelation(profile, entity, str_table_name):
    for relation in profile.parent_relations(entity):
        if relation.child.name == str_table_name:
            return relation


def get_db_columns(entity):
    query = "SELECT column_name FROM information_schema.columns WHERE table_name='{}';".format(
        entity.name)
    cols = []
    result = []
    with connection.cursor() as cursor:
        cursor.execute(query)
        cols = cursor.fetchall()
    for col in cols:
        result.append(col[0])
    return result


def get_entity_columns(profile, entity):
    query_columns = []
    db_columns = CheckColumnInDB(entity)
    for col in entity.columns.values():
        # , 'SERIAL'
        if col.name in db_columns and col.TYPE_INFO not in ['GEOMETRY', 'FOREIGN_KEY', 'SERIAL']:
            query_columns.append(col.name)
    return query_columns


def createParentJoins(profile, entity):
    joins = ''
    for en in entity.parents():
        en_parent_relations = profile.parent_relations(en)
        for relation in en_parent_relations:
            if (relation.parent.name == profile.prefix+'_social_tenure_relationship'):
                en_parent_relations.remove(relation)
            if (entity.name == relation.child.name and relation.parent.TYPE_INFO == 'VALUE_LIST'):
                join = 'left join ' + en.name + ' ' + en.name+' on ' + en.name+'.' + \
                    relation.parent_column + '= ' + relation.child.name+'.' + relation.child_column
                joins += " "
                joins += join

    return joins


def queryWithColumnNames(query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        data = cursor.fetchall()
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
        query = "select array_to_json(array_agg(row_to_json(t))) from (select column_name, data_type from information_schema.columns WHERE table_name= '{0}') t;".format(
            table_name)
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
    profile_name = request.POST.get('mobile_profile', None)
    source_entity = request.POST.get('source_table', None)
    target_table = request.POST.get('target_table', None)
    column_mapping = json.loads(request.POST.get('data_fields'))
    prof = mobile_stdm_config.profile(profile_name)
    mobile_entity_name = prof.entity(source_entity)
    response = upload_mobile_data(
        profile_name, mobile_entity_name.name, target_table, column_mapping)
    messages.error(request, response)
    print('This is the message', messages.error(request, response))
    return redirect('/mobile/sync')


def table_columns_data_types(table_name):
    with connection.cursor() as cursor:
        query = "select array_to_json(array_agg(row_to_json(t))) from (select column_name, data_type from information_schema.columns WHERE table_name= '{0}') t;".format(
            table_name)
        cursor.execute(query)
        return cursor.fetchall()


def table_columns(table_name):
    with connection.cursor() as cursor:
        query = "select array_to_json(array_agg(row_to_json(t))) from (select column_name from information_schema.columns WHERE table_name= '{0}') t;".format(
            table_name)
        cursor.execute(query)
        return cursor.fetchall()


def upload_mobile_data(profile_name, mobile_entity_name, table_name, column_map):
    column_data_mapping = OrderedDict()

    submissions = read_mobile_submissions(profile_name, mobile_entity_name)
    values_clause = []

    for submission in submissions:
        for key, value in submission.items():
            print(key, " ", value)

            value_map = {}
            if key in column_map.keys():
                db_column = column_map[key]
                data_type = column_data_type(table_name, db_column)
                value_map[value] = data_type
                column_data_mapping[db_column] = value_map

        value_clause = prepare_values(table_name, column_data_mapping)
        values_clause.append(value_clause)
    columns = column_data_mapping.keys()
    query = "INSERT INTO public.{0} ({1}) VALUES {2};".format(
        table_name, ','.join(columns), ','.join(values_clause))
    print('QUERY', query)
    try:
        write_to_db(query)
        return "Success"
    except Exception as e:
        return ("Ooops ", str(e.__class__), " ocurred")


def write_to_db(query):
    with connection.cursor() as cursor:
        cursor.execute(query)


def column_data_type(table_name, column_name):
    columns_with_data_types = table_columns_data_types(table_name)
    # print("column with data types", columns_with_data_types)
    for col in columns_with_data_types[0][0]:  # [{"column_name":"id","data_type":"integer"},{"column_name":"household_number","data_type":"character varying"},{"column_name":"number_of_male","data_type":"integer"},{"column_name":"number_of_female","data_type":"integer"},{"column_name":"household_vicinity","data_type":"integer"},{"column_name":"house_use_type","data_type":"integer"},{"column_name":"house_type","data_type":"integer"},{"column_name":"tenure_type","data_type":"integer"},{"column_name":"written_tenure_agreement","data_type":"integer"},{"column_name":"form_of_agreement","data_type":"integer"},{"column_name":"house_eastings","data_type":"character varying"},{"column_name":"house_northings","data_type":"character varying"}]
        print(">>>", col)
        # {"column_name":"id","data_type":"integer"}
        if column_name in col.values():
            return col["data_type"]  # integer


def prepare_values(table_name, col_data_map):
    values_with_data_type = col_data_map.values()

    insert_value = '('
    for item in values_with_data_type:
        for value, data_type in item.items():
            if data_type in ["integer", 'numeric', 'bigint']:
                if value:
                    insert_value = insert_value + \
                        " ".join(str(value).split()) + ", "
                else:
                    insert_value = insert_value + "0, "
            elif data_type in ["character varying", "date", 'datetime', 'timestamp without time zone', 'text']:
                if value:
                    insert_value = insert_value + "'" + \
                        " ".join(str(value).split())+"',"
                else:
                    insert_value = insert_value + "' ', "
    print('Insert value', insert_value)
    insert_value = insert_value.rstrip(insert_value[-1])
    # insert_value = insert_value.rstrip(insert_value[-1])
    insert_value = insert_value + ")"
    print('Insert value', insert_value)
    return insert_value


def read_mobile_submissions(profile_name, entity_name):
    datas = []
    for file in FindEntitySubmissions(profile_name):
        submission_xml = ET.parse(file)

        submission_root = submission_xml.getroot()
        if (submission_root.tag == profile_name):
            entity_data = {}
            spatial_item = {}
            for entity in submission_root:
                if entity.tag == entity_name:
                    columns = [elem.tag for elem in entity.iter()
                               if elem is not entity]
                    for elem in entity.iter():
                        if elem is not entity:
                            spatial_item[elem.tag] = elem.text
                            if elem.tag != 'spatial_geometry':
                                entity_data[elem.tag] = elem.text
                    datas.append(entity_data)
    return datas
