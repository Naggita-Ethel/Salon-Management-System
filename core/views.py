from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from .models import Branch, Business, Customer, Service, User
from .forms import BusinessRegisterForm, LoginForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.views.decorators.http import require_POST
from django.contrib.auth import logout
from django.contrib.auth import authenticate, login


def login_view(request):
    form = LoginForm(request.POST or None)

    msg = None

    if request.method == "POST":

        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect("dashboard")
            else:
                msg = 'Invalid credentials'
        else:
            msg = 'Error validating the form'

    return render(request, "accounts/login.html", {"form": form, "msg": msg})


@login_required(login_url='login')
def dashboard_view(request):
    return render(request, 'home/dashboard.html')

def forgot_password(request):
    return render(request, 'home/page-forgot-password.html')

def register_business(request):
    if request.method == 'POST':
        form = BusinessRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')  # Redirect to login after registration
    else:
        form = BusinessRegisterForm()

    return render(request, 'accounts/register.html', {'form': form})

@login_required(login_url='login')
def transactions_view(request):
    return render(request, 'home/transactions.html')

@login_required(login_url='login')
def settings_view(request):
    return render(request, 'home/settings.html')

def tables_view(request):
    return render(request, 'home/tables-bootstrap-tables.html')

def pagelock_view(request):
    return render(request, 'home/page-lock.html')

def branch_view(request):
    branches = Branch.objects.prefetch_related('services').all()
    return render(request, "home/branch.html", {"branches": branches})

def forms_view(request):
    return render(request, 'home/components-forms.html')

def addbranch_view(request):
    if request.method == "POST":
        branch_name = request.POST.get("branch-name")
        location = request.POST.get("location")
        services = request.POST.getlist("services[]")
        custom_services = request.POST.getlist("custom_services[]")
        prices = request.POST.getlist("prices[]")

        business = request.user.business

        branch = Branch.objects.create(name=branch_name, location=location, business=business)

        for i, service in enumerate(services):
            if service == "custom":
                service_name = custom_services[i]
            else:
                service_name = service

            price = prices[i]
            Service.objects.create(branch=branch, name=service_name, price=price)

        return redirect("branch")  # redirect to a success page

    return render(request, "home/add_branch.html")

def edit_branch_view(request, branch_id):
    branch = get_object_or_404(Branch, id=branch_id)
    services = Service.objects.filter(branch=branch)

    if request.method == "POST":
        # Update branch info
        branch.name = request.POST.get("branch-name")
        branch.location = request.POST.get("location")
        branch.save()

        # Get posted form values
        service_names = request.POST.getlist("services[]")
        custom_services = request.POST.getlist("custom_services[]")
        prices = request.POST.getlist("prices[]")

        # Clear old services for a fresh update
        Service.objects.filter(branch=branch).delete()

        for i in range(len(prices)):
            if not prices[i]:  # Skip empty/deleted rows (failsafe)
                continue

            name = service_names[i]
            if name == "custom":
                name = custom_services[i]  # use custom service name

            # Only create service if name is not empty
            if name.strip():
                Service.objects.create(branch=branch, name=name.strip(), price=prices[i])

        return redirect("branch")  # redirect to branch listing or detail

    predefined_services = [
        "Hair Cuts", "Hair Plaiting", "Massage",
        "Manicure and Pedicure", "Hair washing", "Hair styling", "Hair treatment"
    ]

    return render(request, "home/edit_branch.html", {
        "branch": branch,
        "services": services,
        "predefined_services": predefined_services
    })

def delete_branch_view(request, branch_id):
    branch = get_object_or_404(Branch, id=branch_id)

    if request.method == "POST":
        branch.delete()  
        return redirect("branch")  

    return redirect("branch")
