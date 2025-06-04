from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    is_super_admin = models.BooleanField(default=False)

    def __str__(self):
        return self.username

class Business(models.Model):
    name = models.CharField(max_length=100)
    registered_by = models.ForeignKey('User', on_delete=models.CASCADE, related_name='registered_businesses')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class Branch(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=100)
    location = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.business.name} - {self.name}"
    
class UserRole(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='roles')
    name = models.CharField(max_length=50)  # e.g., Manager, Receptionist
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.business.name} - {self.name}"
    
class UserBusinessRole(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='business_roles')
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    role = models.ForeignKey(UserRole, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.role.name} @ {self.business.name}"

class Customer(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='customers')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    loyalty_points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name

class Service(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
class Employee(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    role = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    performance_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    total_clients_served = models.IntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

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


class Visit(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='visits')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    visit_date = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)  # receptionist, manager etc.
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.customer.full_name} visited on {self.visit_date.strftime('%Y-%m-%d %H:%M')}"

class VisitService(models.Model):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='visit_services')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    price_at_time = models.DecimalField(max_digits=10, decimal_places=2)
    performed_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='performed_services')

    def __str__(self):
        return f"{self.visit.customer.full_name} - {self.service.name}"
    
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # fixed UGX
    discount_percent = models.FloatField(null=True, blank=True)  # % discount
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    min_spend = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # optional
    applicable_services = models.ManyToManyField('Service', blank=True)  # limit to services
    is_active = models.BooleanField(default=True)
    usage_limit = models.IntegerField(null=True, blank=True)  # optional
    

    def __str__(self):
        return self.code

class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='coupon_usages')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='services')
    

    def __str__(self):
        return f"{self.customer.full_name} used {self.coupon.code}"

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
    
class Payroll(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    period_start = models.DateField()
    period_end = models.DateField()
    total_clients = models.PositiveIntegerField()
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2)
    calculated_pay = models.DecimalField(max_digits=10, decimal_places=2)
    generated_at = models.DateTimeField(auto_now_add=True)






