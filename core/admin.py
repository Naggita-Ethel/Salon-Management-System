from django.contrib import admin

from core.models import Customer

# Register your models here.
@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone', 'email', 'business']
    search_fields = ['full_name', 'phone', 'email']
