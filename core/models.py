from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.forms import ValidationError
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum, Count # Import these for aggregation
from decimal import Decimal # Important for financial calculations
from django.db.models.signals import post_save
from django.dispatch import receiver

class Payment(models.Model):
    transaction = models.ForeignKey('Transaction', related_name='payments', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Payment of {self.amount} for {self.transaction}"

class User(AbstractUser):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)  # Added for employee address
    GENDER_CHOICES = (
        ('Male', 'Male'),
        ('Female', 'Female'),
    )
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES)  # Added for gender

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
        return self.name

class Item(models.Model):
    ITEM_TYPES = (
        ('service', 'Service'),
        ('product', 'Product'),
    )
    business = models.ForeignKey('Business', on_delete=models.CASCADE, related_name='items')
    type = models.CharField(max_length=20, choices=ITEM_TYPES)
    name = models.CharField(max_length=100)
    selling_price = models.DecimalField(max_digits=10, decimal_places=0, validators=[MinValueValidator(0.0)])
    cost_price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True, validators=[MinValueValidator(0.0)])

    class Meta:
        unique_together = ('business', 'name', 'type')  # Unique name per type per business

    def __str__(self):
        return self.name
    
    def available_stock(self, branch=None):
        filters = {}
        if branch:
            filters['transaction__branch'] = branch

        stock_in = self.transaction_items.filter(
            transaction__transaction_type='expense',
            **filters
        ).aggregate(total=Sum('quantity'))['total'] or 0

        stock_out = self.transaction_items.filter(
            transaction__transaction_type='revenue',
            **filters
        ).aggregate(total=Sum('quantity'))['total'] or 0

        return stock_in - stock_out

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
    
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]
    gender = models.CharField(max_length=50, choices=GENDER_CHOICES, null=True, blank=True)

    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    branch = models.ForeignKey('Branch', on_delete=models.CASCADE, null=True, blank=True) 
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True, null=True) 
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    company = models.CharField(max_length=150, blank=True, null=True) 
    loyalty_points = models.IntegerField(default=0) 
    created_at = models.DateTimeField(auto_now_add=True)
    business = models.ForeignKey('Business', on_delete=models.CASCADE, related_name='parties')
    
    def __str__(self):
        if self.type == 'supplier' and self.company:
            return f"{self.full_name} ({self.company})"
        return self.full_name

    @property
    def total_spend(self):
        """
        Calculates the total amount spent by this customer across all their completed and paid revenue transactions.
        """
        # Assuming 'Transaction' model has a ForeignKey to 'Party' named 'party'
        # And assuming 'Transaction' has 'amount', 'transaction_type', 'status', and 'is_paid' fields.
        total = self.transaction_set.filter(
            transaction_type='revenue', 
            status='completed', 
            is_paid=True # Only count fully paid transactions for 'total spend'
        ).aggregate(sum_amount=Sum('amount'))['sum_amount']
        # Return Decimal('0.00') if no transactions or sum is None
        return total if total is not None else Decimal('0.00')

    @property
    def total_visits(self):
        """
        Counts the number of distinct completed revenue transactions (visits) for this customer.
        """
        # Count distinct transactions. If each transaction represents a visit.
        visits = self.transaction_set.filter(
            transaction_type='revenue', 
            status='completed'
        ).count()
        return visits

class Transaction(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('fully_paid', 'Fully Paid'),
        ('partially_paid', 'Partially Paid'),
        ('pending', 'Not Paid / Pending'),
    ]
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        help_text="Tracks if the transaction is fully paid, partially paid, or pending."
    )

    amount_paid = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        help_text="Amount paid so far for this transaction (for partial payments)."
    )

    TRANSACTION_TYPE_CHOICES = [
        ('revenue', 'Customer Purchase'),  # money coming in
        ('expense', 'Expense'),             # money going out
    ]

    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Card', 'Card'),
        ('MobileMoney', 'Mobile Money'),
    ]

    TRANSACTION_STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('voided', 'Voided'),
        ('refunded', 'Refunded'),
        # Add other statuses as needed, e.g., 'pending', 'draft'
    ]

    # New status field for the transaction's overall state
    status = models.CharField(
        max_length=20, 
        choices=TRANSACTION_STATUS_CHOICES, 
        default='completed', # Most transactions will start as completed
        help_text="Overall status of the transaction (e.g., Completed, Voided, Refunded)."
    )
    # Fields for auditing void/refund actions (optional but good practice)
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(
        'core.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='voided_transactions',
        help_text="User who voided this transaction."
    )
    refund_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Amount refunded for this transaction (if status is 'refunded')."
    )

    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)

    branch = models.ForeignKey('Branch', on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)

    party = models.ForeignKey('Party', on_delete=models.SET_NULL, null=True, blank=True)
    expense_category = models.ForeignKey('ExpenseCategory', on_delete=models.SET_NULL, null=True, blank=True)

    # Payment and discount details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Coupon for revenue transactions
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True)
    serviced_by = models.ForeignKey('BranchEmployee', on_delete=models.SET_NULL, null=True, blank=True, related_name='serviced_transactions')


    loyalty_points_earned = models.IntegerField(default=0)
    loyalty_points_redeemed = models.IntegerField(default=0)
    business = models.ForeignKey('Business', on_delete=models.CASCADE, related_name='transactions')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    expense_name = models.CharField(max_length=200, blank=True, null=True)
   
      # Add this method for convenience
    def mark_as_voided(self, user):
        if self.status not in ['voided', 'refunded']: # Only void if not already voided/refunded
            self.status = 'voided'
            self.voided_at = timezone.now()
            self.voided_by = user
            self.save()
            return True
        return False
    
    # You might add a mark_as_refunded method too, which would be tied to the refund view logic
    def mark_as_refunded(self, user, refund_amount):
        if self.status not in ['voided', 'refunded']:
             self.status = 'refunded'
             self.refund_amount = refund_amount
             self.voided_at = timezone.now() # Re-using voided_at for consistency if you don't add refund_at
             self.voided_by = user
             self.save()
             return True
        return False

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
    item = models.ForeignKey('Item', on_delete=models.CASCADE, related_name='transaction_items')
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
    
@receiver(post_save, sender=Business)
def create_product_purchase_category(sender, instance, created, **kwargs):
    if created:
        ExpenseCategory.objects.get_or_create(
            business=instance,
            name="Product Purchases"
        )


class BusinessSettings(models.Model):
    business = models.OneToOneField(Business, on_delete=models.CASCADE, related_name='settings')

    # Loyalty Points Earning (already exists, but for context)
    loyalty_points_per_ugx_spent = models.DecimalField(
        max_digits=10, decimal_places=2, default=100.00,
        help_text="Amount in UGX a customer needs to spend to earn 1 loyalty point."
    )

    enable_loyalty_point_earning = models.BooleanField(
        default=True, # Usually enabled by default if you have a per_ugx_spent value
        help_text="Allow customers to earn loyalty points on purchases."
    )

    # --- Loyalty Point Redemption Settings ---
    enable_loyalty_point_redemption = models.BooleanField(
        default=False,
        help_text="Allow customers to redeem loyalty points for discounts."
    )
    loyalty_points_required_for_redemption = models.IntegerField(
        default=500,
        help_text="Minimum loyalty points a customer must have to redeem for a discount."
    )
    loyalty_redemption_discount_type = models.CharField(
        max_length=10,
        choices=[('percentage', 'Percentage'), ('fixed', 'Fixed Amount')],
        default='percentage',
        help_text="Type of discount when loyalty points are redeemed."
    )
    loyalty_redemption_discount_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=5.00,
        help_text="Value of discount (e.g., 5 for 5% or 5000 for UGX 5000). If Percentage, value should be 0-100."
    )
    loyalty_redemption_max_discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, blank=True, null=True,
        help_text="Maximum fixed amount discount (UGX) a loyalty redemption can provide. Leave 0 or blank for no max."
    )
    # New: Option to make loyalty redemption branch-specific
    loyalty_redemption_is_branch_specific = models.BooleanField(
        default=False,
        help_text="If checked, loyalty points can only be redeemed at the branch where they were earned."
    )


    # --- Coupon Code Settings (General eligibility for *any* coupon) ---
    enable_coupon_codes = models.BooleanField(
        default=False,
        help_text="Allow the use of coupon codes in transactions."
    )
    coupon_loyalty_requirement_type = models.CharField(
        max_length=20,
        choices=[
            ('none', 'No loyalty requirement'),
            ('min_spend', 'Minimum total spend'),
            ('min_visits', 'Minimum visits'),
            ('both', 'Minimum spend AND visits'),
            ('either', 'Minimum spend OR visits')
        ],
        default='none',
        help_text="How loyalty affects coupon eligibility. 'Both' means customer must meet both criteria. 'Either' means customer meets at least one."
    )
    loyalty_min_spend_for_coupon = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, blank=True, null=True,
        help_text="Minimum total amount a customer must have spent to be eligible for a coupon. Required if loyalty requirement is not 'none'."
    )
    loyalty_min_visits_for_coupon = models.IntegerField(
        default=0, blank=True, null=True,
        help_text="Minimum number of visits a customer must have made to be eligible for a coupon. Required if loyalty requirement is not 'none'."
    )
    # New: Option to make coupons branch-specific (this affects Coupon model too)
    coupon_is_branch_specific = models.BooleanField(
        default=False,
        help_text="If checked, coupon codes can only be used at branches explicitly assigned to the coupon."
    )


    class Meta:
        verbose_name_plural = "Business Settings"

    def __str__(self):
        return f"Settings for {self.business.name}"

# --- Coupon Model Enhancements ---
# If coupon_is_branch_specific is true, then coupons need a M2M to Branch
class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="If percentage, value is 0-100. If fixed, value is actual amount."
    )
    minimum_spend = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,
                                        help_text="Minimum transaction amount required for this coupon to apply.")
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(blank=True, null=True)
    usage_limit = models.IntegerField(blank=True, null=True,
                                      help_text="Maximum number of times this coupon can be used overall. Leave blank for unlimited.")
    times_used = models.IntegerField(default=0)
    
    # New: Link to Business
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='coupons', null=True, blank=True)
    
    # New: Branches where this coupon is valid (if coupon_is_branch_specific in BusinessSettings is true)
    valid_branches = models.ManyToManyField(Branch, blank=True, related_name='coupons',
                                             help_text="Branches where this coupon is valid. If left blank and 'Coupon is branch specific' is checked in Business Settings, this coupon will be invalid.")


    class Meta:
        ordering = ['-valid_from']

    def __str__(self):
        return self.code

    def calculate_discount(self, transaction_total):
        if self.discount_type == 'percentage':
            discount = (transaction_total * self.discount_value) / 100
            # Optional: Add a max discount for percentage coupons if needed
            # e.g., if self.max_discount_amount and discount > self.max_discount_amount:
            #          return self.max_discount_amount
            return discount
        elif self.discount_type == 'fixed':
            return min(self.discount_value, transaction_total) # Cannot discount more than total
        return 0

    def is_valid(self, transaction_total, current_branch=None, customer=None, business_settings=None):
        # Basic validity checks
        if not self.is_active:
            return False, "Coupon is not active."
        if self.valid_from and self.valid_from > timezone.now():
            return False, "Coupon is not yet valid."
        if self.valid_until and self.valid_until < timezone.now():
            return False, "Coupon has expired."
        if self.usage_limit is not None and self.times_used >= self.usage_limit:
            return False, "Coupon has reached its usage limit."
        if transaction_total < self.minimum_spend:
            return False, f"Minimum spend of UGX {self.minimum_spend} required."
        
        # Branch-specific check based on BusinessSettings
        if business_settings and business_settings.coupon_is_branch_specific:
            if not self.valid_branches.exists(): # No branches assigned to coupon
                return False, "This coupon is not assigned to any valid branches."
            if current_branch and current_branch not in self.valid_branches.all():
                return False, "This coupon is not valid at the selected branch."

        # Loyalty requirement check (now handled in the view, but keeping for reference if needed elsewhere)
        # This will be primarily in `revenue_create_view` because it needs customer's full transaction history.

        return True, "Coupon is valid."




    






