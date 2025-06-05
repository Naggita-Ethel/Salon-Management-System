from django import forms

from core.models import Customer

from .models import Business

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['full_name', 'phone', 'email', 'loyalty_points']


class BusinessForm(forms.ModelForm):
    class Meta:
        model = Business
        fields = ['name', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Business name'}),
            'is_active': forms.CheckboxInput(),
        }
