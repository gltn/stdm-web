from rest_framework import serializers

class RowDataSerialize(serializers.Serializer):
    key = serializers.CharField(required=True)
    value = serializers.CharField(required=True)

class TableDataSerializer(serializers.Serializer):
    row_data = RowDataSerialize(many = True)

class MobileDataSerializer(serializers.Serializer):
    table_name = serializers.CharField(required=True)
    table_data = TableDataSerializer(required=True, many = True)