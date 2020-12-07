from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField

def upload_logo(instance, filename):
   # return "title_images/%s" % (filename)
    return '/'.join(['logo', str(instance.site_name), filename])

# Create your models here.
class Configuration(models.Model):
    name = models.TextField(max_length = 100)


class Profile(models.Model):
    name = models.CharField(max_length = 100, unique = True)
    description = models.TextField()
    configuration = models.ForeignKey(Configuration, on_delete = models.CASCADE, related_name = 'configuration', null=True)

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
    config = models.OneToOneField(Configuration, on_delete=models.CASCADE)

    

class ValueList(models.Model):
    name = models.TextField(max_length = 255)
    displayName = models.TextField(max_length = 255)
    codeValues = JSONField() # Example data here [{"code":"Husband", "value":"Husband"},{"code":"Wife", "value":"Wife"},{"code":"Daughter", "value":"Daughter"}]
    profile = models.ForeignKey(Profile, on_delete = models.CASCADE, related_name = 'profile')

    def __str__(self):
        return self.displayName

    class Meta:
        verbose_name_plural = 'ValueLists'

class Entity(models.Model):
    name = models.CharField(max_length = 100)
    shortName = models.CharField(max_length = 100)
    editable = models.BooleanField()
    description  = models.TextField()
    associative = models.BooleanField()
    documentTypeLookup = models.ForeignKey(ValueList,on_delete = models.CASCADE)
    supportsDocuments = models.BooleanField()
    profile = models.ForeignKey(Profile, related_name = 'profiles',on_delete = models.CASCADE)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Entity'

class EntityRelation(models.Model):
    parent = models.OneToOneField(Entity,on_delete = models.CASCADE, related_name='parent')
    child = models.OneToOneField(Entity,on_delete = models.CASCADE, related_name='child')
    name = models.CharField(max_length = 100)
    parentColumn = models.CharField(max_length = 100)
    childColumn = models.CharField(max_length = 100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Entity Relation'


        




