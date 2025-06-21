from datetime import timezone
from django import forms
from .models import Branch, BranchEmployee, Business, Coupon, Party, Transaction, TransactionItem, User, UserRole
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

# In forms.py

class TransactionForm(forms.ModelForm):
    # Simplified customer choices
    CUSTOMER_CHOICES = [
        ('existing', 'Existing Customer'),
        ('new', 'New Customer (for walk-ins or new credit customers)'),
    ]

    customer_selection_type = forms.ChoiceField(
        choices=CUSTOMER_CHOICES,
        label="Customer Type",
        initial='new', # Default to 'new' for quick walk-in capture
        widget=forms.Select(attrs={'id': 'id_customer_selector'})
    )
    existing_customer = forms.ModelChoiceField(
        queryset=Party.objects.none(), # Populated dynamically
        required=False,
        label="Select Existing Customer",
        widget=forms.Select(attrs={'id': 'id_existing_customer'})
    )
    
    # These fields will be used for 'new' customer selection or to update details
    # Make phone required for loyalty, but not for the form submission itself,
    # rather in the clean method if loyalty is being applied.
    new_customer_name = forms.CharField(max_length=100, required=False, label="Full Name")
    new_customer_phone = forms.CharField(max_length=15, required=False, label="Phone Number") # Make it clear it's for loyalty
    new_customer_email = forms.EmailField(required=False, label="Email")
    new_customer_address = forms.CharField(widget=forms.Textarea, required=False, label="Address")
    new_customer_gender = forms.ChoiceField(choices=User.GENDER_CHOICES, required=False, label="Gender")

    coupon_code = forms.CharField(max_length=50, required=False, help_text="Enter coupon code if applicable.")
    
    # Field to select the primary employee for the entire transaction (e.g., the cashier)
    serviced_by = forms.ModelChoiceField(
        queryset=BranchEmployee.objects.none(), # Will be filtered by branch
        required=False, # Make optional if a transaction doesn't always have one main employee
        label="Main Employee Servicing"
    )

    class Meta:
        model = Transaction
        fields = [
            'branch', 'payment_method', 'is_paid',
            'customer_selection_type', 'existing_customer',
            'new_customer_name', 'new_customer_phone', 'new_customer_email',
            'new_customer_address', 'new_customer_gender',
            'coupon_code', 'serviced_by'
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['branch'].queryset = Branch.objects.filter(business=user.business)
            self.fields['existing_customer'].queryset = Party.objects.filter(business=user.business, type='customer').order_by('full_name')
            self.fields['serviced_by'].queryset = BranchEmployee.objects.filter(branch__business=user.business, status='active')

        # Initializing `serviced_by` field based on the transaction's existing value
        if self.instance and self.instance.serviced_by:
            self.initial['serviced_by'] = self.instance.serviced_by.pk

    def clean(self):
        cleaned_data = super().clean()
        customer_selection_type = cleaned_data.get('customer_selection_type')
        existing_customer = cleaned_data.get('existing_customer')
        new_customer_name = cleaned_data.get('new_customer_name')
        new_customer_phone = cleaned_data.get('new_customer_phone')
        
        party = None

        if customer_selection_type == 'existing':
            if not existing_customer:
                self.add_error('existing_customer', "Please select an existing customer.")
            party = existing_customer
        elif customer_selection_type == 'new':
            if not new_customer_name:
                self.add_error('new_customer_name', "Full Name is required for a new customer.")
            # If phone is provided, check for uniqueness for new customers to avoid duplicates
            if new_customer_phone:
                if Party.objects.filter(business=self.cleaned_data['branch'].business, type='customer', phone=new_customer_phone).exists():
                    self.add_error('new_customer_phone', "A customer with this phone number already exists. Please select them from existing customers or use a different number.")
            
            # For new customers, `party` will be created in the view.
            # For now, we store necessary info in cleaned_data:
            cleaned_data['party'] = None # Placeholder; actual Party object will be created/assigned in the view

        # Coupon validation (as previously discussed, can stay here)
        coupon_code = cleaned_data.get('coupon_code')
        if coupon_code:
            try:
                coupon = Coupon.objects.get(
                    code=coupon_code,
                    is_active=True,
                    valid_from__lte=timezone.now(),
                    valid_until__gte=timezone.now(),
                    # Add branch filtering if coupons are branch-specific
                    # branch=cleaned_data.get('branch')
                )
                
                if coupon.usage_limit is not None and coupon.times_used >= coupon.usage_limit:
                    self.add_error('coupon_code', "Coupon has reached its usage limit.")
                
                cleaned_data['coupon'] = coupon
            except Coupon.DoesNotExist:
                self.add_error('coupon_code', "Invalid or expired coupon code.")
        else:
            cleaned_data['coupon'] = None
        
        return cleaned_data

class TransactionItemForm(forms.ModelForm):
    employee = forms.ModelChoiceField(
        queryset=BranchEmployee.objects.none(), # Keep this empty by default
        required=False,
        label="Serviced By"
    )

    class Meta:
        model = TransactionItem
        fields = ['item', 'quantity', 'employee']

    def __init__(self, *args, **kwargs):
        # Remove branch_id from kwargs.pop('branch_id', None)
        super().__init__(*args, **kwargs)

        # For existing transaction items (e.g., if you were editing a saved transaction)
        # We can still keep this for the *display* of existing data,
        # but for new forms, JS will handle it.
        # However, to avoid the error on GET, if `self.instance` exists but has no `transaction`,
        # we still want a safe default.
        if self.instance and self.instance.pk: # Only if it's a *saved* instance
            if self.instance.transaction and self.instance.transaction.branch:
                self.fields['employee'].queryset = BranchEmployee.objects.filter(
                    branch=self.instance.transaction.branch, status='active'
                )
            else:
                # If an existing item somehow has no transaction or branch, fall back to empty
                self.fields['employee'].queryset = BranchEmployee.objects.none()
        else:
            # For new, unsaved forms (both on GET and dynamically added via JS)
            # The queryset remains empty. JavaScript will populate it.
            self.fields['employee'].queryset = BranchEmployee.objects.none()
            # It's good practice to disable the field until a branch is selected
            self.fields['employee'].widget.attrs['disabled'] = 'disabled'


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

