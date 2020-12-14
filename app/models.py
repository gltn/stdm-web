from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField, HStoreField

def upload_logo(instance, filename):
   # return "title_images/%s" % (filename)
    return '/'.join(['logo', str(instance.site_name), filename])

# Create your models here.
class Profile(models.Model):
    name = models.CharField(max_length = 100, unique = True)
    description = models.TextField()

    def __str__(self):
        return self.name
    class Meta:
        verbose_name_plural = 'Profiles'

class Setting(models.Model):
    site_name = models.CharField(max_length=20)
    logo = models.ImageField(upload_to=upload_logo, default='static/dashboard/dist/img/logo.png')
    header_color = models.CharField(max_length=7, default='#fff')
    background_color = models.CharField(max_length=7, default='#fff')
    sidebar_color = models.CharField(max_length=7, default='#343a40')
    footer_color = models.CharField(max_length=7,default='#fff')
    default_profile = models.ForeignKey(Profile, on_delete=models.CASCADE)

    def __str__(self):
        return self.site_name
    class Meta:
        verbose_name_plural = 'Site Settings'



class UserConfig(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username
    class Meta:
        verbose_name_plural = 'User Config'


class ValueList(models.Model):
    name = models.CharField(max_length = 255)
    profile = models.ForeignKey(Profile, on_delete = models.CASCADE, related_name = 'profile')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'ValueLists'
        unique_together = ("name", "profile")

class CodeValue(models.Model):
    code = models.CharField(max_length = 25, null=True, blank=True)
    value = models.CharField(max_length = 50)
    valueList = models.ForeignKey(ValueList, on_delete = models.CASCADE, related_name = 'codeValue', null = False)

    def __str__(self):
        return self.value
    class Meta:
        unique_together = ("value", "valueList")
    
    
class Entity(models.Model):
    name = models.CharField(max_length = 100)
    shortName = models.CharField(max_length = 100)
    description  = models.TextField()
    associative = models.BooleanField()
    supportsDocuments = models.BooleanField()
    documentTypeLookup = models.ForeignKey(ValueList,on_delete = models.CASCADE, null=True, blank=True)
    profile = models.ForeignKey(Profile, related_name = 'profiles',on_delete = models.CASCADE)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Entity'
        unique_together = ('name','profile')

class EntityRelation(models.Model):
    parent = models.OneToOneField(Entity,on_delete = models.CASCADE, related_name='parent')
    child = models.OneToOneField(Entity,on_delete = models.CASCADE, related_name='child')
    name = models.CharField(max_length = 100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Entity Relation'

class Column(models.Model):
    entity = models.ForeignKey(Entity, on_delete = models.CASCADE, null = False, related_name = 'columns')
    name = models.CharField(max_length = 100)
    description = models.TextField()
    unique = models.BooleanField()
    tip = models.CharField(max_length = 255)
    rowindex = models.IntegerField()
    minimum = models.BigIntegerField() 
    maximum = models.BigIntegerField()
    index = models.BooleanField()
    searchable = models.BooleanField()
    typeInfo = models.CharField(max_length = 255) # This should be a list of the Django/Postgres Datatyle. How can we get them?
    label = models.CharField(max_length = 255)
    mandatory = models.BooleanField()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Columns'
        
class SocialTenure(models.Model):
    tenureTypeList = models.ForeignKey(CodeValue, related_name = "social_tenure", on_delete=models.CASCADE)
    supportsMultipleParties = models.BooleanField()
    validity = models.OneToOneField('Validity', on_delete=models.CASCADE)
    party = models.ManyToManyField(Entity, related_name = 'parties')
    spatialUnit = models.ForeignKey(Entity,on_delete=models.CASCADE)


class Validity(models.Model):
    startMinimum = models.DateField()
    startMaximum = models.DateField()
    endMinimum = models.DateField()
    endMaximum = models.DateField()





