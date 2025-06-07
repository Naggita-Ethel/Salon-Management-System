from django.contrib import admin

from core.models import Business, Customer

# Register your models here.
@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Business._meta.fields]

