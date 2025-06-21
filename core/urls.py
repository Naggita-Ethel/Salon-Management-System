from django.urls import path
from .views import add_employee_view, add_service_product_view, addbranch_view, branch_view, dashboard_view, delete_branch_view, delete_employee_view, delete_service_product_view, edit_branch_view, edit_employee_view, edit_service_product_view, employees_view, expense_list_view, forgot_password, forms_view, get_employees_by_branch, get_items_by_category,  pagelock_view, receipt_view, register_business, revenue_create_view, revenue_list_view, services_products_view, settings_view
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('get-employees-by-branch/', get_employees_by_branch, name='get_employees_by_branch'),
    path('revenue/', revenue_list_view, name='revenue_list'),
    path('get-items-by-category/', get_items_by_category, name='get_items_by_category'),
    path('revenue/add/', revenue_create_view, name='revenue_create'),
    path('', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('forgot-password/', forgot_password, name='forgot-password'),
    path('business/register/', register_business, name='register-business'),
    path('dashboard/', dashboard_view, name='dashboard'), 
    path('expenses/', expense_list_view, name='expenses'),
    path('settings/', settings_view, name='settings'),
    path('pagelock/', pagelock_view, name='pagelock'),
    path('branch/', branch_view, name='branch'),
    path('add-branch/', addbranch_view, name='add-branch'),
    path('edit-branch/<int:branch_id>/', edit_branch_view, name='edit-branch'),
    path('branch/<int:branch_id>/delete/', delete_branch_view, name='delete-branch'),
    path('services-products/', services_products_view, name='services-products'),
    path('services-products/add/', add_service_product_view, name='add-service-product'),
    path('services-products/edit/<int:item_id>/', edit_service_product_view, name='edit-service-product'),
    path('services-products/delete/<int:item_id>/', delete_service_product_view, name='delete-service-product'),
    path('employees/<int:employee_id>/edit/', edit_employee_view, name='edit-employee'),
    path('employees/', employees_view, name='employees'),
    path('employees/add/', add_employee_view, name='add-employee'),
    path('employees/delete/<int:employee_id>/', delete_employee_view, name='delete-employee'),
    path('receipt/<int:transaction_id>/', receipt_view, name='receipt_detail'),

]

