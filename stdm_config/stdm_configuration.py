"""
/***************************************************************************
Name                 : Config
Description          : Configuration classes of STDM entities.
Date                 : 22/December/2015
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
from .profile import Profile

LOGGER = logging.getLogger('stdm')


class Singleton(object):
    """
    Singleton class
    """
    def __init__(self, decorated):
        self.__decorated = decorated

    def instance(self, *args, **kwargs):
        try:
            return self._instance

        # Catch null property exception and create a new instance of the class
        except AttributeError:
            self._instance = self.__decorated(*args, **kwargs)
            return self._instance

    def __call__(self, *args, **kwargs):
        raise TypeError('Singleton must be accessed through the instance method')

    def cleanUp(self):
        del self._instance


@Singleton
class StdmConfiguration(object):
    """
    The main class containing all the stdm_config information. This
    information is grouped into profiles, where only one profile instance can
    be active in the system.
    """
    VERSION = 1.3

    def __init__(self):
        self.profiles = OrderedDict()
        self.is_null = True
        self._removed_profiles = []

        LOGGER.debug("STDM Configuration initialized.")

    def __len__(self):
        """
        Return a count of all assets in the stdm_config
        """
        count = 0
        for p in self.profiles.values():
            for e in p.entities.values():
                if e.TYPE_INFO == 'VALUE_LIST':
                    count += len(list(e.values.values()))
                count += len(e.columns)
            count += len(p.entities)
        count += len(self.profiles)
        return count

    @property
    def removed_profiles(self):
        """
        :return: Returns a list of removed profiles.
        :rtype: list(Profile)
        """
        return self._removed_profiles

    def reset_removed_profiles(self):
        """
        Clears the list of removed profiles.
        """
        self._removed_profiles = []

    def add_profile(self, profile):
        """
        Add a new profile to the collection. The name of the profile is
        checked to ensure that it is unique.
        :param profile: Profile object.
        :type profile: Profile
        """
        profile_name = str(profile.name)

        if profile_name not in self.profiles:
            self.profiles[profile_name] = profile

            LOGGER.debug('%s profile added', profile_name)

            if self.is_null:
                self.is_null = False

    def create_profile(self, name):
        """
        Creates a new profile with the given name. This stdm_config becomes
        the parent.
        :param name: Name of the profile.
        :type name: str
        :returns: Profile object which is not yet added to the collection in
        the stdm_config.
        :rtype: Profile
        """
        return Profile(name, self)

    def remove_profile(self, name):
        """
        Remove a profile with the given name from the collection.
        :param name: Name of the profile to be removed.
        :type name: str
        :returns: True if the profile was successfully removed. False if the
        profile was not found.
        :rtype: bool
        """
        if name not in self.profiles:
            LOGGER.debug('Profile named %s not found.', name)

            return False

        del_profile = self.profiles.pop(name, None)

        if len(self.profiles) == 0:
            self.is_null = True

        # Remove all references for the profile using the clone object
        if del_profile is not None:
            del_profile.on_delete()

        # Add to the list of removed profiles
        self._removed_profiles.append(del_profile)

        LOGGER.debug('%s profile removed.', name)

        return True

    def profile(self, name):
        """
        Get profile using its name.
        :param name: Name of the profile.
        :type name: str
        :returns: Return a profile with the given name if found, else None.
        :rtype: Profile
        """
        return self.profiles.get(name, None)

    def prefixes(self):
        """
        :returns: A list containing prefixes of the profiles contained in the
        collection.
        :rtype: list
        """
        return [p.prefix for p in self.profiles.values()]

    # Added in v1.7
    def prefix_from_profile_name(self, profile):
        """
        Creates profile prefix using a given profile name.
        :param profile: Profile name
        :type profile: String
        :return: Profile prefix
        :rtype: String
        """
        prefixes = self.prefixes()

        prefix = profile

        for i in range(2, len(profile)):
            curr_prefix = profile[0:i].lower()

            if curr_prefix not in prefixes:
                prefix = curr_prefix

                LOGGER.debug('Prefix determined %s for %s profile',
                             prefix.lower(), profile)

                break

        return prefix.lower()

    def _clear(self):
        """
        Resets the profile collection without syncing the operations in the
        database. Only used when loading the stdm_config from file. It
        should not be used in most circumstances.
        """
        self.profiles = OrderedDict()
        self.is_null = True

