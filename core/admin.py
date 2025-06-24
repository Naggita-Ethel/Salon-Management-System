from django.contrib import admin
from django.contrib.auth import get_user_model
from core.models import Branch, BranchEmployee, Business, BusinessSettings, Coupon, ExpenseCategory,Item, Party, Transaction, UserRole

# Use the custom user model
User = get_user_model()

# Dynamically show all model fields in the admin list display
def all_fields(model):
    return [field.name for field in model._meta.fields]

# Register your models here.
@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Business._meta.fields]

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = all_fields(Branch)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = all_fields(User)

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = all_fields(UserRole)

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = all_fields(Item)

@admin.register(BranchEmployee)
class BranchEmployeeAdmin(admin.ModelAdmin):
    list_display = all_fields(BranchEmployee)

@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'type', 'phone', 'email', 'company', 'loyalty_points', 'branch')
    list_filter = ('type', 'branch')
    search_fields = ('full_name', 'phone', 'email', 'company')
    raw_id_fields = ('branch',)


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'business')
    search_fields = ('name',)
    raw_id_fields = ('business',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_type', 'amount', 'payment_method', 'is_paid', 'paid_at', 'branch', 'party']
    list_filter = ['transaction_type', 'payment_method', 'is_paid']
    search_fields = ['party__name']  # Assumes Party model has a name
    raw_id_fields = ['party', 'coupon', 'created_by']

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_value', 'discount_type', 'is_active', 'valid_from', 'valid_until', 'usage_limit', 'times_used', 'business')
    list_filter = ('is_active', 'discount_type', 'business', 'valid_branches') # Add valid_branches to filter
    search_fields = ('code', 'description')
    date_hierarchy = 'valid_from'
    filter_horizontal = ('valid_branches',) # For ManyToMany field

    fieldsets = (
        (None, {
            'fields': ('business', 'code', 'description', 'discount_type', 'discount_value', 'minimum_spend', 'is_active')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_until', 'usage_limit', 'times_used')
        }),
        ('Branch Specificity', {
            'fields': ('valid_branches',),
            'description': 'Select branches where this coupon is valid. Only applies if "Coupon is branch specific" is enabled in Business Settings.'
        })
    )

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "valid_branches":
            # Filter branches by the current user's business
            if hasattr(request.user, 'business') and request.user.business:
                kwargs["queryset"] = Branch.objects.filter(business=request.user.business)
            else:
                kwargs["queryset"] = Branch.objects.none() # Or all branches if no business context
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request.user, 'business') and request.user.business:
            return qs.filter(business=request.user.business)
        return qs.none() # Or all coupons if no business context

    def save_model(self, request, obj, form, change):
        if not obj.business and hasattr(request.user, 'business') and request.user.business:
            obj.business = request.user.business
        super().save_model(request, obj, form, change)


@admin.register(BusinessSettings)
class BusinessSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'business',
        'enable_loyalty_point_redemption', # New
        'loyalty_points_required_for_redemption', # New
        'loyalty_redemption_discount_type', # New
        'loyalty_redemption_discount_value', # New
        'enable_coupon_codes', # New
        'coupon_loyalty_requirement_type', # New
    )
    list_filter = ('business', 'enable_loyalty_point_redemption', 'enable_coupon_codes')
    search_fields = ('business__name',)

    fieldsets = (
        (None, {
            'fields': ('business',)
        }),
        ('Loyalty Points Earning', {
            'fields': ('loyalty_points_per_ugx_spent',),
            'description': 'Settings for how customers earn loyalty points.'
        }),
        ('Loyalty Point Redemption', {
            'fields': (
                'enable_loyalty_point_redemption',
                'loyalty_points_required_for_redemption',
                'loyalty_redemption_discount_type',
                'loyalty_redemption_discount_value',
                'loyalty_redemption_max_discount_amount',
                'loyalty_redemption_is_branch_specific',
            ),
            'description': 'Settings for how customers can redeem their earned loyalty points for discounts.'
        }),
        ('Coupon Code Eligibility', {
            'fields': (
                'enable_coupon_codes',
                'coupon_loyalty_requirement_type',
                'loyalty_min_spend_for_coupon',
                'loyalty_min_visits_for_coupon',
                'coupon_is_branch_specific',
            ),
            'description': 'General rules for allowing coupon codes based on customer loyalty. Specific coupon values are set on individual coupons.'
        }),
    )

