from datetime import timezone
from django import forms
from .models import Branch, BranchEmployee, Business, Coupon, Item, Party, Transaction, TransactionItem, User, UserRole
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


class TransactionForm(forms.ModelForm):
    CUSTOMER_CHOICES = [
        ('existing', 'Existing Customer'),
        ('new', 'New Customer (for walk-ins or new credit customers)'),
    ]

    customer_selection_type = forms.ChoiceField(
        choices=CUSTOMER_CHOICES,
        label="Customer Type",
        initial='new',
        widget=forms.Select(attrs={'id': 'id_customer_selector'})
    )
    existing_customer = forms.ModelChoiceField(
        queryset=Party.objects.none(),
        required=False,
        label="Select Existing Customer",
        widget=forms.Select(attrs={'id': 'id_existing_customer'})
    )
    
    new_customer_name = forms.CharField(max_length=100, required=False, label="Full Name")
    new_customer_phone = forms.CharField(max_length=15, required=False, label="Phone Number")
    new_customer_email = forms.EmailField(required=False, label="Email")
    new_customer_address = forms.CharField(
        max_length=255, 
        required=False,
        label="Address",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    new_customer_gender = forms.ChoiceField(choices=User.GENDER_CHOICES, required=False, label="Gender")

    redeem_loyalty_points = forms.BooleanField(
        required=False,
        label="Redeem Loyalty Points?",
        widget=forms.CheckboxInput(attrs={'id': 'id_redeem_loyalty_points'})
    )

    coupon_code = forms.CharField(max_length=50, required=False, help_text="Enter coupon code if applicable.")
    
    class Meta:
        model = Transaction
        fields = ['branch', 'payment_method', 'is_paid']

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['branch'].queryset = Branch.objects.filter(business=user.business)
            self.fields['existing_customer'].queryset = Party.objects.filter(business=user.business, type='customer').order_by('full_name')

        if self.instance and self.instance.pk and self.instance.party:
            self.fields['customer_selection_type'].initial = 'existing'
            self.fields['existing_customer'].initial = self.instance.party.pk
            self.fields['new_customer_name'].initial = self.instance.party.full_name
            self.fields['new_customer_phone'].initial = self.instance.party.phone
            self.fields['new_customer_email'].initial = self.instance.party.email
            self.fields['new_customer_address'].initial = self.instance.party.address
            self.fields['new_customer_gender'].initial = self.instance.party.gender
            
            if self.instance.coupon:
                self.fields['coupon_code'].initial = self.instance.coupon.code
            
    def clean(self):
        cleaned_data = super().clean()
        customer_selection_type = cleaned_data.get('customer_selection_type')
        existing_customer = cleaned_data.get('existing_customer')
        new_customer_name = cleaned_data.get('new_customer_name')
        new_customer_phone = cleaned_data.get('new_customer_phone')
        
        # Validation for customer selection
        if customer_selection_type == 'existing':
            if not existing_customer:
                self.add_error('existing_customer', "Please select an existing customer.")
        elif customer_selection_type == 'new':
            if not new_customer_name:
                self.add_error('new_customer_name', "Full Name is required for a new customer.")
            
            # Phone uniqueness check
            if new_customer_phone:
                business = None
                selected_branch_id = self.data.get('branch') # Use self.data because it might not be in cleaned_data yet
                if selected_branch_id:
                    try:
                        business = Branch.objects.get(id=selected_branch_id).business
                    except Branch.DoesNotExist:
                        pass # Handled by branch field validation already
                
                if business:
                    exclude_pk = None
                    # If this form is for an existing transaction being edited, and it has a party,
                    # and that party's phone matches the new_customer_phone, exclude it from the check.
                    if self.instance and self.instance.pk and self.instance.party and self.instance.party.phone == new_customer_phone:
                        exclude_pk = self.instance.party.pk

                    if Party.objects.filter(business=business, type='customer', phone=new_customer_phone).exclude(pk=exclude_pk).exists():
                        self.add_error('new_customer_phone', "A customer with this phone number already exists. Please select them from existing customers or use a different number.")
                else:
                    # If no business could be determined (e.g., branch not selected), cannot perform phone uniqueness check accurately
                    # This might happen if branch field itself is invalid
                    pass # The view will handle overall form validity, including branch.
        else:
            self.add_error('customer_selection_type', "Invalid customer selection type.")


        # Coupon validation (initial check only)
        coupon_code = cleaned_data.get('coupon_code')
        if coupon_code:
            try:
                business = None
                selected_branch_id = self.data.get('branch')
                if selected_branch_id:
                    try:
                        business = Branch.objects.get(id=selected_branch_id).business
                    except Branch.DoesNotExist:
                        pass
                
                if business:
                    coupon = Coupon.objects.get(
                        code=coupon_code,
                        business=business,
                        is_active=True,
                        valid_from__lte=timezone.now(),
                    )
                    cleaned_data['coupon'] = coupon # Store the coupon object if valid
                else:
                    self.add_error('coupon_code', "Invalid branch selected, cannot validate coupon.")
            except Coupon.DoesNotExist:
                self.add_error('coupon_code', "Invalid or expired coupon code.")
        else:
            cleaned_data['coupon'] = None # Ensure it's explicitly None if no code

        return cleaned_data # <--- No 'customer_party' or 'party' assignment here

class TransactionItemForm(forms.ModelForm):
    item = forms.ModelChoiceField(
        queryset=Item.objects.none(), # Will be set in __init__
        required=True,
        label="Item"
    )
    employee = forms.ModelChoiceField(
        queryset=BranchEmployee.objects.none(), # Will be set in __init__
        required=False,
        label="Serviced By"
    )

    class Meta:
        model = TransactionItem
        fields = ['item', 'quantity', 'employee']

    def __init__(self, *args, **kwargs):
        business = kwargs.pop('business', None)
        branch = kwargs.pop('branch', None) # Get the branch object passed from the view

        super().__init__(*args, **kwargs)

        if business:
            self.fields['item'].queryset = Item.objects.filter(business=business).order_by('name')
        else:
            self.fields['item'].queryset = Item.objects.none()

        # Crucial for employee dropdown:
        if branch: # If a branch is selected/provided
            self.fields['employee'].queryset = BranchEmployee.objects.filter(
                branch=branch, status='active'
            ).select_related('user').order_by('user__full_name')
            self.fields['employee'].widget.attrs.pop('disabled', None) # Remove disabled if branch is set
        else:
            self.fields['employee'].queryset = BranchEmployee.objects.none()
            # self.fields['employee'].widget.attrs['disabled'] = 'disabled' # Keep disabled if no branch
            self.fields['employee'].help_text = 'Select a branch first to see employees.'


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

