
from django import forms
from django.forms import ModelForm
from .models import Setting


class SettingForm(ModelForm):
	class Meta:
		model = Setting
		fields = '__all__'


	def __init__(self, *args, **kwargs):
		super(SettingForm, self).__init__(*args, **kwargs)
		for field_name, field in self.fields.items():
			field.widget.attrs['class'] = 'form-control'	