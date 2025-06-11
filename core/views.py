from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from .models import Branch, BranchEmployee, Business, Customer, Item, User, UserRole
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

@login_required
def branch_view(request):
    business = getattr(request.user, 'business', None)
    branches = Branch.objects.filter(business=business) if business else []
    return render(request, 'home/branch.html', {'branches': branches})

def forms_view(request):
    return render(request, 'home/components-forms.html')

def addbranch_view(request):
    if request.method == "POST":
        branch_name = request.POST.get("branch-name")
        location = request.POST.get("location")

        business = request.user.business

        branch = Branch.objects.create(name=branch_name, location=location, business=business)


        return redirect("branch")  # redirect to a success page

    return render(request, "home/add_branch.html")

def edit_branch_view(request, branch_id):
    branch = get_object_or_404(Branch, id=branch_id)

    if request.method == "POST":
        # Update branch info
        branch.name = request.POST.get("branch-name")
        branch.location = request.POST.get("location")
        branch.save()

        return redirect("branch")  # redirect to branch listing or detail


    return render(request, "home/edit_branch.html", {
        "branch": branch,
        
    })

def delete_branch_view(request, branch_id):
    branch = get_object_or_404(Branch, id=branch_id)

    if request.method == "POST":
        branch.delete()  
        return redirect("branch")  

    return redirect("branch")

@login_required
def services_products_view(request):
    business = getattr(request.user, 'business', None)
    branches = Branch.objects.filter(business=business) if business else []
    return render(request, 'home/item.html', {'branches': branches})

@login_required
def add_service_product_view(request):
    business = getattr(request.user, 'business', None)
    branches = Branch.objects.filter(business=business) if business else []

    if not branches:
        return redirect('services-products')  # Redirects to list page with no-branch message

    form_errors = []
    if request.method == 'POST':
        branch_id = request.POST.get('branch')
        item_type = request.POST.get('item-type')
        name = request.POST.get('name')
        selling_price = request.POST.get('selling-price')
        cost_price = request.POST.get('cost-price')

        if not name or not selling_price or (item_type == 'product' and not cost_price):
            form_errors.append("All required fields must be filled. Cost price is required for products.")
        elif Decimal(selling_price) < 0 or (cost_price and Decimal(cost_price) < 0):
            form_errors.append("Prices cannot be negative.")
        else:
            branch = get_object_or_404(Branch, id=branch_id, business=business)
            try:
                Item.objects.create(
                    branch=branch,
                    type=item_type,
                    name=name,
                    selling_price=selling_price,
                    cost_price=cost_price if item_type == 'product' else None
                )
                return redirect('services-products')
            except Exception as e:
                form_errors.append(str(e))

    return render(request, 'home/add_item.html', {
        'branches': branches,
        'form_errors': form_errors
    })

@login_required
def edit_service_product_view(request, item_id):
    business = getattr(request.user, 'business', None)
    branches = Branch.objects.filter(business=business) if business else []
    item = get_object_or_404(Item, id=item_id, branch__business=business)

    form_errors = []
    if request.method == 'POST':
        name = request.POST.get('name')
        selling_price = request.POST.get('selling-price')
        cost_price = request.POST.get('cost-price')
        branch_id = request.POST.get('branch')
        branch = get_object_or_404(Branch, id=branch_id, business=business)

        if not name or not selling_price or (item.type == 'product' and not cost_price):
            form_errors.append("All required fields must be filled. Cost price is required for products.")
        elif Decimal(selling_price) < 0 or (cost_price and Decimal(cost_price) < 0):
            form_errors.append("Prices cannot be negative.")
        else:
            try:
                item.name = name
                item.selling_price = selling_price
                item.cost_price = cost_price if item.type == 'product' else None
                item.branch = branch
                item.save()
                return redirect('services-products')
            except Exception as e:
                form_errors.append(str(e))

    return render(request, 'home/edit_item.html', {
        'branches': branches,
        'item': item,
        'item_type': item.type,
        'form_errors': form_errors
    })

@login_required
def delete_service_product_view(request, item_id):
    business = getattr(request.user, 'business', None)
    item = get_object_or_404(Item, id=item_id, branch__business=business)

    if request.method == 'POST':
        item.delete()
        return redirect('services-products')

    return redirect('services-products')

@login_required
def employees_view(request):
    business = getattr(request.user, 'business', None)
    branches = Branch.objects.filter(business=business).prefetch_related('employees__user', 'employees__role') if business else []
    return render(request, 'home/employees.html', {'branches': branches})

@login_required
def add_employee_view(request):
    business = getattr(request.user, 'business', None)
    branches = Branch.objects.filter(business=business) if business else []
    roles = UserRole.objects.filter(business=business) if business else []

    if not branches:
        return redirect('employees')

    form_errors = []
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        gender = request.POST.get('gender')
        branch_id = request.POST.get('branch')
        role_id = request.POST.get('role')
        status = request.POST.get('status')
        start_date = request.POST.get('start_date') or None

        if not all([username, email, full_name, branch_id, role_id, status, gender]):
            form_errors.append("All required fields must be filled.")
        else:
            try:
                branch = get_object_or_404(Branch, id=branch_id, business=business)
                role = get_object_or_404(UserRole, id=role_id, business=business)
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': email,
                        'full_name': full_name,
                        'phone': phone,
                        'address': address,
                        'gender': gender
                    }
                )
                if not created and (user.email != email or user.full_name != full_name):
                    form_errors.append("Username exists with different email or full name.")
                else:
                    BranchEmployee.objects.create(
                        user=user,
                        branch=branch,
                        role=role,
                        status=status,
                        start_date=start_date
                    )
                    return redirect('employees')
            except Exception as e:
                form_errors.append(str(e))

    return render(request, 'home/add_employee.html', {
        'branches': branches,
        'roles': roles,
        'form_errors': form_errors
    })

@login_required
def edit_employee_view(request, employee_id):
    business = getattr(request.user, 'business', None)
    branches = Branch.objects.filter(business=business) if business else []
    roles = UserRole.objects.filter(business=business) if business else []
    employee = get_object_or_404(BranchEmployee, id=employee_id, branch__business=business)

    form_errors = []
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        gender = request.POST.get('gender')
        branch_id = request.POST.get('branch')
        role_id = request.POST.get('role')
        status = request.POST.get('status')
        start_date = request.POST.get('start_date') or None
        end_date = request.POST.get('end_date') or None

        if not all([full_name, branch_id, role_id, status, gender]):
            form_errors.append("All required fields must be filled.")
        else:
            try:
                branch = get_object_or_404(Branch, id=branch_id, business=business)
                role = get_object_or_404(UserRole, id=role_id, business=business)
                employee.user.full_name = full_name
                employee.user.phone = phone
                employee.user.address = address
                employee.user.gender = gender
                employee.user.save()
                employee.branch = branch
                employee.role = role
                employee.status = status
                employee.start_date = start_date
                employee.end_date = end_date
                employee.save()
                return redirect('employees')
            except Exception as e:
                form_errors.append(str(e))

    return render(request, 'home/edit_employee.html', {
        'branches': branches,
        'roles': roles,
        'employee': employee,
        'form_errors': form_errors
    })

@login_required
def delete_employee_view(request, employee_id):
    business = getattr(request.user, 'business', None)
    employee = get_object_or_404(BranchEmployee, id=employee_id, branch__business=business)

    if request.method == 'POST':
        employee.delete()
        return redirect('employees')

    return redirect('employees')