from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from .models import Branch, Business, Customer, Service, User
from .forms import CustomerForm
from django.contrib.auth.decorators import login_required

@login_required(login_url='login')
def home_view(request):
    context = {
        'total_businesses': Business.objects.count(),
        'total_branches': Branch.objects.count(),
        'total_users': User.objects.count(),
        'total_services': Service.objects.count(),
    }
    return render(request, 'home.html', context)

class CustomerListView(ListView):
    model = Customer
    template_name = 'customers/customer_list.html'
    context_object_name = 'customers'

class CustomerCreateView(CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customer-list')

class CustomerUpdateView(UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customer-list')

class CustomerDetailView(DetailView):
    model = Customer
    template_name = 'customers/customer_detail.html'
    context_object_name = 'customer'
