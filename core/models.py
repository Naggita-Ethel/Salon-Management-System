from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models
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
    description = models.TextField(blank=True)

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

class Customer(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    loyalty_points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name



class Payment(models.Model):
    METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Card', 'Card'),
        ('MobileMoney', 'Mobile Money'),
    ]

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    branch = models.ForeignKey('Branch', on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.is_paid and self.paid_at is None:
            self.paid_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.amount} ({self.method})"


    
class Coupon(models.Model):
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


class Expense(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='expenses')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='expenses', null=True, blank=True)
    category = models.ForeignKey('ExpenseCategory', on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.branch.name if self.branch else 'Head Office'} - UGX {self.amount} - {self.category.name if self.category else 'Uncategorized'}"

class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
    






