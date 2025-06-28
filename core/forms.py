from datetime import timezone
from django import forms
from .models import Branch, BranchEmployee, Business, BusinessSettings, Coupon, Item, Party, Transaction, TransactionItem, User, UserRole
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Party
        fields = ['full_name', 'phone', 'email', 'address', 'company']
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.type = 'supplier'
        if commit:
            instance.save()
        return instance

class ProductPurchaseForm(forms.ModelForm):
    supplier_selection_type = forms.ChoiceField(
        choices=[('existing', 'Existing Supplier'), ('new', 'New Supplier')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    existing_supplier = forms.ModelChoiceField(
        queryset=Party.objects.filter(type='supplier'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    # New supplier fields
    new_supplier_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    new_supplier_phone = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    new_supplier_email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    new_supplier_address = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    new_supplier_company = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Transaction
        fields = ['branch', 'payment_method', 'payment_status', 'amount_paid',]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('supplier_selection_type') == 'existing' and not cleaned.get('existing_supplier'):
            self.add_error('existing_supplier', 'Please select a supplier.')
        if cleaned.get('supplier_selection_type') == 'new' and not cleaned.get('new_supplier_name'):
            self.add_error('new_supplier_name', 'Please enter the supplier name.')
        return cleaned

    def get_supplier(self, business):
        if self.cleaned_data['supplier_selection_type'] == 'existing':
            return self.cleaned_data['existing_supplier']
        else:
            supplier, _ = Party.objects.get_or_create(
                full_name=self.cleaned_data['new_supplier_name'],
                phone=self.cleaned_data['new_supplier_phone'],
                email=self.cleaned_data['new_supplier_email'],
                address=self.cleaned_data['new_supplier_address'],
                company=self.cleaned_data['new_supplier_company'],
                type='supplier',
                business=business
            )
            return supplier

class ProductPurchaseItemForm(forms.ModelForm):
    class Meta:
        model = TransactionItem
        fields = ['item', 'quantity', 'employee']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'employee': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        business = kwargs.pop('business', None)
        branch = kwargs.pop('branch', None)  # <-- Accept branch
        super().__init__(*args, **kwargs)
        qs = Item.objects.filter(type='product')
        if business:
            qs = qs.filter(business=business)
        self.fields['item'].queryset = qs
        # Optionally, filter employee queryset by branch if needed:
        if branch: # If a branch is selected/provided
            self.fields['employee'].queryset = BranchEmployee.objects.filter(
                branch=branch, status='active'
            ).select_related('user').order_by('user__full_name')
            self.fields['employee'].widget.attrs.pop('disabled', None) # Remove disabled if branch is set
        else:
            self.fields['employee'].queryset = BranchEmployee.objects.none()
            # self.fields['employee'].widget.attrs['disabled'] = 'disabled' # Keep disabled if no branch
            self.fields['employee'].help_text = 'Select a branch first to see employees.'


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
        fields = ['branch', 'payment_method', 'payment_status',   # <-- Add this line
            'amount_paid',]

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

class BusinessSettingsForm(forms.ModelForm):
    class Meta:
        model = BusinessSettings
        # Specify all fields you want the owner to be able to edit
        fields = [
            'enable_loyalty_point_earning',
            'loyalty_points_per_ugx_spent',
            'enable_loyalty_point_redemption',
            'loyalty_points_required_for_redemption',
            'loyalty_redemption_discount_type',
            'loyalty_redemption_discount_value',
            'loyalty_redemption_max_discount_amount',
            'loyalty_redemption_is_branch_specific',
            'enable_coupon_codes',
            'coupon_loyalty_requirement_type',
            'loyalty_min_spend_for_coupon',
            'loyalty_min_visits_for_coupon',
            'coupon_is_branch_specific',
        ]
        widgets = {
            'loyalty_redemption_discount_type': forms.RadioSelect(), # Use radio buttons for discount type
            'coupon_loyalty_requirement_type': forms.RadioSelect(), # Use radio buttons for loyalty requirement type
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.NumberInput, forms.Select, forms.EmailInput, forms.URLInput, forms.DateInput, forms.DateTimeInput, forms.Textarea)):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, forms.RadioSelect):
                # For radio select, you might need to style the container/individual items
                pass # Already handled by Bootstrap styles if applied globally or by custom CSS

        # Dynamically make fields required/optional based on enablement checkboxes
        # These will mostly be client-side handled by JS, but also good for server-side validation
        if not self.initial.get('enable_loyalty_point_earning', False):
            self.fields['loyalty_points_per_ugx_spent'].required = False
            self.fields['loyalty_points_per_ugx_spent'].widget.attrs['disabled'] = 'disabled'

        if not self.initial.get('enable_loyalty_point_redemption', False):
            self.fields['loyalty_points_required_for_redemption'].required = False
            self.fields['loyalty_points_required_for_redemption'].widget.attrs['disabled'] = 'disabled'
            self.fields['loyalty_redemption_discount_type'].required = False
            self.fields['loyalty_redemption_discount_type'].widget.attrs['disabled'] = 'disabled'
            self.fields['loyalty_redemption_discount_value'].required = False
            self.fields['loyalty_redemption_discount_value'].widget.attrs['disabled'] = 'disabled'
            self.fields['loyalty_redemption_max_discount_amount'].required = False
            self.fields['loyalty_redemption_max_discount_amount'].widget.attrs['disabled'] = 'disabled'
            self.fields['loyalty_redemption_is_branch_specific'].required = False
            self.fields['loyalty_redemption_is_branch_specific'].widget.attrs['disabled'] = 'disabled'
        
        if not self.initial.get('enable_coupon_codes', False):
            self.fields['coupon_loyalty_requirement_type'].required = False
            self.fields['coupon_loyalty_requirement_type'].widget.attrs['disabled'] = 'disabled'
            self.fields['loyalty_min_spend_for_coupon'].required = False
            self.fields['loyalty_min_spend_for_coupon'].widget.attrs['disabled'] = 'disabled'
            self.fields['loyalty_min_visits_for_coupon'].required = False
            self.fields['loyalty_min_visits_for_coupon'].widget.attrs['disabled'] = 'disabled'
            self.fields['coupon_is_branch_specific'].required = False
            self.fields['coupon_is_branch_specific'].widget.attrs['disabled'] = 'disabled'

    def clean(self):
        cleaned_data = super().clean()

        # Conditional validation based on checkboxes
        if cleaned_data.get('enable_loyalty_point_earning'):
            if not cleaned_data.get('loyalty_points_per_ugx_spent'):
                self.add_error('loyalty_points_per_ugx_spent', 'This field is required when loyalty point earning is enabled.')

        if cleaned_data.get('enable_loyalty_point_redemption'):
            if not cleaned_data.get('loyalty_points_required_for_redemption'):
                self.add_error('loyalty_points_required_for_redemption', 'This field is required when loyalty point redemption is enabled.')
            if not cleaned_data.get('loyalty_redemption_discount_value'):
                self.add_error('loyalty_redemption_discount_value', 'This field is required when loyalty point redemption is enabled.')
            
            # Additional validation for percentage type
            if cleaned_data.get('loyalty_redemption_discount_type') == 'percentage':
                value = cleaned_data.get('loyalty_redemption_discount_value')
                if value is not None and (value < 0 or value > 100):
                    self.add_error('loyalty_redemption_discount_value', 'Percentage value must be between 0 and 100.')

        if cleaned_data.get('enable_coupon_codes'):
            req_type = cleaned_data.get('coupon_loyalty_requirement_type')
            if req_type in ['min_spend', 'both', 'either'] and not cleaned_data.get('loyalty_min_spend_for_coupon'):
                self.add_error('loyalty_min_spend_for_coupon', 'Minimum spend is required for this coupon loyalty requirement type.')
            if req_type in ['min_visits', 'both', 'either'] and not cleaned_data.get('loyalty_min_visits_for_coupon'):
                self.add_error('loyalty_min_visits_for_coupon', 'Minimum visits is required for this coupon loyalty requirement type.')

        return cleaned_data
    
class CustomerForm(forms.ModelForm):
    class Meta:
        model = Party
        fields = ['gender', 'full_name', 'phone', 'email', 'address']
        widgets = {
            'address': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 150}),
        }

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        phone = cleaned_data.get('phone')

        # Exclude self when editing
        qs = Party.objects.filter(type='customer')
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if email and qs.filter(email=email).exists():
            self.add_error('email', 'A customer with this email already exists.')
        if phone and qs.filter(phone=phone).exists():
            self.add_error('phone', 'A customer with this phone number already exists.')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.type = 'customer'
        instance.loyalty_points = 0
        if commit:
            instance.save()
        return instance