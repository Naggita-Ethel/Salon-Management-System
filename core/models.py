from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.forms import ValidationError
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

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
    phone = models.CharField(max_length=15, blank=True, null=True) # Made phone optional for generic walk-in
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    company = models.CharField(max_length=150, blank=True, null=True)  # Used mainly for suppliers
    loyalty_points = models.IntegerField(default=0)  # Used mainly for customers
    created_at = models.DateTimeField(auto_now_add=True)
    business = models.ForeignKey('Business', on_delete=models.CASCADE, related_name='parties')
    

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
    serviced_by = models.ForeignKey('BranchEmployee', on_delete=models.SET_NULL, null=True, blank=True, related_name='serviced_transactions')


    loyalty_points_earned = models.IntegerField(default=0)
    loyalty_points_redeemed = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
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
    
# Associates each transaction with individual items and quantity.
class TransactionItem(models.Model):
    transaction = models.ForeignKey('Transaction', on_delete=models.CASCADE, related_name='transaction_items')
    item = models.ForeignKey('Item', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    employee = models.ForeignKey('BranchEmployee', on_delete=models.SET_NULL, null=True, blank=True, related_name='item_sales')

    def total_price(self):
        return self.quantity * self.item.selling_price



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
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount_percent = models.FloatField(null=True, blank=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    min_spend = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    applicable_items = models.ManyToManyField('Item', blank=True)
    is_active = models.BooleanField(default=True)
    usage_limit = models.IntegerField(null=True, blank=True)
    
    # New: To track how many times this coupon has been used
    times_used = models.IntegerField(default=0) 

    def __str__(self):
        return self.code

    def clean(self):
        if self.discount_amount is None and self.discount_percent is None:
            raise ValidationError("Either discount amount or discount percent must be set.")
        if self.discount_amount is not None and self.discount_percent is not None:
            raise ValidationError("Cannot set both discount amount and discount percent. Choose one.")
        if self.discount_percent is not None and (self.discount_percent < 0 or self.discount_percent > 100):
            raise ValidationError("Discount percent must be between 0 and 100.")

    def is_valid(self, transaction_total=0):
        now = timezone.now()
        if not self.is_active:
            return False, "Coupon is not active."
        if now < self.valid_from:
            return False, "Coupon is not yet valid."
        if now > self.valid_until:
            return False, "Coupon has expired."
        if self.min_spend > transaction_total:
            return False, f"Minimum spend of UGX {self.min_spend} is required."
        if self.usage_limit is not None and self.times_used >= self.usage_limit:
            return False, "Coupon has reached its usage limit."
        return True, "Coupon is valid."

    def calculate_discount(self, total_amount):
        if self.discount_amount:
            return min(self.discount_amount, total_amount) # Ensure discount doesn't exceed total
        elif self.discount_percent:
            return total_amount * (self.discount_percent / 100)
        return 0



class BusinessSettings(models.Model):
    business = models.OneToOneField(Business, on_delete=models.CASCADE, related_name='settings')
    
    # Loyalty Settings (assuming you want to track these per business)
    # Loyalty points earned per X amount spent
    loyalty_points_per_ugx_spent = models.DecimalField(
        max_digits=10, decimal_places=2, default=100.00,
        help_text="Amount in UGX a customer needs to spend to earn 1 loyalty point."
    )
    # Loyalty points required to qualify for a discount
    loyalty_points_required_for_discount = models.IntegerField(
        default=500,
        help_text="Number of loyalty points required for a customer to qualify for a discount."
    )
    # Discount percentage given when loyalty points are redeemed
    loyalty_discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=5.00,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Percentage discount applied when loyalty points are redeemed (e.g., 5 for 5%)."
    )

    # Coupon Settings (general settings for how coupons might behave)
    # Minimum spend for a coupon to be applicable
    coupon_min_spend = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Minimum transaction amount required for any coupon to be applied (0 for no minimum)."
    )
    # Default discount percentage for newly created coupons (if not specified)
    coupon_discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.00,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Default percentage discount for coupons if not overridden by specific coupon settings."
    )
    
    # You had 'loyalty_points_per_visit' in the error. If you actually want this, add it:
    # loyalty_points_per_visit = models.IntegerField(default=5, help_text="Points earned per visit, regardless of spend.")


    class Meta:
        verbose_name_plural = "Business Settings"

    def __str__(self):
        return f"Settings for {self.business.name}"

    






