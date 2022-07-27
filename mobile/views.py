import os
from stdm_config import StdmConfigurationReader, StdmConfiguration
from app.models import Setting, Configuration, KoboConfiguration
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from stdm_config.create_model import create_model
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from os import listdir, path
import xml.etree.ElementTree as ET
from collections import Counter
from stdm_config.views import toHeader
import json
from django.conf import settings
from app.config_reader import GetStdmConfig, GetConfig
from stdm_config.mobile_reader import FindEntitySubmissions
from koboextractor import KoboExtractor
import requests
from django.contrib import messages
from itertools import groupby
from operator import countOf, itemgetter


# Mobile Component
BASE_DIR_MOBILE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# config = GetConfig("Mobile")
# MOBILE_CONFIG_PATH = os.path.join(settings.MEDIA_ROOT, str(config.config_file))
# mobile_reader = StdmConfigurationReader(MOBILE_CONFIG_PATH)
# mobile_reader.load()
# mobile_stdm_config = GetStdmConfig("Mobile")
# print('Value of complete',config.complete, config.config_type)
# Mobile instances detail
instance_path = os.path.join(BASE_DIR_MOBILE, 'config/mobile_instances')
# mobile_xml_files = [path.join(instance_path, f) for f in listdir(instance_path) if f.endswith('.xml')]


def EntityData(profile_name, entity_name, entity_short_name):
    print(profile_name, entity_name, entity_short_name)
    mobile_stdm_config = GetStdmConfig("Mobile")
    datas = []
    spatial_data = []
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
                                entity_data[toHeader(elem.tag)] = elem.text
                    datas.append(entity_data)
                    spatial_data.append(spatial_item)
    prof = mobile_stdm_config.profile(profile_name)
    entity_object = prof.entity(entity_short_name)
    geojson = None
    if entity_object.has_geometry_column():
        geojson = {'type': 'FeatureCollection', 'features': []}
        for row in spatial_data:
            feature = {'type': 'Feature', 'properties': {},
                       'geometry': {'coordinates': []}}
            feature['geometry']['coordinates'] = json.dumps(
                row['spatial_geometry'])
            for prop in row:
                if prop != 'spatial_geometry':
                    feature['properties'][prop] = row[prop]
            geojson['features'].append(feature)

    return [datas, json.dumps(geojson)]


@login_required
def MobileView(request):
    config = GetConfig("Mobile")
    if config is None or not config.complete:
        return render(request, 'dashboard/no_config.html',)
    mobile_stdm_config = GetStdmConfig("Mobile")
    profiles_list = []
    entities = []
    config_entities = []
    default_profile = None
    configs = None
    for profile in mobile_stdm_config.profiles.values():
        profiles_list.append(profile.name)
    if profiles_list:
        default_profile = profiles_list[0]
        if Setting.objects.exists():
            configs = Setting.objects.all().first()
    profiler = mobile_stdm_config.profile(default_profile)
    party = profiler.social_tenure.parties[0]
    spatial_unit = profiler.social_tenure.spatial_units[0]
    config_entities.append(party)
    config_entities.append(spatial_unit)
    for entity in profiler.entities.values():
        if entity.TYPE_INFO == 'ENTITY':
            if entity.user_editable == True:
                entities.append(entity)
                if entity is not party and entity is not spatial_unit:
                    config_entities.append(entity)
    # Reading xml files
    summaries = []
    for file in FindEntitySubmissions(default_profile):
        tree = ET.parse(file)
        root = tree.getroot()
        if root.tag == default_profile:
            for child in root:
                for en in entities:
                    if child.tag != 'meta' and child.tag != 'social_tenure':
                        if child.tag == en.name:
                            summaries.append(en.short_name)
    dict_summaries = Counter(summaries)
    actual_summaries = {'name': [], 'count': []}
    for i in Counter(summaries):
        actual_summaries["name"].append(i)
        actual_summaries["count"].append(dict_summaries[i])
    zipped_summaries = zip(
        actual_summaries["name"][:4], actual_summaries["count"][:4])
    print('Zipped', actual_summaries)
    return render(request, 'dashboard/mobile.html', {'configs': configs, 'default_profile': default_profile, 'profiles': profiles_list, 'm_entities': entities, 'summaries': zipped_summaries, 'charts': actual_summaries})


@login_required
def MobileViewSync(request):

    config = GetConfig("Mobile")
    if config is None or not config.complete:
        return render(request, 'dashboard/no_config.html',)
    mobile_stdm_config = GetStdmConfig("Mobile")
    profiles_list = []
    entities = []
    config_entities = []
    default_profile = None
    configs = None

    for profile in mobile_stdm_config.profiles.values():
        profiles_list.append(profile.name)
    if profiles_list:
        default_profile = profiles_list[0]
        if Setting.objects.exists():
            configs = Setting.objects.all().first()

    profiler = mobile_stdm_config.profile(default_profile)
    party = profiler.social_tenure.parties[0]
    spatial_unit = profiler.social_tenure.spatial_units[0]
    config_entities.append(party)
    config_entities.append(spatial_unit)
    for entity in profiler.entities.values():
        if entity.TYPE_INFO == 'ENTITY':
            if entity.user_editable == True:
                entities.append(entity)
                if entity is not party and entity is not spatial_unit:
                    config_entities.append(entity)
    # Reading xml files
    summaries = []
    for file in FindEntitySubmissions(default_profile):
        tree = ET.parse(file)
        root = tree.getroot()
        if root.tag == default_profile:
            for child in root:
                for en in entities:
                    if child.tag != 'meta' and child.tag != 'social_tenure':
                        if child.tag == en.name:
                            summaries.append(en.short_name)
    dict_summaries = Counter(summaries)
    actual_summaries = {'name': [], 'count': []}
    for i in Counter(summaries):
        actual_summaries["name"].append(i)
        actual_summaries["count"].append(dict_summaries[i])
    zipped_summaries = zip(
        actual_summaries["name"][:4], actual_summaries["count"][:4])
    return render(request, 'dashboard/mobile_sync.html', {'configs': configs, 'default_profile': default_profile, 'profiles': profiles_list, 'm_entities': entities, 'summaries': zipped_summaries, 'charts': actual_summaries})


def entity_columns_with_type_given_entity_object(entity):
    entity_columns = []
    for column in entity.columns.values():
        column_data = {}
        print('Columns:', column.name, column.TYPE_INFO)
        if column not in entity.geometry_columns():
            column_data['column_name'] = column.name
            column_data['data_type'] = column.TYPE_INFO
            entity_columns.append(column_data)
    return entity_columns


def entity_columns_given_entity_object(entity):
    entity_columns = []
    for column in entity.columns.values():
        if column not in entity.geometry_columns():
            entity_columns.append(column.name)
    return entity_columns


def entity_columns_with_type_given_entity_object(entity):
    entity_columns = []
    for column in entity.columns.values():
        column_data = {}
        print('Columns:', column.name, column.TYPE_INFO)
        if column not in entity.geometry_columns():
            column_data['column_name'] = column.name
            column_data['data_type'] = column.TYPE_INFO
            entity_columns.append(column_data)
    return entity_columns


@csrf_exempt
def MobileEntityDetailView(request, profile_name, name):
    config = GetConfig("Mobile")
    if config is None or not config.complete:
        return render(request, 'dashboard/no_config.html',)
    mobile_stdm_config = GetStdmConfig("Mobile")
    entity_name = None
    entities = []
    query_columns = []
    columns = []
    has_spatial_column = None
    is_str_entity = None

    prof = mobile_stdm_config.profile(profile_name)
    entity = prof.entity(name)
    social_tenure = prof.social_tenure
    entity_name = entity.name
    entity_short_name = entity.short_name
    entities.append(entity)

    entity_columns = entity_columns_given_entity_object(entity)

    if entity.has_geometry_column():
        has_spatial_column = True
    else:
        has_spatial_column = False

    if social_tenure.is_str_entity(entity):
        is_str_entity = True

    default_entity = entities[0]
    format_query_columns = []
    for col in query_columns:
        if col in entity_columns:
            columns.append(toHeader(col))
            format_query_columns.append(col)
    returned_data = EntityData(profile_name, entity_name, entity_short_name)
    return render(request, 'dashboard/mobile_entity.html', {'default_entity': default_entity, 'profile': profile_name, 'entity_name': entity_name, 'columns': columns, 'has_spatial_column': has_spatial_column, 'is_str_entity': is_str_entity, 'data': returned_data[0], 'spatial_dataset': returned_data[1]})


@csrf_exempt
def entity_columns(request, profile_name, entity_name):
    print(profile_name, entity_name)
    mobile_stdm_config = GetStdmConfig("Mobile")
    profile = mobile_stdm_config.profile(profile_name)
    entity = profile.entity(entity_name)
    print('Tunacheki entities', entity, entity_name)
    entity_columns_list = entity_columns_with_type_given_entity_object(entity)
    print(entity_columns_list)
    return render(request, 'dashboard/mobile_entity_columns.html', {'entity_columns_list': entity_columns_list, })


@login_required
def KoboFormView(request):
    kobo_configs = KoboConfiguration.objects.all().first()
    assets_results = None
    assets = None
    if kobo_configs:
        kpi = kobo_configs.kpi_url
        token = kobo_configs.token
        kobo = KoboExtractor(token, kpi, debug=True)
        assets = kobo.list_assets()
        if assets:
            assets_results = assets['results']

    return render(request, 'dashboard/kobo_data.html', {'kobo_settings': kobo_configs, 'assets': assets_results})


KOBO_TOKEN = "4de3b0a34f2824b424cbbe93e1bd3461d6b7dac7"
KPI = "https://kobo.humanitarianresponse.info"
ASSET = "axPo5r5hcP88m5zc9n6poX"

def KoboView(request):
    kpi = request.GET.get('kpi', None)
    token = request.GET.get('token', None)
    asset_uid = request.GET.get('asset', None)
    submission_date = request.GET.get('subDate', None)
    kpi_url = kpi + "/api/v2"
    # Limit the no of rcrods fetched
    kobo = KoboExtractor(token, kpi_url, debug=True)
    asset = kobo.get_asset(asset_uid)
    choice_lists = kobo.get_choices(asset)
    questions = kobo.get_questions(asset=asset, unpack_multiples=True)
    # Get data submitted after a certain time
    if submission_date:
        new_data = kobo.get_data(asset_uid, submitted_after=submission_date)
    else:
        new_data = kobo.get_data(asset_uid)
    # print(new_data)
    new_results = kobo.sort_results_by_time(
        new_data['results'])  # Sort list by time
    labeled_results = []
    columns = []
    data_used = {}
    columns_to_check = ['group_lm2ih88/Date_of_profiling',
                        'group_km9hr22/Name_of_the_city', 'group_km9hr22/Name_of_the_settlement',
                        'group_km9hr22/Name_of_the_ward', 'group_km9hr22/Type_of_the_settlement',
                        'group_km9hr22/First_year_of_occupation', 'group_km9hr22/Reason_for_occupation',
                        'group_km9hr22/Risk_perception_level_of_the_settlement', 'group_km9hr22/Settlement_total_area',
                        'group_zh1kn53/Proportion_of_renting_population', 'group_zh1kn53/Population_of_structure_owners',
                        'group_rc8eq43/Proportion_of_land_owned_by_government', 'group_hs99t35/What_are_the_most_de_es_in_the_settlement',
                        'group_rc8eq43/Major_land_tenure_challenges', 'group_pb5nd79/Total_number_of_households', 'group_pb5nd79/Total_Population',
                        'group_pb5nd79/Number_of_males', 'group_pb5nd79/Number_of_females', 'group_km9hr22/settlement_location', 
                        'group_xf3ce54/What_are_other_major_problems_', 'group_hs99t35/Type_of_ongoing_development_projects', 
                        'group_yr55q84/Major_priorities_identified', 'group_hs99t35/Public_services_avai_le_in_the_settlement', 
                        'group_pb5nd79/Major_source_of_income', 'group_pb5nd79/Average_income_levels_per_month',
                        'group_pb5nd79/Types_of_saving_schemes_available', 'group_pb5nd79/Highest_expenditure_item_per_m', 
                        'group_hs99t35/Most_common_health_facilities', 'group_km9hr22/Were_there_cases_of_Covid_19', 'group_km9hr22/How_many_reported_cases', ]
    for result in new_results:  # new_results is a list of list of dicts
        labeled_results.append(kobo.label_result(
            unlabeled_result=result, choice_lists=choice_lists, questions=questions, unpack_multiples=True))
    n = 0
    record_results = []
    data_use = dict()
    data_use1 = []
    for rec in labeled_results:
        record_results.append(rec["results"])
    for row in record_results:
        paired = {}
        for col in columns_to_check:
            if col in row.keys():                
                col_formatted = col.split("/", 1)[1]                
                paired[col_formatted] = (row.get(col).get("answer_label")).replace(';', '\n')
            else:
                col_formatted = col.split("/", 1)[1]
                paired[col_formatted] = "-"
            # print(paired)
        data_use[n] = paired
        n += 1
    table_columns = []
    for key, value in data_use.items():
        for ky, val in value.items():
            if toHeader(ky) not in table_columns:
                table_columns.append(toHeader(ky))
    formatted_result = []    
    for key, value in data_use.items():
        record = {}
        for ky, val in value.items():
            record[ky] = val
        formatted_result.append(record)
    city_profile = []
    #sort the list of items
    formatted_result.sort(key=lambda x:x['Name_of_the_city'])
    for k, v in groupby(formatted_result, key=lambda x: x['Name_of_the_city']):
        households = 0
        counts = 0
        population = 0
        tenure_challenges = []
        public_services = []
        total_area = 0
        city_details = {}
        city_details['Name'] = k        
        for d in v:
            households += int(d['Total_number_of_households'])
            counts += 1
            total_area += float(d['Settlement_total_area'])
            population += int(d['Total_Population'])
            if d['Major_land_tenure_challenges']:
                if d['Major_land_tenure_challenges'] not in tenure_challenges:
                    tenure_challenges.append(d['Major_land_tenure_challenges'])
            if d['Public_services_avai_le_in_the_settlement']:
                if d['Public_services_avai_le_in_the_settlement'] not in public_services:
                    public_services.append(d['Public_services_avai_le_in_the_settlement'])

        city_details['Settlement_Count'] = counts
        city_details['Number_of_Households'] = households
        city_details['Total_Settlement_Area'] = total_area
        city_details['Population'] = population
        city_details['Average_household_size'] = int((population/households) if households != 0 else 0)
        city_details['Major_Tenure_Challenges'] = tenure_challenges
        city_details['Public_Services'] = public_services
        city_profile.append(city_details)


    return render(request, 'dashboard/kobo_response.html', {'data': formatted_result, 'columns': table_columns,'city_profiles':city_profile})

@ csrf_exempt
def VisualizationView(request):
    data = json.loads(request.GET.get('data'))
    return render(request, 'dashboard/mobile_data_details.html', {'data': data, })
