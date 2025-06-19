from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.forms import ValidationError
from django.utils import timezone
from django.core.validators import MinValueValidator

class User(AbstractUser):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)  # Added for employee address
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        
    )
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)  # Added for gender

    def __str__(self):
        return self.full_name or self.username


class Business(models.Model):
    name = models.CharField(max_length=100)
    owner = models.OneToOneField(User, on_delete=models.CASCADE)
    contact = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def number_of_branches(self):
        return self.branches.count()

    
class Branch(models.Model):
    business = models.ForeignKey(Business, related_name='branches', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    location = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('business', 'name', 'location')  # Unique within a business

    def __str__(self):
        return f"{self.business.name} - {self.name}"

class Item(models.Model):
    ITEM_TYPES = (
        ('service', 'Service'),
        ('product', 'Product'),
    )
    business = models.ForeignKey('Business', on_delete=models.CASCADE, related_name='items')
    type = models.CharField(max_length=20, choices=ITEM_TYPES)
    name = models.CharField(max_length=100)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.0)])
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.0)])

    class Meta:
        unique_together = ('business', 'name', 'type')  # Unique name per type per business

    def __str__(self):
        return f"{self.name} ({self.get_type_display()} at {self.business.name})"

class UserRole(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='roles')
    name = models.CharField(max_length=50)  # e.g., Manager, Receptionist

    def __str__(self):
        return f"{self.business.name} - {self.name}"
    
class BranchEmployee(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='employees')
    role = models.ForeignKey(UserRole, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    assigned_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'branch', 'role')

    def __str__(self):
        return f"{self.user.full_name} as {self.role.name} at {self.branch.name}"

class Party(models.Model):
    TYPE_CHOICES = [
        ('customer', 'Customer'),
        ('supplier', 'Supplier'),
    ]

    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    branch = models.ForeignKey('Branch', on_delete=models.CASCADE, null=True, blank=True)  # Optional if supplier may not be branch-specific
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    company = models.CharField(max_length=150, blank=True, null=True)  # Used mainly for suppliers
    loyalty_points = models.IntegerField(default=0)  # Used mainly for customers
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.type == 'supplier' and self.company:
            return f"{self.full_name} ({self.company})"
        return self.full_name



class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('revenue', 'Customer Purchase'),  # money coming in
        ('expense', 'Expense'),             # money going out
    ]

    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Card', 'Card'),
        ('MobileMoney', 'Mobile Money'),
    ]

    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)

    branch = models.ForeignKey('Branch', on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)

    party = models.ForeignKey('Party', on_delete=models.SET_NULL, null=True, blank=True)
    expense_category = models.ForeignKey('ExpenseCategory', on_delete=models.SET_NULL, null=True, blank=True)

    # Payment and discount details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)

    # Coupon for revenue transactions
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True)

    # New fields
    items = models.ManyToManyField('Item', blank=True)  # many items per transaction
    loyalty_points_earned = models.IntegerField(default=0)
    loyalty_points_redeemed = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    quantity = models.PositiveIntegerField(default=1)
    expense_name = models.CharField(max_length=200, blank=True, null=True)
   


    def clean(self):
    # Validate fields depending on transaction type
        if self.transaction_type == 'revenue':
            if not self.party:
                raise ValidationError("Customer (party) must be set for revenue transactions.")
            if self.expense_category is not None:
                raise ValidationError("Expense category must be empty for revenue transactions.")
            # Coupon is optional for revenue

        elif self.transaction_type == 'expense':
            if not self.party and not self.expense_category:
                raise ValidationError("Supplier (party) or Expense Category must be set for expense transactions.")
            if self.coupon is not None:
                raise ValidationError("Coupon must be empty for expense transactions.")

    def save(self, *args, **kwargs):
        self.clean()  # Call validation before saving
        if self.is_paid and self.paid_at is None:
            self.paid_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} at {self.branch}"



class ExpenseCategory(models.Model):
    business = models.ForeignKey('Business', on_delete=models.CASCADE, related_name='expense_categories')
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ('business', 'name')  # ensure unique category names per business

    def __str__(self):
        return self.name



    
class Coupon(models.Model):
    branch = models.ForeignKey('Branch', on_delete=models.CASCADE, related_name='coupons', null=True, blank=True)
    code = models.CharField(max_length=50, unique=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # fixed UGX
    discount_percent = models.FloatField(null=True, blank=True)  # % discount
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    min_spend = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # optional
    applicable_items = models.ManyToManyField('Item', blank=True)  # limit to items
    is_active = models.BooleanField(default=True)
    usage_limit = models.IntegerField(null=True, blank=True)  # optional
    

    def __str__(self):
        return self.code


class BusinessSettings(models.Model):
    business = models.OneToOneField('Business', on_delete=models.CASCADE)
    loyalty_points_per_visit = models.IntegerField(default=1)
    loyalty_points_required_for_discount = models.IntegerField(default=10)
    loyalty_discount_percent = models.FloatField(default=5.0)
    coupon_min_spend = models.DecimalField(max_digits=12, decimal_places=2, default=200000)
    coupon_discount_percent = models.FloatField(default=5.0)
    # add more fields as needed

    def __str__(self):
        return f"Settings for {self.business.name}"

    






