import os
import xml.etree.ElementTree as ET

BASE_DIR_MOBILE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
instance_path = os.path.join(BASE_DIR_MOBILE, 'config/mobile_instances')

def FindEntitySubmissions(profile_name):
	submissions =[]
	for subdir, dirs, files in os.walk(instance_path):
		for file in files:
			file_name = os.path.join(subdir, file)
			if (file_name.endswith('.xml')):
				xml = ET.parse(file_name)
				if xml.getroot().tag == profile_name:
					submissions.append(file_name)
	return submissions