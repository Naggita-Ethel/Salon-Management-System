from django.urls import path
from .views import dashboard_view, forgot_password, register_business, settings_view, transactions_view
from django.contrib.auth import views as auth_views

urlpatterns = [

    path('', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('forgot-password/', forgot_password, name='forgot-password'),
    path('business/register/', register_business, name='register-business'),
    path('dashboard/', dashboard_view, name='dashboard'), 
    path('transactions/', transactions_view, name='transactions'),
    path('settings/', settings_view, name='settings'),
    
]
