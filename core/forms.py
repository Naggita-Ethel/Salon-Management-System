from django import forms
from core.models import Customer
from .models import Branch, Business, User, UserRole
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


class BusinessRegisterForm(UserCreationForm):
    owner_name = forms.CharField(max_length=150, label="Owner Name")
    contact = forms.CharField(max_length=15)
    business_name = forms.CharField(max_length=200)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['owner_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Create the business without number_of_branches
            Business.objects.create(
                owner=user,
                name=self.cleaned_data['business_name'],
                contact=self.cleaned_data['contact'],
            )
        return user


class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "Username",
                "class": "form-control"
            }
        ))
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Password",
                "class": "form-control"
            }
        ))

class AddEmployeeForm(forms.Form):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    full_name = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    address = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}), required=True)
    gender = forms.ChoiceField(
        choices=[('', 'Select Gender')] + [('M', 'Male'), ('F', 'Female')],
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    branch = forms.ModelChoiceField(
        queryset=None,
        empty_label='Select Branch',
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    role = forms.ChoiceField(
        choices=[('', 'Select Role')] + [
            ('receptionist', 'Receptionist'),
            ('manager', 'Manager'),
            ('cashier', 'Cashier'),
            ('hair stylist', 'Hair Stylist'),
            ('messuse', 'Messuse'),
            ('other', 'Other (Add Custom)')
        ],
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    custom_role = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter new role'})
    )
    status = forms.ChoiceField(
        choices=[('', 'Select Status')] + [('active', 'Active'), ('inactive', 'Inactive')],
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    start_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        business = kwargs.pop('business', None)
        super().__init__(*args, **kwargs)
        if business:
            self.fields['branch'].queryset = Branch.objects.filter(business=business)

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        custom_role = cleaned_data.get('custom_role')
        if role == 'other' and not custom_role:
            raise forms.ValidationError("Custom role is required when 'Other' is selected.")
        return cleaned_data
    
    
class EditEmployeeForm(forms.Form):
    username = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    full_name = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    address = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}), required=True)
    gender = forms.ChoiceField(choices=[('M', 'Male'), ('F', 'Female')], required=True, widget=forms.Select(attrs={'class': 'form-select'}))
    branch = forms.ModelChoiceField(queryset=None, empty_label=None, required=True, widget=forms.Select(attrs={'class': 'form-select'}))
    role = forms.ModelChoiceField(queryset=None, empty_label=None, required=True, widget=forms.Select(attrs={'class': 'form-select'}))
    status = forms.ChoiceField(choices=[('active', 'Active'), ('inactive', 'Inactive')], required=True, widget=forms.Select(attrs={'class': 'form-select'}))
    start_date = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        business = kwargs.pop('business', None)
        employee = kwargs.pop('employee', None)
        self.employee = employee  # Store employee for clean methods
        super().__init__(*args, **kwargs)
        if business:
            self.fields['branch'].queryset = Branch.objects.filter(business=business)
            self.fields['role'].queryset = UserRole.objects.filter(business=business)
        if employee:
            self.initial = {
                'username': employee.user.username,
                'email': employee.user.email,
                'full_name': employee.user.full_name,
                'phone': employee.user.phone or '',
                'address': employee.user.address or '',
                'gender': employee.user.gender,
                'branch': employee.branch,
                'role': employee.role,
                'status': employee.status,
                'start_date': employee.start_date,
                'end_date': employee.end_date,
            }

    def clean_username(self):
        username = self.cleaned_data['username']
        user_id = self.employee.user.id if self.employee else None
        if User.objects.filter(username=username).exclude(id=user_id).exists():
            raise ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        user_id = self.employee.user.id if self.employee else None
        if User.objects.filter(email=email).exclude(id=user_id).exists():
            raise ValidationError("This email is already in use.")
        return email