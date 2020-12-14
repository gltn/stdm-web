"""
/***************************************************************************
Name                 : ConfigurationWriter
Description          : Reads/writes stdm_config object from/to file.
Date                 : 15/February/2016
copyright            : (C) 2015 by UN-Habitat and implementing partners.
                       See the accompanying file CONTRIBUTORS.txt in the root
email                : stdm@unhabitat.org
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import logging
from collections import OrderedDict
from datetime import (
    datetime
)
import os
from decimal import Decimal
import xml.etree.ElementTree as ET

from .association_entity import AssociationEntity
from .entity import (
    BaseColumn,
    ForeignKeyColumn
)
from .entity import Entity
from .entity_relation import EntityRelation
from .exception import ConfigurationException
from .profile import Profile
from .social_tenure import SocialTenure
from .stdm_configuration import StdmConfiguration
from .value_list import ValueList


LOGGER = logging.getLogger('stdm')


def date_from_string(str_val):
    """
    Converts a date in string value to the corresponding date object.
    :param str_val: Date in string.
    :type str_val: str
    :return: Returns a date object from the corresponding string value.
    :rtype: date
    """
    return datetime.strptime(str(str_val), '%Y-%m-%d').date()


def datetime_from_string(str_val):
    """
    Converts a datetime in string value to the corresponding datetime object.
    :param str_val: Datetime
    :type str_val: str
    :return: Returns a datetime object from the corresponding string value.
    :rtype: datetime
    """
    return datetime.strptime(str(str_val), '%Y-%m-%d %H:%M:%S')


def string_to_boolean(string_bool, default):
    """
    Converts string to boolean.
    :param string_bool: The string containing a boolean text.
    :type string_bool: String
    :param default: Default boolean value.
    :type default: Boolean
    :return: Converted boolean
    :rtype: Boolean
    """
    if not isinstance(string_bool, bool):
        if string_bool == '':
            result = default
        elif string_bool == None:
            result = default
        elif string_bool.lower() == 'true':
            result = True
        elif string_bool.lower() == 'false':
            result = False
        else:
            result = default
        return result
    else:
        return string_bool


class ConfigurationFileSerializer(object):
    """
    (De)serializes stdm_config object from/to a specified file object.
    """

    def __init__(self, path, parent=None):
        """
        :param path: Path to the STDM configuration file.
        :type path: str
        """
        self.path = path
        self.config = StdmConfiguration.instance()

    def load(self):
        """
        Loads the contents of the stdm_config file to the corresponding
        instance object.
        """
        if not os.path.exists(self.path):
            raise IOError('{0} does not exist. Configuration file cannot be '
                          'loaded.'.format(self.path))

        tree = ET.parse(self.path)
        config_root = tree.getroot()

        if not config_root:
            raise ConfigurationException(
                'Root element could not be initialized'
            )

        # Load stdm_config items
        self.read_xml(config_root)

    def read_xml(self, root_element):
        """
        Reads stdm_config file and loads contents into a stdm_config
        instance.
        :param root_element: Main document object containing config information.
        :type root_element: Element
        """
        # Reset items in the config file
        self.config._clear()

        # Check version
        config_version = root_element.get('version')
        if config_version:
            config_version = float(config_version)

        else:
            # Fatal error
            raise ConfigurationException('Error extracting version '
                                         'number from the '
                                         'stdm_config file.')

        # All should be good at this point so start parsing the items
        self._load_config_items(root_element)

    def _load_config_items(self, element):
        # Load profiles
        profile_elements = element.findall('Profile')
        for profile_element in profile_elements:
            profile = ProfileSerializer.read_xml(
                profile_element,
                element,
                self.config
            )

            if profile:
                profile.sort_entities()
                self.config.add_profile(profile)

            else:
                LOGGER.debug(
                    'Empty profile name in the stdm_config file, '
                    'profile cannot be loaded.'
                )


def _populate_collections_from_element(element, tag_name, collection):
    group_el = element.find(tag_name)

    if group_el:
        for child_el in list(group_el):
            if 'name' in child_el.keys():
                name = child_el.get('name')
                collection[name] = child_el


class ProfileSerializer(object):
    """
    (De)serialize profile information.
    """

    @staticmethod
    def _populate_entity_relations(element, collection):
        # Populate collection
        _populate_collections_from_element(
            element,
            'Relations',
            collection
        )

    @staticmethod
    def _populate_associations(element, collection):
        # Populate collection
        _populate_collections_from_element(
            element,
            AssociationEntitySerializer.GROUP_TAG,
            collection
        )

    @staticmethod
    def read_xml(element, config_element, configuration):
        """
        :param element: Element containing profile information.
        :type element: QDomElement
        :param config_element: Parent stdm_config element.
        :type config_element: QDomElement
        :param configuration: Current stdm_config instance.
        :type configuration: StdmConfiguration
        :return: Returns a Profile object using information contained in the
        profile element.
        :rtype: Profile
        """
        profile_name = element.get('name', '')
        if not profile_name:
            LOGGER.debug('Empty profile name. Profile will not be loaded.')

            return None

        profile = Profile(str(profile_name), configuration)

        # Set description
        description = element.get('description', '')
        profile.description = description

        '''
        Now populate the entity relations and associations for use by child
        elements.
        '''
        association_elements = {}
        entity_relation_elements = {}
        ProfileSerializer._populate_associations(element,association_elements)
        ProfileSerializer._populate_entity_relations(
            element,
            entity_relation_elements
        )

        '''
        We resort to manually loading the entities (and subclasses) which
        have no dependencies to any parents. Start with value lists.
        '''
        value_lists_el = element.find(ValueListSerializer.GROUP_TAG)
        if value_lists_el:
            ValueListSerializer.read_xml(value_lists_el, profile,
                                         association_elements,
                                         entity_relation_elements)

        deferred_elements = []

        # Process entity elements with no dependency first
        for child_element in list(element):
            child_tag_name = child_element.tag
            item_serializer = EntitySerializerCollection.handler_by_tag_name(
                child_tag_name
            )

            if child_tag_name == 'Entity':
                if not item_serializer is None:
                    # Check if element has dependency
                    if not item_serializer.has_dependency(child_element):
                        item_serializer.read_xml(child_element, profile,
                                                 association_elements,
                                                 entity_relation_elements)

                    else:
                        # Queue the item - tuple containing element and serializer
                        deferred_elements.append((child_element, item_serializer))

        # Process deferred items
        for c in deferred_elements:
            el, serializer = c[0], c[1]
            # Resolve dependency
            serializer.resolve_dependency(
                el,
                profile,
                element,
                association_elements,
                entity_relation_elements
            )

        # Set social tenure entities
        str_el = element.find('SocialTenure')
        if str_el is not None:
            SocialTenureSerializer.read_xml(str_el, profile,
                                            association_elements,
                                            entity_relation_elements)

        return profile

    @staticmethod
    def entity_element(profile_element, entity_name):
        """
        Searches the profile for an entity with the given short name.
        :param profile_element: Profile element to search.
        :type profile_element: QDomElement
        :param entity_name: Entity short name to search for.
        :rtype: str
        :return: Entity element with the corresponding short name, else None
        if not found.
        :rtype: QDomElement
        """
        e_element = None
        entity_el_list = profile_element.findall('Entity')
        for entity_element in list(entity_el_list):
            entity_attribute = entity_element.get(
                EntitySerializer.SHORT_NAME,
                ''
            )
            if entity_attribute == entity_name:
                e_element = entity_element
                break

        return e_element


class SocialTenureSerializer(object):
    """
    (De)serializes social tenure information.
    """
    PARTY = 'party'
    SPATIAL_UNIT = 'spatialUnit'
    TENURE_TYPE = 'tenureTypeList'
    LAYER_DISPLAY = 'layerDisplay'
    MULTIPARTY = 'supportsMultipleParties'
    VALIDITY_TAG = 'Validity'
    START_TAG = 'Start'
    END_TAG = 'End'
    MINIMUM = 'minimum'
    MAXIMUM = 'maximum'
    SP_TENURE_MAPPINGS = 'SpatialUnitTenureMappings'
    SP_TENURE_MAPPING = 'Mapping'
    T_TYPE_ATTRS = 'CustomAttributes'
    T_ATTRS_ENTITY = 'TenureEntity'
    ENTITY = 'entity'

    @staticmethod
    def read_xml(child_element, profile, association_elements,
                 entity_relation_elements):
        """
        Reads the social tenure attributes in the child element and set them
        in the profile.
        :param child_element: Element containing social tenure information.
        :type child_element: QDomElement
        :param profile: Profile object whose STR attributes are to be set.
        :type profile: Profile
        """
        party = str(child_element.get(
            SocialTenureSerializer.PARTY, '')
        ).strip()
        spatial_unit = str(child_element.get(
            SocialTenureSerializer.SPATIAL_UNIT, '')
        ).strip()
        layer_display = str(child_element.get(
            SocialTenureSerializer.LAYER_DISPLAY, '')
        )
        multi_party = str(child_element.get(
            SocialTenureSerializer.MULTIPARTY, '')
        )

        # Set STR attributes
        if party:
            # Get list of party names
            parties = party.split(',')
            parties = [p.strip() for p in parties]
            profile.set_social_tenure_attr(SocialTenure.PARTY, parties)

        if spatial_unit:
            # Get list of spatial unit names
            sp_units = spatial_unit.split(',')
            sp_units = [sp.strip() for sp in sp_units]
            profile.set_social_tenure_attr(
                SocialTenure.SPATIAL_UNIT,
                sp_units
            )

        if layer_display:
            profile.social_tenure.layer_display_name = layer_display

        if multi_party:
            profile.social_tenure.multi_party = _str_to_bool(multi_party)

        # Set start validity ranges
        start_min_dt = SocialTenureSerializer._read_validity_date(
            child_element,
            SocialTenureSerializer.START_TAG,
            SocialTenureSerializer.MINIMUM
        )
        start_max_dt = SocialTenureSerializer._read_validity_date(
            child_element,
            SocialTenureSerializer.START_TAG,
            SocialTenureSerializer.MAXIMUM
        )
        if not start_min_dt is None and not start_max_dt is None:
            profile.set_social_tenure_attr(
                SocialTenure.START_DATE,
                (start_min_dt, start_max_dt)
            )

        # Set end validity ranges
        end_min_dt = SocialTenureSerializer._read_validity_date(
            child_element,
            SocialTenureSerializer.END_TAG,
            SocialTenureSerializer.MINIMUM
        )
        end_max_dt = SocialTenureSerializer._read_validity_date(
            child_element,
            SocialTenureSerializer.END_TAG,
            SocialTenureSerializer.MAXIMUM
        )
        if not end_min_dt is None and not end_max_dt is None:
            profile.set_social_tenure_attr(
                SocialTenure.END_DATE,
                (end_min_dt, end_max_dt)
            )

        # Set spatial unit tenure mapping
        sp_tenure_mapping_el = child_element.find(
            SocialTenureSerializer.SP_TENURE_MAPPINGS
        )
        if sp_tenure_mapping_el is not None:
            for t_mapping_el in list(sp_tenure_mapping_el):
                sp_unit = t_mapping_el.get(
                    SocialTenureSerializer.SPATIAL_UNIT,
                    ''
                )
                tenure_list = t_mapping_el.get(
                    SocialTenureSerializer.TENURE_TYPE,
                    ''
                )
                profile.social_tenure.add_spatial_tenure_mapping(
                    sp_unit,
                    tenure_list
                )

        # Set tenure type custom attributes
        custom_attrs_ent_el = child_element.find(
            SocialTenureSerializer.T_TYPE_ATTRS
        )
        if custom_attrs_ent_el is not None:
            for custom_ent_el in list(custom_attrs_ent_el):
                t_type = custom_ent_el.get(
                    SocialTenureSerializer.TENURE_TYPE,
                    ''
                )
                custom_ent = custom_ent_el.get(
                    SocialTenureSerializer.ENTITY,
                    ''
                )
                profile.social_tenure.add_tenure_attr_custom_entity(
                    t_type,
                    custom_ent
                )

    @staticmethod
    def _read_validity_date(str_element, tag_name, min_max):
        # Returns the validity start/end minimum/maximum dates
        validity_el = str_element.find(
            SocialTenureSerializer.VALIDITY_TAG
        )
        if validity_el is None:
            return None

        if tag_name == SocialTenureSerializer.START_TAG:
            start_el = validity_el.find(
                SocialTenureSerializer.START_TAG
            )
            if start_el is None:
                return None

            if min_max in start_el.keys():
                return date_from_string(start_el.get(min_max))
            else:
                return None

        if tag_name == SocialTenureSerializer.END_TAG:
            end_el = validity_el.find(
                SocialTenureSerializer.END_TAG
            )
            if end_el is None:
                return None

            if min_max in end_el.keys():
                return date_from_string(end_el.get(min_max))
            else:
                return None

        return None


class EntitySerializerCollection(object):
    """
    Container for entity-based serializers which are registered using the
    type info of the Entity subclass.
    """
    _registry = OrderedDict()

    @classmethod
    def register(cls):
        if not hasattr(cls, 'ENTITY_TYPE_INFO'):
            return

        EntitySerializerCollection._registry[cls.ENTITY_TYPE_INFO] = cls

    @staticmethod
    def handler(type_info):
        return EntitySerializerCollection._registry.get(type_info, None)

    @classmethod
    def entry_tag_name(cls):
        if hasattr(cls, 'GROUP_TAG'):
            return cls.GROUP_TAG

        return cls.TAG_NAME

    @staticmethod
    def handler_by_tag_name(tag_name):
        handler = [s for s in EntitySerializerCollection._registry.values()
                   if s.entry_tag_name() == tag_name]

        if len(handler) == 0:
            return None

        return handler[0]

    @classmethod
    def has_dependency(cls, element):
        """
        :param element: Element containing entity information.
        :type element: QDomElement
        :return: Return True if the entity element has columns that are
        dependent on other entities such as foreign key columns.Default is
        False.
        :rtype: bool
        """
        return False

    @classmethod
    def group_element(cls, parent_node, document):
        """
        Creates a parent/group element which is then used as the parent node
        for this serializer. If no 'GROUP_TAG' class attribute is specified
        then the profile node is returned.
        :param parent_node: Parent node corresponding to the profile node,
        :type parent_node: QDomNode
        :param document: main document object.
        :type document: QDomDocument
        :return: Prent/group node fpr appending the child node created by
        this serializer.
        :rtype: QDomNode
        """
        if not hasattr(cls, 'GROUP_TAG'):
            return parent_node

        group_tag = getattr(cls, 'GROUP_TAG')

        # Search for group element and create if it does not exist
        group_element = parent_node.find(group_tag)

        if group_element:
            group_element = document.createElement(group_tag)
            parent_node.appendChild(group_element)

        return group_element


class EntitySerializer(EntitySerializerCollection):
    """
    (De)serializes entity information.
    """
    TAG_NAME = 'Entity'

    # Specify attribute names
    GLOBAL = 'global'
    SHORT_NAME = 'shortName'
    NAME = 'name'
    DESCRIPTION = 'description'
    ASSOCIATIVE = 'associative'
    EDITABLE = 'editable'
    CREATE_ID = 'createId'
    PROXY = 'proxy'
    SUPPORTS_DOCUMENTS = 'supportsDocuments'
    DOCUMENT_TYPE_LOOKUP = 'documentTypeLookup'
    ENTITY_TYPE_INFO = 'ENTITY'
    ROW_INDEX = 'rowindex'
    LABEL = 'label'
    DEPENDENCY_FLAGS = [ForeignKeyColumn.TYPE_INFO]

    @staticmethod
    def read_xml(child_element, profile, association_elements,
                 entity_relation_elements):
        """
        Reads entity information in the entity element and add to the profile.
        :param child_element: Element containing entity information.
        :type child_element: QDomElement
        :param profile: Profile object to be populated with the entity
        information.
        :type profile: Profile
        """
        short_name = str(child_element.get(
            EntitySerializer.SHORT_NAME, '')
        )
        if short_name:
            optional_args = {}

            # Check global
            is_global = str(child_element.get(
                EntitySerializer.GLOBAL, '')
            )
            if is_global:
                is_global = _str_to_bool(is_global)
                optional_args['is_global'] = is_global

            # Proxy
            proxy = str(child_element.get(
                EntitySerializer.PROXY, '')
            )
            if proxy:
                proxy = _str_to_bool(proxy)
                optional_args['is_proxy'] = proxy

            # Create ID
            create_id = str(child_element.get(
                EntitySerializer.CREATE_ID, '')
            )
            if create_id:
                create_id = _str_to_bool(create_id)
                optional_args['create_id_column'] = create_id

            # Supports documents
            supports_docs = str(child_element.get(
                EntitySerializer.SUPPORTS_DOCUMENTS, '')
            )
            if supports_docs:
                supports_docs = _str_to_bool(supports_docs)
                optional_args['supports_documents'] = supports_docs

            ent = Entity(short_name, profile, **optional_args)

            # Associative
            associative = str(child_element.get(
                EntitySerializer.ASSOCIATIVE, '')
            )
            if associative:
                associative = _str_to_bool(associative)
                ent.is_associative = associative

            # Editable
            editable = str(child_element.get(
                EntitySerializer.EDITABLE, '')
            )
            if editable:
                editable = _str_to_bool(editable)
                ent.user_editable = editable

            # Description
            description = str(child_element.get(
                EntitySerializer.DESCRIPTION, '')
            )
            ent.description = description

            # RowIndex
            row_index = str(child_element.get(
                EntitySerializer.ROW_INDEX, '')
            )
            if row_index:
                row_index = int(row_index)
                ent.row_index = row_index

            # Label
            label = str(child_element.get(
                EntitySerializer.LABEL, '')
            )
            ent.label = label

            # Add entity to the profile so that it is discoverable
            profile.add_entity(ent)

            column_elements = EntitySerializer.column_elements(child_element)

            for ce in column_elements:
                # Just validate that it is a 'Column' element
                if str(ce.tag) == 'Column':
                    '''
                    Read element and load the corresponding column object
                    into the entity.
                    '''
                    ColumnSerializerCollection.read_xml(ce, ent,
                                                        association_elements,
                                                        entity_relation_elements)

    @staticmethod
    def column_elements(entity_element):
        """
        Parses the entity element and returns a list of column elements.
        :param entity_element: Element containing entity information.
        :type entity_element: QDomElement
        :return: A list of elements containing column information.
        :rtype: list
        """
        col_els = []

        cols_group_el = entity_element.find('Columns')

        if cols_group_el is not None:
            # Populate columns in the entity
            for column_el in list(cols_group_el):
                col_els.append(column_el)

        return col_els

    @classmethod
    def has_dependency(cls, element):
        """
        :param element: Element containing entity information.
        :type element: QDomElement
        :return: Return True if the entity element has columns that are
        dependent on other entities such as foreign key columns.Default is
        False.
        :rtype: bool
        """
        dep_cols = EntitySerializer._dependency_columns(element)
        if len(dep_cols) == 0:
            return False

        return True

    @classmethod
    def _dependency_columns(cls, element):
        # Returns a list of dependency column elements
        dep_col_elements = []

        column_elements = EntitySerializer.column_elements(element)
        for ce in column_elements:
            if 'TYPE_INFO' in ce.keys():
                type_info = str(ce.get('TYPE_INFO'))

                # Check if the type info is in the flags' list
                if type_info in cls.DEPENDENCY_FLAGS:
                    dep_col_elements.append(ce)

        return dep_col_elements

    @classmethod
    def resolve_dependency(
            cls,
            element,
            profile,
            profile_element,
            association_elements,
            entity_relation_elements
    ):
        """
        Performs a depth-first addition of an entity to a profile by
        recursively cascading all related entities first.
        :param element: Element representing the entity.
        :type element: QDomElement
        :param profile: Profile object to be populated with the entity
        information.
        :type profile: Profile
        """
        dep_cols = EntitySerializer._dependency_columns(element)

        # Add entity directly if there are no dependency columns
        if len(dep_cols) == 0:
            EntitySerializer.read_xml(
                element,
                profile,
                association_elements,
                entity_relation_elements
            )

            return

        for c in dep_cols:
            # Get foreign key columns
            type_info = str(c.get('TYPE_INFO'))

            if type_info == ForeignKeyColumn.TYPE_INFO:
                # Get relation element
                er_element = ForeignKeyColumnSerializer.entity_relation_element(c)
                relation_name = str(er_element.get('name', ''))
                er_element = entity_relation_elements.get(relation_name, None)

                if er_element is not None:
                    # Get parent
                    parent = str(
                        er_element.get(
                            EntityRelationSerializer.PARENT,
                            ''
                        )
                    )

                    # Get parent entity element
                    if parent:
                        parent_element = ProfileSerializer.entity_element(
                            profile_element,
                            parent
                        )

                        if parent_element is not None:
                            # Check if parent has dependency
                            if EntitySerializer.has_dependency(parent_element):
                                # Resolve dependency
                                EntitySerializer.resolve_dependency(
                                    parent_element,
                                    profile,
                                    profile_element,
                                    association_elements,
                                    entity_relation_elements
                                )

                            # No more dependencies
                            else:
                                EntitySerializer.read_xml(
                                    parent_element,
                                    profile,
                                    association_elements,
                                    entity_relation_elements
                                )

        # Now add entity to profile
        EntitySerializer.read_xml(
            element,
            profile,
            association_elements,
            entity_relation_elements
        )


EntitySerializer.register()


class AssociationEntitySerializer(EntitySerializerCollection):
    """
    (De)serializes association entity information.
    """
    GROUP_TAG = 'Associations'
    TAG_NAME = 'Association'

    # Attribute names
    FIRST_PARENT = 'firstParent'
    SECOND_PARENT = 'secondParent'

    # Corresponding type info to (de)serialize
    ENTITY_TYPE_INFO = 'ASSOCIATION_ENTITY'

    @staticmethod
    def read_xml(element, profile, association_elements,
                 entity_relation_elements):
        """
        Reads association information from the element.
        :param child_element: Element containing association entity
        information.
        :type child_element: QDomElement
        :param profile: Profile object to be populated with the association
        entity information.
        :type profile: Profile
        :return: Association entity object.
        :rtype: AssociationEntity
        """
        ae = None

        short_name = element.get(EntitySerializer.SHORT_NAME, '')
        if short_name:
            ae = AssociationEntity(str(short_name), profile)

            first_parent = element.get(
                AssociationEntitySerializer.FIRST_PARENT, '')
            second_parent = element.get(
                AssociationEntitySerializer.SECOND_PARENT, '')

            ae.first_parent = str(first_parent)
            ae.second_parent = str(second_parent)

        return ae


AssociationEntitySerializer.register()


class ValueListSerializer(EntitySerializerCollection):
    """
    (De)serializes ValueList information.
    """
    GROUP_TAG = 'ValueLists'
    TAG_NAME = 'ValueList'
    CODE_VALUE_TAG = 'CodeValue'

    # Attribute names
    NAME = 'name'
    CV_CODE = 'code'
    CV_VALUE = 'value'

    # Corresponding type info to (de)serialize
    ENTITY_TYPE_INFO = 'VALUE_LIST'

    @staticmethod
    def read_xml(child_element, profile, association_elements,
                 entity_relation_elements):
        """
        Reads the items in the child list element and add to the profile.
        If child element is a group element then children nodes are also
        extracted.
        :param child_element: Element containing value list information.
        :type child_element: QDomElement
        :param profile: Profile object to be populated with the value list
        information.
        :type profile: Profile
        """
        value_list_elements = child_element.findall(
            ValueListSerializer.TAG_NAME
        )

        for value_list_el in value_list_elements:
            name = value_list_el.get('name', '')
            if name:
                value_list = ValueList(str(name), profile)

                # Get code values
                cd_elements = value_list_el.findall(
                    ValueListSerializer.CODE_VALUE_TAG
                )

                for cd_el in cd_elements:
                    code = cd_el.get(ValueListSerializer.CV_CODE, '')
                    value = cd_el.get(ValueListSerializer.CV_VALUE, '')

                    # Add lookup items only when value is not empty
                    if value:
                        value_list.add_value(value, code)

                # Check if the value list is for tenure types

                if name == 'check_tenure_type':
                    profile.set_social_tenure_attr(SocialTenure.SOCIAL_TENURE_TYPE,
                                                   value_list)

                elif name == 'check_social_tenure_relationship_document_type':
                    tenure_doc_type_t_name = profile.social_tenure.supporting_doc. \
                        document_type_entity.short_name
                    vl_doc_type = profile.entity(tenure_doc_type_t_name)

                    if not vl_doc_type is None:
                        vl_doc_type.copy_from(value_list, True)


                else:
                    # Add value list to the profile
                    profile.add_entity(value_list)


ValueListSerializer.register()


class EntityRelationSerializer(object):
    """
    (De)serializes EntityRelation information.
    """
    TAG_NAME = 'EntityRelation'

    NAME = 'name'
    PARENT = 'parent'
    PARENT_COLUMN = 'parentColumn'
    CHILD = 'child'
    CHILD_COLUMN = 'childColumn'
    DISPLAY_COLUMNS = 'displayColumns'
    SHOW_IN_PARENT = 'showInParent'
    SHOW_IN_CHILD = 'showInChild'

    @staticmethod
    def read_xml(element, profile, association_elements,
                 entity_relation_elements):
        """
        Reads entity relation information from the element object.
        :param element: Element object containing entity relation information.
        :type element: QDomElement
        :param profile: Profile object that the entity relations belongs to.
        :type profile: Profile
        :param association_elements: Collection of QDomElements containing
        association entity information.
        :type association_elements: dict
        :param entity_relation_elements: Collection of QDomElements
        containing entity relation information.
        :type entity_relation_elements: dict
        :return: Returns an EntityRelation object constructed from the
        information contained in the element.
        :rtype: EntityRelation
        """
        kw = {}
        kw['parent'] = str(
            element.get(EntityRelationSerializer.PARENT, '')
        )
        kw['child'] = str(
            element.get(EntityRelationSerializer.CHILD, '')
        )
        kw['parent_column'] = str(
            element.get(EntityRelationSerializer.PARENT_COLUMN, '')
        )
        kw['child_column'] = str(
            element.get(EntityRelationSerializer.CHILD_COLUMN, '')
        )
        kw['show_in_parent'] = str(
            element.get(EntityRelationSerializer.SHOW_IN_PARENT, 'True')
        )
        kw['show_in_child'] = str(
            element.get(EntityRelationSerializer.SHOW_IN_CHILD, 'True')
        )
        dc_str = str(
            element.get(EntityRelationSerializer.DISPLAY_COLUMNS, '')
        )

        if not dc_str:
            dc = []
        else:
            dc = dc_str.split(',')
        kw['display_columns'] = dc

        er = EntityRelation(profile, **kw)

        return er


class ColumnSerializerCollection(object):
    """
    Container for column-based serializers which are registered using the
    type info of the column subclass.
    """
    _registry = {}
    TAG_NAME = 'Column'

    # Attribute names
    DESCRIPTION = 'description'
    NAME = 'name'
    INDEX = 'index'
    MANDATORY = 'mandatory'
    SEARCHABLE = 'searchable'
    UNIQUE = 'unique'
    USER_TIP = 'tip'
    MINIMUM = 'minimum'
    MAXIMUM = 'maximum'
    LABEL = 'label'
    ROW_INDEX = 'rowindex'  # for ordering on a listview

    @classmethod
    def register(cls):
        if not hasattr(cls, 'COLUMN_TYPE_INFO'):
            return

        ColumnSerializerCollection._registry[cls.COLUMN_TYPE_INFO] = cls

    @staticmethod
    def handler_by_element(element):
        t_info = str(ColumnSerializerCollection.type_info(element))

        if not t_info:
            return None

        return ColumnSerializerCollection.handler(t_info)

    @staticmethod
    def type_info(element):
        return element.get('TYPE_INFO', '')

    @staticmethod
    def read_xml(element, entity, association_elements,
                 entity_relation_elements):
        column_handler = ColumnSerializerCollection.handler_by_element(
            element
        )

        if not column_handler is None:
            column_handler.read(element, entity, association_elements,
                                entity_relation_elements)

    @classmethod
    def read(cls, element, entity, association_elements,
             entity_relation_elements):
        col_type_info = str(ColumnSerializerCollection.type_info(element))
        if not col_type_info:
            return

        # Get column attributes
        name = str(element.get(ColumnSerializerCollection.NAME, ''))
        if not name:
            return

        kwargs = {}

        # Description
        description = str(
            element.get(ColumnSerializerCollection.DESCRIPTION, '')
        )
        kwargs['description'] = description

        # Index
        index = str(
            element.get(ColumnSerializerCollection.INDEX, 'False')
        )
        kwargs['index'] = _str_to_bool(index)

        # Mandatory
        mandatory = str(
            element.get(ColumnSerializerCollection.MANDATORY, 'False')
        )
        kwargs['mandatory'] = _str_to_bool(mandatory)

        # Searchable
        searchable = str(
            element.get(ColumnSerializerCollection.SEARCHABLE, 'False')
        )
        kwargs['searchable'] = _str_to_bool(searchable)

        # Unique
        unique = str(
            element.get(ColumnSerializerCollection.UNIQUE, 'False')
        )
        kwargs['unique'] = _str_to_bool(unique)

        # User tip
        user_tip = str(
            element.get(ColumnSerializerCollection.USER_TIP, '')
        )
        kwargs['user_tip'] = user_tip

        # Label
        label = str(
            element.get(ColumnSerializerCollection.LABEL, '')
        )
        kwargs['label'] = label

        # Row Index - for ordering on a viewer
        row_index = str(
            element.get(ColumnSerializerCollection.ROW_INDEX, '')
        )
        kwargs['row_index'] = row_index

        # Minimum
        if ColumnSerializerCollection.MINIMUM in element.keys():
            minimum = element.get(ColumnSerializerCollection.MINIMUM)
            '''
            The value is not set if an exception is raised. Type will
            use defaults.
            '''
            try:
                kwargs['minimum'] = cls._convert_bounds_type(minimum)
            except ValueError:
                pass

        # Maximum
        if ColumnSerializerCollection.MAXIMUM in element.keys():
            maximum = element.get(ColumnSerializerCollection.MAXIMUM)

            try:
                kwargs['maximum'] = cls._convert_bounds_type(maximum)
            except ValueError:
                pass

        # Mandatory arguments
        args = [name, entity]

        # Custom arguments provided by subclasses
        custom_args, custom_kwargs = cls._obj_args(args, kwargs, element,
                                                   association_elements,
                                                   entity_relation_elements)

        # Get column type based on type info
        column_cls = BaseColumn.column_type(col_type_info)

        if not column_cls is None:
            column = column_cls(*custom_args, **custom_kwargs)

            # Append column to the entity
            entity.add_column(column)

    @classmethod
    def _obj_args(cls, args, kwargs, element, associations, entity_relations):
        """
        To be implemented by subclasses if they want to pass additional
        or modify existing arguments in the class constructor of the given
        column type.
        Default implementation returns the default arguments that were
        specified in the function.
        """
        return args, kwargs

    @classmethod
    def _convert_bounds_type(cls, value):
        """
        Converts string value of the minimum/maximum value to the correct
        type e.g. string to date, string to int etc.
        Default implementation returns the original value as a string.
        """
        return value

    @staticmethod
    def handler(type_info):
        return ColumnSerializerCollection._registry.get(type_info, None)


class TextColumnSerializer(ColumnSerializerCollection):
    """
    (De)serializes text column type.
    """
    COLUMN_TYPE_INFO = 'TEXT'


TextColumnSerializer.register()


class VarCharColumnSerializer(ColumnSerializerCollection):
    """
    (De)serializes VarChar column type.
    """
    COLUMN_TYPE_INFO = 'VARCHAR'

    @classmethod
    def _convert_bounds_type(cls, value):
        return int(value)


VarCharColumnSerializer.register()


class TextColumnSerializer(ColumnSerializerCollection):
    """
    (De)serializes VarChar column type.
    """
    COLUMN_TYPE_INFO = 'TEXT'

    @classmethod
    def _convert_bounds_type(cls, value):
        return int(value)


TextColumnSerializer.register()


class IntegerColumnSerializer(ColumnSerializerCollection):
    """
    (De)serializes integer column type.
    """
    COLUMN_TYPE_INFO = 'INT'

    @classmethod
    def _convert_bounds_type(cls, value):
        return int(value)


IntegerColumnSerializer.register()


class DoubleColumnSerializer(ColumnSerializerCollection):
    """
    (De)serializes double column type.
    """
    COLUMN_TYPE_INFO = 'DOUBLE'
    NUMERIC_TAG = 'Numeric'
    PRECISION = 'precision'
    SCALE = 'scale'

    @classmethod
    def _obj_args(cls, args, kwargs, element, assoc_elements,
                  entity_relation_elements):
        # Get numeric properties
        numeric_el = element.find(
            DoubleColumnSerializer.NUMERIC_TAG
        )
        if numeric_el is not None:
            precision = int(
                numeric_el.get(DoubleColumnSerializer.PRECISION, '18')
            )
            scale = int(
                numeric_el.get(DoubleColumnSerializer.SCALE, '6')
            )

            # Append additional information
            kwargs['precision'] = precision
            kwargs['scale'] = scale

        return args, kwargs

    @classmethod
    def _convert_bounds_type(cls, value):
        return Decimal.from_float(float(value))


DoubleColumnSerializer.register()


class SerialColumnSerializer(ColumnSerializerCollection):
    """
    (De)serializes serial/auto-increment column type.
    """
    COLUMN_TYPE_INFO = 'SERIAL'


SerialColumnSerializer.register()


class DateColumnSerializer(ColumnSerializerCollection):
    """
    (De)serializes date column type.
    """
    COLUMN_TYPE_INFO = 'DATE'
    CURRENT_DATE = 'currentDate'

    @classmethod
    def _obj_args(cls, args, kwargs, element, assoc_elements,
                  entity_relation_elements):
        # Set current date settings
        curr_date_el = element.find(
            DateColumnSerializer.CURRENT_DATE
        )
        if curr_date_el is not None:
            current_min = _str_to_bool(curr_date_el.get(
                'minimum',
                ''
            ))
            current_max = _str_to_bool(curr_date_el.get(
                'maximum',
                ''
            ))

            # Append additional information
            kwargs['min_use_current_date'] = current_min
            kwargs['max_use_current_date'] = current_max

        return args, kwargs

    @classmethod
    def _convert_bounds_type(cls, value):
        return date_from_string(value)


DateColumnSerializer.register()


class DateTimeColumnSerializer(ColumnSerializerCollection):
    """
    (De)serializes date time column type.
    """
    COLUMN_TYPE_INFO = 'DATETIME'
    CURRENT_DATE_TIME = 'currentDateTime'

    @classmethod
    def _obj_args(cls, args, kwargs, element, assoc_elements,
                  entity_relation_elements):
        # Set current date time settings
        curr_date_time_el = element.find(
            DateTimeColumnSerializer.CURRENT_DATE_TIME
        )
        if curr_date_time_el is not None:
            current_min = _str_to_bool(curr_date_time_el.get(
                'minimum',
                ''
            ))
            current_max = _str_to_bool(curr_date_time_el.get(
                'maximum',
                ''
            ))

            # Append additional information
            kwargs['min_use_current_datetime'] = current_min
            kwargs['max_use_current_datetime'] = current_max

        return args, kwargs

    @classmethod
    def _convert_bounds_type(cls, value):
        return datetime_from_string(value)


DateTimeColumnSerializer.register()


class BooleanColumnSerializer(ColumnSerializerCollection):
    """
    (De)serializes yes/no column type.
    """
    COLUMN_TYPE_INFO = 'BOOL'


BooleanColumnSerializer.register()


class GeometryColumnSerializer(ColumnSerializerCollection):
    """
    (De)serializes geometry column type.
    """
    COLUMN_TYPE_INFO = 'GEOMETRY'
    GEOM_TAG = 'Geometry'

    # Attribute names
    SRID = 'srid'
    GEOMETRY_TYPE = 'type'
    LAYER_DISPLAY = 'layerDisplay'

    @classmethod
    def _obj_args(cls, args, kwargs, element, assoc_elements,
                  entity_relation_elements):
        # Include the geometry type and SRID in the arguments.
        geom_el = element.find(GeometryColumnSerializer.GEOM_TAG)
        if geom_el is not None:
            geom_type = int(geom_el.get(
                GeometryColumnSerializer.GEOMETRY_TYPE,
                '2'
            ))

            srid = int(geom_el.get(
                GeometryColumnSerializer.SRID,
                '4326'
            ))

            display_name = str(geom_el.get(
                GeometryColumnSerializer.LAYER_DISPLAY,
                ''
            ))

            # Append additional geometry information
            args.append(geom_type)
            kwargs['srid'] = srid
            kwargs['layer_display'] = display_name

        return args, kwargs


GeometryColumnSerializer.register()


class ForeignKeyColumnSerializer(ColumnSerializerCollection):
    """
    (De)serializes foreign key column type.
    """
    COLUMN_TYPE_INFO = 'FOREIGN_KEY'
    RELATION_TAG = 'Relation'

    @classmethod
    def entity_relation_element(cls, foreign_key_element):
        # Returns the entity relation element from a foreign key element.
        return foreign_key_element.find(
            ForeignKeyColumnSerializer.RELATION_TAG
        )

    @classmethod
    def _obj_args(cls, args, kwargs, element, assoc_elements,
                  entity_relation_elements):
        # Include entity relation information.
        relation_el = ForeignKeyColumnSerializer.entity_relation_element(
            element
        )

        if relation_el is not None:
            relation_name = str(relation_el.get('name', ''))
            er_element = entity_relation_elements.get(relation_name, None)

            if er_element is not None:
                profile = args[1].profile
                er = EntityRelationSerializer.read_xml(er_element, profile,
                                                       assoc_elements,
                                                       entity_relation_elements)

                status, msg = er.valid()
                if status:
                    # Append entity relation information
                    kwargs['entity_relation'] = er

        return args, kwargs


ForeignKeyColumnSerializer.register()


class LookupColumnSerializer(ForeignKeyColumnSerializer):
    """
    (De)serializes lookup column type.
    """
    COLUMN_TYPE_INFO = 'LOOKUP'


LookupColumnSerializer.register()


class PercentColumnSerializer(DoubleColumnSerializer):
    """
    (De)serializes percent column type.
    """
    COLUMN_TYPE_INFO = 'PERCENT'


PercentColumnSerializer.register()


class AdminSpatialUnitColumnSerializer(ForeignKeyColumnSerializer):
    """
    (De)serializes administrative spatial unit column type.
    """
    COLUMN_TYPE_INFO = 'ADMIN_SPATIAL_UNIT'

    @classmethod
    def _obj_args(cls, args, kwargs, element, assoc_elements,
                  entity_relation_elements):
        return args, kwargs


AdminSpatialUnitColumnSerializer.register()


class AutoGeneratedColumnSerializer(ColumnSerializerCollection):
    """
    (De)serializes administrative spatial unit column type.
    """
    COLUMN_TYPE_INFO = 'AUTO_GENERATED'
    CODE = 'Code'
    PREFIX_SOURCE = 'prefix_source'
    LEADING_ZERO = 'leading_zero'
    SEPARATOR = 'separator'
    COLUMNS = 'columns'
    COLUMN_SEPARATORS = 'columnSeparators'
    DISABLE_AUTO_INCREMENT = 'disableAutoIncrement'
    ENABLE_EDITING = 'enableEditing'
    HIDE_PREFIX = 'hidePrefix'

    @classmethod
    def _convert_bounds_type(cls, value):
        return int(value)

    @classmethod
    def _obj_args(cls, args, kwargs, element, assoc_elements,
                  entity_relation_elements):
        # Include the prefix_code in the arguments.
        code_ele = element.find(
            AutoGeneratedColumnSerializer.CODE
        )
        if code_ele is not None:

            prefix_source = code_ele.get(
                AutoGeneratedColumnSerializer.PREFIX_SOURCE,
                ''
            )
            columns = code_ele.get(
                AutoGeneratedColumnSerializer.COLUMNS,
                ''
            )
            column_separators = code_ele.get(
                AutoGeneratedColumnSerializer.COLUMN_SEPARATORS,
                ''
            )
            leading_zero = code_ele.get(
                AutoGeneratedColumnSerializer.LEADING_ZERO,
                ''
            )
            separator = code_ele.get(
                AutoGeneratedColumnSerializer.SEPARATOR,
                ''
            )
            disable_auto_increment = code_ele.get(
                AutoGeneratedColumnSerializer.DISABLE_AUTO_INCREMENT,
                'True'
            )
            enable_editing = code_ele.get(
                AutoGeneratedColumnSerializer.ENABLE_EDITING,
                'False'
            )
            hide_prefix = code_ele.get(
                AutoGeneratedColumnSerializer.HIDE_PREFIX,
                'False'
            )
            if not columns:
                columns = []
            else:
                columns = columns.split(',')

            if not column_separators:
                column_separators = []
            else:
                column_separators = column_separators.split(',')

            disable_auto_increment = string_to_boolean(disable_auto_increment, False)
            enable_editing = string_to_boolean(enable_editing, False)
            hide_prefix = string_to_boolean(hide_prefix, False)

            # Append prefix_source
            kwargs['prefix_source'] = prefix_source
            kwargs['columns'] = columns
            kwargs['leading_zero'] = leading_zero
            kwargs['separator'] = separator
            kwargs['disable_auto_increment'] = disable_auto_increment
            kwargs['enable_editing'] = enable_editing
            kwargs['column_separators'] = column_separators
            kwargs['hide_prefix'] = hide_prefix

        return args, kwargs


AutoGeneratedColumnSerializer.register()


class MultipleSelectColumnSerializer(ColumnSerializerCollection):
    """
    (De)serializes multiple select column type information.
    """
    COLUMN_TYPE_INFO = 'MULTIPLE_SELECT'

    ASSOCIATION_TAG = 'associationEntity'

    @classmethod
    def _obj_args(cls, args, kwargs, element, associations, entity_relations):
        # Include entity relation information.
        assoc_el = element.find(
            MultipleSelectColumnSerializer.ASSOCIATION_TAG
        )

        if assoc_el is not None:
            assoc_name = str(assoc_el.get('name', ''))
            association_element = associations.get(assoc_name, None)

            if association_element is not None:
                first_parent = str(association_element.get(
                    AssociationEntitySerializer.FIRST_PARENT, '')
                )

                if first_parent:
                    # Include the name of the first_parent table in kwargs
                    kwargs['first_parent'] = first_parent

        return args, kwargs


MultipleSelectColumnSerializer.register()


def _str_to_bool(bool_str):
    if len(bool_str) > 1:
        bool_str = bool_str[0]
    return str(bool_str).upper() == 'T'


class ExpressionColumnSerializer(ColumnSerializerCollection):
    """
    (De)serializes administrative spatial unit column type.
    """
    COLUMN_TYPE_INFO = 'EXPRESSION'

    EXPRESSION = 'expression'
    OUTPUT_DATA_TYPE = 'outputDataType'

    @classmethod
    def _convert_bounds_type(cls, value):
        return int(value)

    @classmethod
    def _obj_args(cls, args, kwargs, element, assoc_elements,
                  entity_relation_elements):
        exp_ele = element.find(
            ExpressionColumnSerializer.EXPRESSION
        )
        if exp_ele is not None:
            expression = exp_ele.get(
                ExpressionColumnSerializer.EXPRESSION,
                ''
            )
            output_data_type = exp_ele.get(
                ExpressionColumnSerializer.OUTPUT_DATA_TYPE,
                ''
            )

            kwargs['expression'] = expression
            kwargs['output_data_type'] = output_data_type

        return args, kwargs


ExpressionColumnSerializer.register()

StdmConfigurationReader = ConfigurationFileSerializer
