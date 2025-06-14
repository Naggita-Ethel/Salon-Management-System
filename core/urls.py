from django.urls import path
from .views import add_service_product_view, addbranch_view, branch_view, dashboard_view, delete_branch_view, delete_service_product_view, edit_branch_view, edit_service_product_view, forgot_password, forms_view, pagelock_view, register_business, services_products_view, settings_view, tables_view, transactions_view
from django.contrib.auth import views as auth_views

urlpatterns = [

    path('', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('forgot-password/', forgot_password, name='forgot-password'),
    path('business/register/', register_business, name='register-business'),
    path('dashboard/', dashboard_view, name='dashboard'), 
    path('transactions/', transactions_view, name='transactions'),
    path('settings/', settings_view, name='settings'),
    path('tables/', tables_view, name='tables'),
    path('pagelock/', pagelock_view, name='pagelock'),
    path('branch/', branch_view, name='branch'),
    path('forms/', forms_view, name='forms'),
    path('add-branch/', addbranch_view, name='add-branch'),
    path('edit-branch/<int:branch_id>/', edit_branch_view, name='edit-branch'),
    path('branch/<int:branch_id>/delete/', delete_branch_view, name='delete-branch'),
    path('services-products/', services_products_view, name='services-products'),
    path('services-products/add/', add_service_product_view, name='add-service-product'),
    path('services-products/edit/<int:item_id>/', edit_service_product_view, name='edit-service-product'),
    path('services-products/delete/<int:item_id>/', delete_service_product_view, name='delete-service-product'),

]

