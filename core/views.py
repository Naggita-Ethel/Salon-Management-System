from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from .models import Branch, BranchEmployee, Business, Customer, Item, User, UserRole
from .forms import AddEmployeeForm, BusinessRegisterForm, EditEmployeeForm, LoginForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.views.decorators.http import require_POST
from django.contrib.auth import logout
from django.contrib.auth import authenticate, login
import logging

from core import forms


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
    if not business:
        return render(request, 'home/item.html', {'services': [], 'products': []})
    
    items = Item.objects.filter(business=business).order_by('name')
    services = items.filter(type='service')
    products = items.filter(type='product')
    
    return render(request, 'home/item.html', {
        'services': services,
        'products': products
    })



logger = logging.getLogger(__name__)

@login_required
def add_service_product_view(request):
    business = getattr(request.user, 'business', None)
    if not business:
        logger.warning("User %s has no business, redirecting.", request.user)
        return redirect('services-products')

    form_errors = []
    if request.method == 'POST':
        logger.debug("POST data: %s", request.POST)
        item_type = request.POST.get('item_type')
        name = request.POST.get('name', '').strip()
        selling_price = request.POST.get('selling_price')
        cost_price = request.POST.get('cost_price')

        # Validation
        if not item_type:
            form_errors.append("Item Type is required.")
        if not name:
            form_errors.append("Name is required.")
        if not selling_price:
            form_errors.append("Selling Price is required.")
        if item_type == 'product' and not cost_price:
            form_errors.append("Cost Price is required for products.")

        if not form_errors:
            if item_type not in ['service', 'product']:
                form_errors.append("Invalid item type selected.")
            else:
                try:
                    selling_price = Decimal(selling_price)
                    cost_price = Decimal(cost_price) if cost_price else None
                    if selling_price < 0 or (cost_price is not None and cost_price < 0):
                        form_errors.append("Prices cannot be negative.")
                except InvalidOperation:
                    form_errors.append("Invalid price format. Please enter valid numbers.")
                    selling_price = None
                    cost_price = None

                # Check for duplicate item
                if not form_errors and Item.objects.filter(business=business, name=name, type=item_type).exists():
                    form_errors.append(f"A {item_type} named '{name}' already exists for this business.")

                if not form_errors:
                    try:
                        Item.objects.create(
                            business=business,
                            type=item_type,
                            name=name,
                            selling_price=selling_price,
                            cost_price=cost_price if item_type == 'product' else None
                        )
                        logger.info("Created item: %s (%s) for business %s", name, item_type, business)
                        return redirect('services-products')
                    except Exception as e:
                        form_errors.append(f"Error creating item: {str(e)}")
                        logger.error("Error creating item: %s", str(e))

    return render(request, 'home/add_item.html', {
        'form_errors': form_errors
    })


@login_required
def edit_service_product_view(request, item_id):
    business = getattr(request.user, 'business', None)
    if not business:
        return redirect('services-products')  # Redirect if no business is associated

    item = get_object_or_404(Item, id=item_id, business=business)

    form_errors = []
    if request.method == 'POST':
        name = request.POST.get('name')
        selling_price = request.POST.get('selling-price')
        cost_price = request.POST.get('cost-price')
        item_type = request.POST.get('item-type')

        if not name or not selling_price or (item_type == 'product' and not cost_price):
            form_errors.append("All required fields must be filled. Cost price is required for products.")
        elif Decimal(selling_price) < 0 or (cost_price and Decimal(cost_price) < 0):
            form_errors.append("Prices cannot be negative.")
        elif item_type not in ['service', 'product']:
            form_errors.append("Invalid item type selected.")
        else:
            try:
                item.name = name
                item.selling_price = selling_price
                item.cost_price = cost_price if item_type == 'product' else None
                item.type = item_type
                item.business = business
                item.save()
                return redirect('services-products')
            except Exception as e:
                form_errors.append(str(e))

    return render(request, 'home/edit_item.html', {
        'item': item,
        'item_type': item.type,
        'form_errors': form_errors,
        'business': business
    })

@login_required
def delete_service_product_view(request, item_id):
    business = getattr(request.user, 'business', None)
    if not business:
        return redirect('services-products')  # Redirect if no business is associated

    item = get_object_or_404(Item, id=item_id, business=business)

    if request.method == 'POST':
        item.delete()
        return redirect('services-products')

    return redirect('services-products')

def get_user_business(user):
    if hasattr(user, 'business'):
        return user.business
    elif hasattr(user, 'branchemployee'):
        return user.branchemployee.branch.business
    return None

@login_required
def employees_view(request):
    business = get_user_business(request.user)
    branches = Branch.objects.filter(business=business).prefetch_related('employees__user', 'employees__role') if business else []
    return render(request, 'home/employees.html', {'branches': branches})



@login_required
def add_employee_view(request):
    business = get_user_business(request.user)
    branches = Branch.objects.filter(business=business) if business else []

    if not branches:
        return redirect('employees')

    form = AddEmployeeForm(request.POST or None, business=business)

    if request.method == 'POST' and form.is_valid():
        try:
            email = form.cleaned_data['email']
            full_name = form.cleaned_data['full_name']
            phone = form.cleaned_data['phone']
            address = form.cleaned_data['address']
            gender = form.cleaned_data['gender']
            branch = form.cleaned_data['branch']
            role_name = form.cleaned_data['role']
            custom_role_name = form.cleaned_data['custom_role']
            status = form.cleaned_data['status']
            start_date = form.cleaned_data['start_date']

            if role_name == 'other' and custom_role_name:
                role, _ = UserRole.objects.get_or_create(
                    name=custom_role_name,
                    business=business
                )
            else:
                role, _ = UserRole.objects.get_or_create(
                    name=role_name,
                    business=business
                )

            user = User.objects.filter(email=email).first()
            if not user:
                generated_username = email.split('@')[0]
                user = User.objects.create_user(
                    username=generated_username,
                    email=email,
                    full_name=full_name,
                    phone=phone,
                    address=address,
                    gender=gender,
                    password='default123'  # Consider a better password strategy
                )
            else:
                user.full_name = full_name
                user.phone = phone
                user.address = address
                user.gender = gender
                user.save()

            BranchEmployee.objects.create(
                user=user,
                branch=branch,
                role=role,
                status=status,
                start_date=start_date
            )
            return redirect('employees')

        except Exception as e:
            form.add_error(None, str(e))

    return render(request, 'home/add_employee.html', {
        'branches': branches,
        'form': form
    })



@login_required
def edit_employee_view(request, employee_id):
    business = get_user_business(request.user)
    employee = get_object_or_404(BranchEmployee, id=employee_id, branch__business=business)

    form = EditEmployeeForm(request.POST or None, business=business, employee=employee)

    if request.method == 'POST' and form.is_valid():
        try:
            employee.user.username = form.cleaned_data['username']
            employee.user.email = form.cleaned_data['email']
            employee.user.full_name = form.cleaned_data['full_name']
            employee.user.phone = form.cleaned_data['phone']
            employee.user.address = form.cleaned_data['address']
            employee.user.gender = form.cleaned_data['gender']
            employee.user.save()
            employee.branch = form.cleaned_data['branch']
            employee.role = form.cleaned_data['role']
            employee.status = form.cleaned_data['status']
            employee.start_date = form.cleaned_data['start_date']
            employee.end_date = form.cleaned_data['end_date']
            employee.save()
            return redirect('employees')
        except Exception as e:
            form.add_error(None, str(e))

    return render(request, 'home/edit_employee.html', {
        'employee': employee,
        'form': form
    })

@login_required
def delete_employee_view(request, employee_id):
    business = get_user_business(request.user)
    employee = get_object_or_404(BranchEmployee, id=employee_id, branch__business=business)

    if request.method == 'POST':
        employee.delete()
        return redirect('employees')

    return redirect('employees')
