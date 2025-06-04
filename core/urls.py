from django.urls import path
from .views import CustomerListView, CustomerCreateView, CustomerUpdateView, CustomerDetailView

urlpatterns = [
    path('customers/', CustomerListView.as_view(), name='customer-list'),
    path('customers/add/', CustomerCreateView.as_view(), name='customer-add'),
    path('customers/<int:pk>/edit/', CustomerUpdateView.as_view(), name='customer-edit'),
    path('customers/<int:pk>/', CustomerDetailView.as_view(), name='customer-detail'),
]
