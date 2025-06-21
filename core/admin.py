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


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'discount_amount', 'discount_percent',
        'valid_from', 'valid_until', 'is_active', 'usage_limit', 'branch'
    ]
    list_filter = ['is_active', 'valid_from', 'valid_until', 'branch']
    search_fields = ['code']
    raw_id_fields = ['branch']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_type', 'amount', 'payment_method', 'is_paid', 'paid_at', 'branch', 'party']
    list_filter = ['transaction_type', 'payment_method', 'is_paid']
    search_fields = ['party__name']  # Assumes Party model has a name
    raw_id_fields = ['party', 'coupon', 'created_by']



@admin.register(BusinessSettings)
class BusinessSettingsAdmin(admin.ModelAdmin):
    # Ensure these match the fields in your BusinessSettings model
    list_display = (
        'business',
        'loyalty_points_per_ugx_spent', # This field name must exist in the model
        'loyalty_points_required_for_discount', # This field name must exist in the model
        'loyalty_discount_percent', # This field name must exist in the model
        'coupon_min_spend', # This field name must exist in the model
        'coupon_discount_percent', # This field name must exist in the model
    )
    list_filter = ('business',)
    search_fields = ('business__name',) # Search by business name

