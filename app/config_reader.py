import os
from stdm_config import StdmConfigurationReader, StdmConfiguration
from django.conf import settings
from .models import Configuration

def GetStdmConfig(config_type):
	#StdmConfiguration.cleanUp()	
	config = GetConfig(config_type)
	if config is None:
		return render(request, 'dashboard/no_config.html',)
	print(config)
	CONFIG_PATH = os.path.join(settings.MEDIA_ROOT, str(config.config_file))
	reader = StdmConfigurationReader(CONFIG_PATH)
	reader.load()
	return StdmConfiguration.instance()

def GetConfig(config_type):
	try:
		config = Configuration.objects.get(config_type=config_type)
	except Configuration.DoesNotExist:
		config = None
	return config