from django.urls import path
from .views import CustomerListView, CustomerCreateView, CustomerUpdateView, CustomerDetailView, home_view
from django.contrib.auth import views as auth_views

urlpatterns = [

    path('', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('home/', home_view, name='home'), 
    path('customers/', CustomerListView.as_view(), name='customer-list'),
    path('customers/add/', CustomerCreateView.as_view(), name='customer-add'),
    path('customers/<int:pk>/edit/', CustomerUpdateView.as_view(), name='customer-edit'),
    path('customers/<int:pk>/', CustomerDetailView.as_view(), name='customer-detail'),
]
