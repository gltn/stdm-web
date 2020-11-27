from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import Profile
from rest_framework import serializers

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['name',]

class SpatialUnitSerializer(GeoFeatureModelSerializer):
    """ A class to serialize locations as GeoJSON compatible data """
    class Meta:
        model = 'SpatialUnit'
        geo_field = "geom"
        id_field = False
