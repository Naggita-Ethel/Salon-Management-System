from django.urls import path
from .views import add_employee_view, add_service_product_view, addbranch_view, branch_view, customer_add_view, customer_delete_view, customer_discount_settings_view, customer_edit_view, customer_list_view, dashboard_view, delete_branch_view, delete_employee_view, delete_service_product_view, edit_branch_view, edit_employee_view, edit_service_product_view, employees_view, expense_list_view, forgot_password, forms_view, get_customer_details, get_customer_loyalty_data, get_employees_by_branch, get_items_by_category,  pagelock_view, receipt_view, register_business, revenue_create_view, revenue_list_view, services_products_view, settings_view, toggle_payment_status, transaction_void_view, update_transaction_status
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('customers/', customer_list_view, name='customer_list'),
    path('customers/add/', customer_add_view, name='customer_add'),
    path('customers/edit/<int:pk>/', customer_edit_view, name='customer_edit'),
    path('customers/delete/<int:pk>/', customer_delete_view, name='customer_delete'),
    path('settings/customer-discounts/', customer_discount_settings_view, name='customer_discount_settings'),
    path('get-customer-details/<int:customer_id>/', get_customer_details, name='get_customer_details'),
    path('transactions/<int:pk>/update_status/', update_transaction_status, name='update_transaction_status'),
    path('transactions/<int:pk>/toggle_payment/', toggle_payment_status, name='toggle_payment_status'),
    path('get-employees-by-branch/', get_employees_by_branch, name='get_employees_by_branch'),
    path('transactions/<int:pk>/void/', transaction_void_view, name='transaction_void'), 
    path('get-customer-loyalty-data/', get_customer_loyalty_data, name='get_customer_loyalty_data'), 
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

