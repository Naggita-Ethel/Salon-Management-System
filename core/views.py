from django.shortcuts import redirect, render
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from .models import Branch, Business, Customer, Service, User
from .forms import BusinessForm, CustomerForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import login_required, user_passes_test

@login_required(login_url='login')
def home_view(request):
    context = {
        'total_businesses': Business.objects.count(),
        'total_branches': Branch.objects.count(),
        'total_users': User.objects.count(),
        'total_services': Service.objects.count(),
    }
    return render(request, 'home.html', context)

def is_super_admin(user):
    return user.is_authenticated and user.is_super_admin

@login_required(login_url='login')
# @user_passes_test(is_super_admin, login_url='login')
def register_business_view(request):
    if request.method == 'POST':
        form = BusinessForm(request.POST)
        if form.is_valid():
            business = form.save(commit=False)
            business.registered_by = request.user
            business.save()
            return redirect('home')
    else:
        form = BusinessForm()
    return render(request, 'business/register_business.html', {'form': form})

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
