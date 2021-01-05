from django.db import models

# Create your models here.
type_options = (
    ('Count', 'Count'),
    ('Mean', 'Mean'),
)
class Chart(models.Model):
    name = models.CharField(max_length = 100, unique = True)
    profile = models.CharField(max_length = 100, unique = True)
    entity =  models.CharField(max_length = 100)
    x_column = models.CharField(max_length = 100)
    y_column = models.CharField(max_length = 100)
    chart_type = models.CharField(max_length = 100, choices=type_options, default=type_options[0][0])

    def save(self, *args, **kwargs):
        if self.__class__.objects.count():
            self.pk = self.__class__.objects.first().pk
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    class Meta:
        verbose_name_plural = 'Chart Settings'
