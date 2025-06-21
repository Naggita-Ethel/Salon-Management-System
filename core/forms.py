from django import forms
from .models import Branch, Business, Party, Transaction, TransactionItem, User, UserRole
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

class TransactionForm(forms.ModelForm):
    NEW_CUSTOMER = 'new_customer'
    WALKIN = 'walkin'

    customer_field = forms.ChoiceField(
        label='Customer',
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_customer_selector'})
    )

    new_customer_name = forms.CharField(required=False)
    new_customer_phone = forms.CharField(required=False)
    new_customer_address = forms.CharField(required=False)
    new_customer_gender = forms.ChoiceField(
        required=False,
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')]
    )

    amount = forms.DecimalField(required=False, disabled=True)

    class Meta:
        model = Transaction
        fields = ['branch', 'payment_method', 'is_paid']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Dynamically load customer choices
        customer_choices = [
            (self.WALKIN, 'Walk-in'),
            (self.NEW_CUSTOMER, 'Create New Customer'),
        ] + [
            (str(p.id), p.full_name)
            for p in Party.objects.filter(type='customer')
        ]

        self.fields['customer_field'].choices = customer_choices


class TransactionItemForm(forms.ModelForm):
    class Meta:
        model = TransactionItem
        fields = ['item', 'quantity']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }

TransactionItemFormSet = forms.inlineformset_factory(
    Transaction,
    TransactionItem,
    form=TransactionItemForm,
    extra=1,
    can_delete=True,
)

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

