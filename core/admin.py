from django.contrib import admin
from django.contrib.auth import get_user_model
from core.models import Branch, BranchEmployee, Business, Customer,Item, UserRole

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



