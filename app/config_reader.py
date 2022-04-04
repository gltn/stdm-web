import logging
import os
from stdm_config import StdmConfigurationReader, StdmConfiguration
from django.conf import settings
from .models import Configuration

LOGGER = logging.getLogger('stdm')

def get_stdm_config(config_type):
	"""Load the specific STM XML confoguration file by type.

	Keyword arguments:
	config_type -- the configuration type the to be leaded fot the specifi context (either mobile or web)
	"""	
	config = find_config(config_type)
	if config is None:
		return render(request, 'dashboard/no_config.html',)
	LOGGER.info(config)
	xml_config_path = os.path.join(settings.MEDIA_ROOT, str(config.config_file))
	reader = StdmConfigurationReader(xml_config_path)
	reader.load()
	return StdmConfiguration.instance()

def find_config(config_type):
	"""Find the STDM context config from the context database.

	confiG_type -- the configuration type the to be leaded fot the specifi context (either mobile or web)
	Returns a stdm web Con
	"""
	config = None
	try:
		config = Configuration.objects.get(config_type=config_type)
	except Configuration.DoesNotExist:
		LOGGER.error("Zero configuration found for %s", config_type)
	return config