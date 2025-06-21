from datetime import timezone
from decimal import Decimal, InvalidOperation
from pyexpat.errors import messages
import uuid
from django.forms import inlineformset_factory
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from .models import Branch, BranchEmployee, BusinessSettings, Item, Party, Transaction, TransactionItem, User, UserRole
from .forms import AddEmployeeForm, BusinessRegisterForm, EditEmployeeForm, LoginForm, TransactionForm, TransactionItemForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.views.decorators.http import require_POST
from django.contrib.auth import logout
from django.contrib.auth import authenticate, login
import logging
from django.db import transaction as db_transaction
from django.core.paginator import Paginator
from xhtml2pdf import pisa # If you choose xhtml2pdf

from core import forms

# In your views.py

from django.http import HttpResponse
from django.template.loader import get_template
import io
from xhtml2pdf import pisa # If you choose xhtml2pdf

@login_required
def receipt_view(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id, branch__business=request.user.business)
    
    context = {
        'transaction': transaction,
        'business': request.user.business,
        'branch': transaction.branch,
        # Add any other data needed for the receipt
    }
    
    # Render for preview
    if 'preview' in request.GET:
        return render(request, 'home/receipt_template.html', context)
    
    # Generate PDF for download
    template = get_template('home/receipt_template.html')
    html = template.render(context)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="receipt_{transaction.id}.pdf"'
        return response
    
    return HttpResponse('Error generating PDF', status=500)



TransactionItemFormSet = inlineformset_factory(Transaction, TransactionItem, form=TransactionItemForm, extra=1, can_delete=True)


@login_required
def get_items_by_category(request):
    category = request.GET.get('category')
    # Filter by business of the current user
    items = Item.objects.filter(business=request.user.business, type=category).values('id', 'name', 'selling_price')
    return JsonResponse(list(items), safe=False)

@login_required
def get_employees_by_branch(request):
    branch_id = request.GET.get('branch_id')
    employees = BranchEmployee.objects.filter(
        branch_id=branch_id,
        branch__business=request.user.business,
        status='active'
    ).select_related('user').values('id', 'user__full_name', 'user__username')
    
    # Format for display: use full_name if available, else username
    formatted_employees = [{'id': emp['id'], 'name': emp['user__full_name'] or emp['user__username']} for emp in employees]
    return JsonResponse(formatted_employees, safe=False)


@login_required
def revenue_create_view(request):
    business_settings = BusinessSettings.objects.get_or_create(business=request.user.business)[0]

    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        # No need to pass branch_id here anymore via form_kwargs
        formset = TransactionItemFormSet(request.POST, prefix='items')

        if form.is_valid() and formset.is_valid():
            with db_transaction.atomic():
                customer = None
                customer_selection_type = form.cleaned_data.get('customer_selection_type')
                branch = form.cleaned_data.get('branch') # Get the selected branch object

                if customer_selection_type == 'new':
                    full_name = form.cleaned_data.get('new_customer_name')
                    phone = form.cleaned_data.get('new_customer_phone')
                    email = form.cleaned_data.get('new_customer_email')
                    address = form.cleaned_data.get('new_customer_address')
                    gender = form.cleaned_data.get('new_customer_gender')

                    if phone:
                        existing_party = Party.objects.filter(business=request.user.business, type='customer', phone=phone).first()
                        if existing_party:
                            customer = existing_party
                            messages.info(request, f"Customer with phone {phone} already exists. Using existing record.")
                            customer.full_name = full_name # Update name
                            customer.email = email # Update email
                            customer.address = address # Update address
                            customer.gender = gender # Update gender
                            customer.save()
                        else:
                            customer = Party.objects.create(
                                type='customer',
                                full_name=full_name,
                                phone=phone,
                                email=email,
                                address=address,
                                gender=gender,
                                branch=branch,
                                business=request.user.business,
                            )
                    else:
                        customer = Party.objects.create(
                                type='customer',
                                full_name=full_name + " (Anonymous Walk-in)",
                                branch=branch,
                                business=request.user.business,
                            )
                        messages.warning(request, "No phone number provided for new customer. Loyalty points cannot be tracked for this individual.")
                else:
                    customer = form.cleaned_data.get('existing_customer')
                    if not customer:
                        messages.error(request, 'Please select an existing customer.')
                        # Re-render with errors
                        all_items_data = Item.objects.filter(business=request.user.business).values('id', 'selling_price')
                        item_prices_json = {str(item['id']): float(item['selling_price']) for item in all_items_data}
                        context = {
                            'form': form,
                            'formset': formset,
                            'business_settings': business_settings,
                            'item_prices_json': item_prices_json
                        }
                        return render(request, 'home/add_revenue.html', context)


                transaction = form.save(commit=False)
                transaction.transaction_type = 'revenue'
                transaction.party = customer
                transaction.created_by = request.user
                
                total_amount = 0
                transaction_items_to_save = []
                for item_form in formset:
                    if item_form.cleaned_data.get('DELETE', False):
                        if item_form.instance.pk: # Only delete if it's an existing item
                            item_form.instance.delete()
                        continue
                    
                    if item_form.is_valid():
                        item = item_form.cleaned_data['item']
                        quantity = item_form.cleaned_data['quantity']
                        total_amount += item.selling_price * quantity
                        transaction_item = item_form.save(commit=False)
                        transaction_items_to_save.append(transaction_item)
                    elif item_form.errors:
                        print("Individual Item Form Errors:", item_form.errors)
                        messages.error(request, "Error in one or more item entries.")
                        all_items_data = Item.objects.filter(business=request.user.business).values('id', 'selling_price')
                        item_prices_json = {str(item['id']): float(item['selling_price']) for item in all_items_data}
                        context = {
                            'form': form,
                            'formset': formset,
                            'business_settings': business_settings,
                            'item_prices_json': item_prices_json
                        }
                        return render(request, 'home/add_revenue.html', context)

                if not transaction_items_to_save and not formset.deleted_forms:
                    messages.error(request, 'No items were added to the purchase.')
                    all_items_data = Item.objects.filter(business=request.user.business).values('id', 'selling_price')
                    item_prices_json = {str(item['id']): float(item['selling_price']) for item in all_items_data}
                    context = {
                        'form': form,
                        'formset': formset,
                        'business_settings': business_settings,
                        'item_prices_json': item_prices_json
                    }
                    return render(request, 'home/add_revenue.html', context)

                coupon = form.cleaned_data.get('coupon')
                if coupon:
                    is_valid, msg = coupon.is_valid(transaction_total=total_amount)
                    if is_valid:
                        transaction.discount_amount = coupon.calculate_discount(total_amount)
                        total_amount -= transaction.discount_amount
                        coupon.times_used += 1
                        coupon.save()
                    else:
                        messages.warning(request, f"Coupon '{coupon.code}' could not be applied: {msg}")
                        transaction.coupon = None

                transaction.amount = total_amount

                if transaction.party and transaction.party.phone:
                    points_earned = int(total_amount / float(business_settings.loyalty_points_per_ugx_spent))
                    transaction.loyalty_points_earned = points_earned
                    transaction.party.loyalty_points += points_earned
                    transaction.party.save()
                else:
                    transaction.loyalty_points_earned = 0
                    messages.info(request, "No loyalty points earned for this transaction as customer details are incomplete.")

                transaction.save()

                for tx_item in transaction_items_to_save:
                    tx_item.transaction = transaction
                    tx_item.save()

                messages.success(request, 'Customer purchase recorded successfully.')
                return redirect('receipt_detail', transaction_id=transaction.id)

        else:
            messages.error(request, 'There was an error saving the form. Please check and try again.')
            print("Main Form Errors:", form.errors)
            print("Formset Errors:", formset.errors)
    else: # GET request
        form = TransactionForm(user=request.user)
        # No form_kwargs for branch_id here anymore
        formset = TransactionItemFormSet(prefix='items')
    
    all_items_data = Item.objects.filter(business=request.user.business).values('id', 'selling_price')
    item_prices_json = {str(item['id']): float(item['selling_price']) for item in all_items_data}

    context = {
        'form': form,
        'formset': formset,
        'business_settings': business_settings,
        'item_prices_json': item_prices_json,
    }
    return render(request, 'home/add_revenue.html', context)

@login_required
def revenue_list_view(request):
    business = request.user.business
    branches = Branch.objects.filter(business=business).order_by('name')  # or any ordering

    if not branches.exists():
        return render(request, 'home/revenue.html', {
            'branches': [],
            'selected_branch': None,
            'transactions': None,
        })

    # Get selected branch from URL or use first available
    selected_branch_id = request.GET.get('branch')
    if selected_branch_id:
        selected_branch = get_object_or_404(Branch, id=selected_branch_id, business=business)
    else:
        selected_branch = branches.first()

    transactions_qs = (
        Transaction.objects
        .filter(branch=selected_branch, transaction_type='revenue')
        .prefetch_related('transaction_items__item', 'party')
        .order_by('-created_at')
    )

    paginator = Paginator(transactions_qs, 20)
    page_number = request.GET.get('page')
    transactions = paginator.get_page(page_number)

    context = {
        'branches': branches,
        'selected_branch': selected_branch,
        'transactions': transactions,
    }
    return render(request, 'home/revenue.html', context)

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

@login_required
def expense_list_view(request):
    branches = Branch.objects.all()
    selected_branch = None
    expenses = Transaction.objects.none()

    if branches.exists():
        selected_branch_id = request.GET.get('branch')

        if selected_branch_id:
            selected_branch = get_object_or_404(Branch, id=selected_branch_id)
        else:
            selected_branch = branches.first()  # default to first branch

        expenses = Transaction.objects.filter(branch=selected_branch, transaction_type='expense')

    return render(request, 'home/expenses.html', {
        'branches': branches,
        'selected_branch': selected_branch,
        'expenses': expenses,
    })


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
