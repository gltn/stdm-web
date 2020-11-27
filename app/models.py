from django.db import models

# Create your models here.
class Profile(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()

    def __str__(self):
        return self.name
    class Meta:
        verbose_name_plural = 'Profiles'
        




