from django.utils import timezone
from decimal import Decimal, InvalidOperation
import json
from django.contrib import messages
import uuid
from django.forms import formset_factory, inlineformset_factory
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse, reverse_lazy
from .models import Branch, BranchEmployee, BusinessSettings, Coupon, Item, Party, Transaction, TransactionItem, User, UserRole
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
from django.db.models import Sum, Count
from django.contrib.humanize.templatetags.humanize import intcomma 
from django.views.decorators.csrf import csrf_protect

from core import forms
import io
from django.template.loader import get_template 

@login_required
def get_customer_details(request, customer_id):
    """
    API endpoint to fetch details of an existing customer,
    specifically loyalty points, total spend, and total visits.
    """
    try:
        # Ensure the customer belongs to the current user's business
        # Add prefetch/select_related here if Party.total_spend/total_visits are not direct fields
        # but calculated from related models (e.g., related transactions)
        customer = Party.objects.get(id=customer_id, business=request.user.business)
        
        data = {
            'success': True,
            'full_name': customer.full_name,
            'phone': customer.phone,
            'email': customer.email,
            'address': customer.address,
            'gender': customer.gender,
            'loyalty_points': customer.loyalty_points,
            # Convert Decimal to float for JSON serialization.
            # Make sure 'total_spend' and 'total_visits' exist on your Party model (as fields or properties).
            'total_spend': float(customer.total_spend) if hasattr(customer, 'total_spend') and customer.total_spend is not None else 0.00,
            'total_visits': customer.total_visits if hasattr(customer, 'total_visits') and customer.total_visits is not None else 0,
            'branch_id': customer.branch.id if customer.branch else None,
        }
    except Party.DoesNotExist:
        data = {'success': False, 'error': 'Customer not found.'}
    except Exception as e:
        # Log the actual exception for debugging
        print(f"Error in get_customer_details: {e}")
        data = {'success': False, 'error': 'An unexpected error occurred.'}
    return JsonResponse(data)

@login_required # Protect this view
@require_POST
def update_transaction_status(request, pk):
    """
    API endpoint to update the status of a specific transaction (e.g., void, refund).
    Expected to receive JSON: {'status': 'new_status'}
    """
    try:
        transaction = get_object_or_404(Transaction, pk=pk, branch__business=request.user.business)
        
        # Ensure only staff or specific roles can perform this action
        if not request.user.is_staff: # Or check custom permission: if not request.user.has_perm('transactions.can_change_status'):
             return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

        data = json.loads(request.body)
        new_status = data.get('status')

        valid_transitions = {
            'completed': ['voided', 'refunded'],
            # You can define other valid transitions here if needed
        }

        # Check if the new_status is valid and the transition is allowed
        if new_status not in ['voided', 'refunded'] or \
           new_status not in valid_transitions.get(transaction.status, []):
            return JsonResponse({'success': False, 'error': f'Invalid status or transition not allowed from {transaction.status} to {new_status}.'}, status=400)

        # Additional business logic for voiding/refunding
        if new_status == 'voided':
            # Example: If you need to revert stock or special accounting
            # transaction.void_transaction() # A method on your model
            pass
        elif new_status == 'refunded':
            # Example: If you need to process a refund, generate a refund record
            # transaction.initiate_refund() # A method on your model
            pass

        transaction.status = new_status
        transaction.save()
        return JsonResponse({'success': True, 'message': f'Transaction status updated to {new_status}.'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON in request body.'}, status=400)
    except Exception as e:
        # Log the error for debugging
        print(f"Error updating transaction status for PK {pk}: {e}")
        return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'}, status=500)


@login_required # Protect this view
@require_POST
# @csrf_protect # Use this in production.
def toggle_payment_status(request, pk):
    """
    API endpoint to toggle the payment status (is_paid) of a specific transaction.
    Expected to receive JSON: {'is_paid': true/false}
    """
    try:
        transaction = get_object_or_404(Transaction, pk=pk, branch__business=request.user.business)

        # Ensure only staff or specific roles can perform this action
        if not request.user.is_staff: # Or check custom permission
             return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

        data = json.loads(request.body)
        is_paid_new = data.get('is_paid')

        if not isinstance(is_paid_new, bool):
            return JsonResponse({'success': False, 'error': 'Invalid value for is_paid. Must be true or false.'}, status=400)

        transaction.is_paid = is_paid_new
        if is_paid_new:
            if not transaction.paid_at: # Only update paid_at if it's currently null
                transaction.paid_at = timezone.now()
        else:
            transaction.paid_at = None # Clear paid_at if marked as pending

        transaction.save()
        return JsonResponse({'success': True, 'message': 'Payment status updated.'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON in request body.'}, status=400)
    except Exception as e:
        # Log the error for debugging
        print(f"Error toggling payment status for PK {pk}: {e}")
        return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'}, status=500)

from django.views.decorators.clickjacking import xframe_options_sameorigin

@login_required
@xframe_options_sameorigin
def receipt_view(request, transaction_id):
    transaction = get_object_or_404(
        Transaction.objects
        .select_related(
            'branch',            # Select related Branch
            'party',             # Select related Customer/Party
            'branch__business',  # Select related Business through Branch
            'branch__business__owner' # Select related User (owner) through Business
        )
        .prefetch_related(
            'transaction_items',                # Prefetch all transaction items
            'transaction_items__item',          # Prefetch the Item related to each TransactionItem
            'transaction_items__employee',      # Prefetch the BranchEmployee related to each TransactionItem
            'transaction_items__employee__user' # Prefetch the User related to each BranchEmployee
        ),
        id=transaction_id, 
        branch__business=request.user.business # Security check: ensure the transaction belongs to the user's business
    )
    
    context = {
        'transaction': transaction,
        'business': transaction.branch.business, # Access business through the transaction's branch
        'branch': transaction.branch,          # Access branch directly from the transaction
        # All other necessary data like item details, employee, etc., are now directly accessible
        # via the 'transaction' object due to prefetch_related
    }
    
    # Render for preview
    if 'preview' in request.GET:
        return render(request, 'home/receipt_template.html', context)
    
    # Generate PDF for download
    template = get_template('home/receipt_template.html')
    html = template.render(context)
    result = io.BytesIO()
    pdf = pisa.CreatePDF(io.BytesIO(html.encode("UTF-8")), result) # Use CreatePDF instead of pisaDocument directly

    # Check for errors in PDF generation
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="receipt_{transaction.id}.pdf"'
        return response
    
    return HttpResponse('Error generating PDF', status=500)


TransactionItemFormSet = inlineformset_factory(Transaction, TransactionItem, form=TransactionItemForm, extra=1, can_delete=True)

@login_required
def get_items_by_category(request): # This AJAX endpoint might become redundant if all items are loaded
    category = request.GET.get('category') # If you still use it for anything else, keep it.
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
    
    formatted_employees = [{'id': emp['id'], 'name': emp['user__full_name'] or emp['user__username']} for emp in employees]
    return JsonResponse(formatted_employees, safe=False)

@login_required
def get_customer_loyalty_data(request):
    """
    AJAX endpoint to fetch customer loyalty points and transaction count/spend
    for dynamic display and validation on the frontend.
    """
    customer_id = request.GET.get('customer_id')
    try:
        customer = Party.objects.get(id=customer_id, business=request.user.business, type='customer')
        
        total_customer_spend = Transaction.objects.filter(
            party=customer,
            transaction_type='revenue',
            is_paid=True
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        total_customer_visits = Transaction.objects.filter(
            party=customer,
            transaction_type='revenue',
            is_paid=True
        ).count()

        business_settings = BusinessSettings.objects.get_or_create(business=request.user.business)[0]

        data = {
            'success': True,
            'loyalty_points': customer.loyalty_points,
            'total_spend': float(total_customer_spend),
            'total_visits': total_customer_visits,
            'enable_loyalty_point_redemption': business_settings.enable_loyalty_point_redemption,
            'loyalty_points_required_for_redemption': business_settings.loyalty_points_required_for_redemption,
            'loyalty_redemption_discount_type': business_settings.loyalty_redemption_discount_type,
            'loyalty_redemption_discount_value': float(business_settings.loyalty_redemption_discount_value),
            'loyalty_redemption_max_discount_amount': float(business_settings.loyalty_redemption_max_discount_amount) if business_settings.loyalty_redemption_max_discount_amount else 0,
            'loyalty_redemption_is_branch_specific': business_settings.loyalty_redemption_is_branch_specific,
            # Pass details about current customer's branches for branch-specific loyalty
            'customer_branch_id': customer.branch.id if customer.branch else None,
            'enable_coupon_codes': business_settings.enable_coupon_codes,
            'coupon_loyalty_requirement_type': business_settings.coupon_loyalty_requirement_type,
            'loyalty_min_spend_for_coupon': float(business_settings.loyalty_min_spend_for_coupon) if business_settings.loyalty_min_spend_for_coupon else 0,
            'loyalty_min_visits_for_coupon': business_settings.loyalty_min_visits_for_coupon if business_settings.loyalty_min_visits_for_coupon else 0,
            'coupon_is_branch_specific': business_settings.coupon_is_branch_specific,
        }
        return JsonResponse(data)
    except Party.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Customer not found.'}, status=404)
    except BusinessSettings.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Business settings not found.'}, status=500)


# Helper to get item prices for JS
def get_item_prices_json(business):
    # CORRECTED: Simply select 'type' as a field, no double underscore
    items = Item.objects.filter(business=business).values('id', 'name', 'selling_price', 'type')
    item_prices = {
        str(item['id']): {
            'name': item['name'],
            'price': str(item['selling_price']),
            'type': item['type'] # Access directly as 'type'
        } for item in items
    }
    return item_prices

@login_required
def revenue_create_view(request):
    business = get_user_business(request.user.business)
    business_settings = BusinessSettings.objects.get(business=request.user.business)
    TransactionItemFormSet = formset_factory(TransactionItemForm, extra=1)
    item_prices_json = get_item_prices_json(request.user.business)


    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        
        selected_branch = None
        if request.POST.get('branch'):
            try:
                selected_branch = Branch.objects.get(id=request.POST.get('branch'), business=request.user.business)
            except Branch.DoesNotExist:
                messages.error(request, 'Invalid branch selected.')
                # If branch is invalid, we can't proceed, re-render form
                formset = TransactionItemFormSet(request.POST, prefix='items',
                                                 form_kwargs={'business': request.user.business, 'branch': None}) # Pass None if branch is invalid
                context = {
                    'form': form, 'formset': formset, 'business_settings': business_settings, 'item_prices_json': item_prices_json
                }
                return render(request, 'home/add_revenue.html', context)


        formset = TransactionItemFormSet(request.POST, prefix='items',
                                         form_kwargs={'business': request.user.business, 'branch': selected_branch})


        if form.is_valid() and formset.is_valid():
            with db_transaction.atomic():
                transaction_obj = form.save(commit=False) 

                customer_selection_type = form.cleaned_data['customer_selection_type']
                customer = None 

                if customer_selection_type == 'new':
                    party_data = {
                        'business': request.user.business,
                        'full_name': form.cleaned_data['new_customer_name'],
                        'phone': form.cleaned_data['new_customer_phone'],
                        'email': form.cleaned_data['new_customer_email'],
                        'address': form.cleaned_data['new_customer_address'],
                        'gender': form.cleaned_data['new_customer_gender'],
                        'type': 'customer', 
                        'branch': selected_branch, # Link new customer to the selected transaction branch
                        'loyalty_points': 0, 
                    }
                    
                    _created = False
                    if party_data['phone']:
                        customer, _created = Party.objects.get_or_create(
                            phone=party_data['phone'],
                            business=party_data['business'],
                            defaults=party_data
                        )
                    elif party_data['email']:
                        customer, _created = Party.objects.get_or_create(
                            email=party_data['email'],
                            business=party_data['business'],
                            defaults=party_data
                        )
                    else: 
                        customer = Party.objects.create(**party_data)
                        _created = True
                        
                    if not _created:
                        for key, value in party_data.items():
                            if key not in ['business', 'phone', 'email']:
                                setattr(customer, key, value)
                        customer.save()
                        messages.info(request, f"Existing customer '{customer.full_name}' updated successfully.")
                    else:
                        messages.info(request, f"New customer '{customer.full_name}' created successfully.")

                else: # customer_selection_type == 'existing'
                    customer = form.cleaned_data['existing_customer']
                    if not customer: 
                        messages.error(request, 'No existing customer was selected. Please select one.')
                        context = {
                            'form': form, 'formset': formset, 'business_settings': business_settings, 'item_prices_json': item_prices_json
                        }
                        return render(request, 'home/add_revenue.html', context)

                # Assign customer and other initial transaction details
                transaction_obj.party = customer 
                transaction_obj.transaction_type = 'revenue' 
                transaction_obj.created_by = request.user
                transaction_obj.branch = selected_branch 
                transaction_obj.status = 'completed' # Set initial status for new transaction


                sub_total = 0 
                transaction_items_to_save = [] 
                
                for item_form in formset:
                    if item_form.cleaned_data.get('DELETE'):
                        continue
                    item = item_form.cleaned_data['item']
                    quantity = item_form.cleaned_data['quantity']
                    
                    sub_total += item.selling_price * quantity

                    transaction_item = item_form.save(commit=False)
                    transaction_item.item = item 
                    transaction_item.quantity = quantity 
                    transaction_item.transaction = transaction_obj 
                    transaction_items_to_save.append(transaction_item)

                total_discount_amount = 0 
                coupon_applied_obj = None 
                loyalty_points_redeemed_current_transaction = 0
                loyalty_points_earned_current_transaction = 0

                coupon_applied_obj = form.cleaned_data.get('coupon') 
                
                if business_settings.enable_coupon_codes and coupon_applied_obj: 
                    discount_value_from_coupon = 0
                    if coupon_applied_obj.discount_type == 'percentage':
                        discount_value_from_coupon = (sub_total * coupon_applied_obj.discount_value) / 100
                        if coupon_applied_obj.max_discount_amount and discount_value_from_coupon > coupon_applied_obj.max_discount_amount:
                            discount_value_from_coupon = coupon_applied_obj.max_discount_amount
                    elif coupon_applied_obj.discount_type == 'fixed':
                        discount_value_from_coupon = coupon_applied_obj.discount_value
                    
                    total_discount_amount += discount_value_from_coupon
                    messages.success(request, f"Coupon '{coupon_applied_obj.code}' applied successfully!")
                
                transaction_obj.coupon = coupon_applied_obj

                if business_settings.enable_loyalty_point_redemption and form.cleaned_data.get('redeem_loyalty_points') and customer:
                    required_points = business_settings.loyalty_points_required_for_redemption
                    if customer.loyalty_points >= required_points:
                        if business_settings.loyalty_redemption_is_branch_specific and \
                           customer.branch and customer.branch != transaction_obj.branch:
                            messages.warning(request, "Loyalty points can only be redeemed at the customer's home branch.")
                        else:
                            loyalty_discount_value = business_settings.loyalty_redemption_discount_value
                            loyalty_discount_amount = 0
                            remaining_total_for_loyalty = sub_total - total_discount_amount

                            if business_settings.loyalty_redemption_discount_type == 'percentage':
                                loyalty_discount_amount = (remaining_total_for_loyalty * loyalty_discount_value) / 100
                                if business_settings.loyalty_redemption_max_discount_amount and loyalty_discount_amount > business_settings.loyalty_redemption_max_discount_amount:
                                    loyalty_discount_amount = business_settings.loyalty_redemption_max_discount_amount
                            elif business_settings.loyalty_redemption_discount_type == 'fixed':
                                loyalty_discount_amount = loyalty_discount_value

                            loyalty_discount_amount = min(loyalty_discount_amount, remaining_total_for_loyalty)
                            
                            total_discount_amount += loyalty_discount_amount 
                            loyalty_points_redeemed_current_transaction = required_points 
                            customer.loyalty_points -= required_points 
                            customer.save() 
                            messages.success(request, f"Loyalty points redeemed for UGX {intcomma(loyalty_discount_amount)} discount.")
                    else:
                        messages.warning(request, f"Customer does not have enough loyalty points to redeem. Required: {required_points}, Has: {customer.loyalty_points}.")
                
                transaction_obj.discount_amount = total_discount_amount

                final_amount = sub_total - total_discount_amount
                if final_amount < 0:
                    final_amount = 0 
                
                transaction_obj.amount = final_amount 

                transaction_obj.loyalty_points_redeemed = loyalty_points_redeemed_current_transaction

                transaction_obj.save() # Save transaction_obj for the first time

                for transaction_item in transaction_items_to_save:
                    transaction_item.transaction = transaction_obj 
                    transaction_item.save()

                # Loyalty Point Earning logic
                if customer: # Ensure customer exists for loyalty
                    if business_settings.enable_loyalty_point_earning: # Use the correct field here
                        if business_settings.loyalty_points_per_ugx_spent and business_settings.loyalty_points_per_ugx_spent > 0:
                            points_earned = int(final_amount / business_settings.loyalty_points_per_ugx_spent)
                        else:
                            points_earned = 0 # Cannot earn points if setting is 0 or invalid
                        
                        customer.loyalty_points += points_earned
                        transaction_obj.loyalty_points_earned = points_earned 
                        customer.save() # Save customer with updated points
                        # Only update loyalty_points_earned on transaction_obj if it changed (it will have)
                        transaction_obj.save(update_fields=['loyalty_points_earned']) 
                    else:
                        transaction_obj.loyalty_points_earned = 0 # Explicitly set to 0 if earning is disabled
                        transaction_obj.save(update_fields=['loyalty_points_earned']) 

                messages.success(request, 'Customer purchase recorded successfully!')
                return redirect(reverse('revenue_list'))

        else: # Form or Formset is not valid
            context = {
                'form': form,
                'formset': formset,
                'business_settings': business_settings,
                'item_prices_json': item_prices_json,
            }
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Form Error - '{form[field].label or field}': {error}")
            for i, fs_errors in enumerate(formset.errors):
                if fs_errors: 
                    messages.error(request, f"Item {i+1} Errors:")
                    for field, errors in fs_errors.items():
                        for error in errors:
                            messages.error(request, f"  '{formset[i][field].label or field}': {error}")
            
            return render(request, 'home/add_revenue.html', context)


    else: # GET request
        form = TransactionForm(user=request.user)
        formset = TransactionItemFormSet(prefix='items', form_kwargs={'business': request.user.business, 'branch': None})

    context = {
        'form': form,
        'formset': formset,
        'business_settings': business_settings,
        'item_prices_json': item_prices_json,
    }
    return render(request, 'home/add_revenue.html', context)


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
        type = request.POST.get('type')
        name = request.POST.get('name', '').strip()
        selling_price = request.POST.get('selling_price')
        cost_price = request.POST.get('cost_price')

        # Validation
        if not type:
            form_errors.append("Item Type is required.")
        if not name:
            form_errors.append("Name is required.")
        if not selling_price:
            form_errors.append("Selling Price is required.")
        if type == 'product' and not cost_price:
            form_errors.append("Cost Price is required for products.")

        if not form_errors:
            if type not in ['service', 'product']:
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
                    form_errors.append(f"A {type} named '{name}' already exists for this business.")

                if not form_errors:
                    try:
                        Item.objects.create(
                            business=business,
                            type=type,
                            name=name,
                            selling_price=selling_price,
                            cost_price=cost_price if type == 'product' else None
                        )
                        logger.info("Created item: %s (%s) for business %s", name, type, business)
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
        item_type = request.POST.get('type')

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

# NEW VIEW FOR VOIDING TRANSACTIONS
@login_required
def transaction_void_view(request, pk):
    # Ensure only transactions for the user's business can be voided
    transaction = get_object_or_404(
        Transaction, 
        pk=pk, 
        created_by__business=request.user.business,
        transaction_type='revenue' # Only allow voiding revenue transactions from this view
    )

    if request.method == 'POST':
        if transaction.mark_as_voided(request.user):
            messages.success(request, f"Transaction #{transaction.id} has been voided.")
            # TODO: Add logic here to reverse inventory, loyalty points, etc. if needed
            # This is complex and depends on your business rules.
            # For now, it just marks the transaction.
        else:
            messages.warning(request, f"Transaction #{transaction.id} cannot be voided (current status: {transaction.status}).")
        return redirect(reverse('revenue_list') + f"?branch={transaction.branch.id}") # Redirect to the same branch list

    # For GET request, just display a confirmation page (optional)
    context = {
        'transaction': transaction
    }
    return render(request, 'home/transaction_void_confirm.html', context) # Create this template

# revenue_list_view (updated)
@login_required
def revenue_list_view(request):
    business = request.user.business
    branches = Branch.objects.filter(business=business).order_by('name')

    if not branches.exists():
        return render(request, 'home/revenue.html', {
            'branches': [],
            'selected_branch': None,
            'transactions': None,
        })

    selected_branch_id = request.GET.get('branch')
    if selected_branch_id:
        selected_branch = get_object_or_404(Branch, id=selected_branch_id, business=business)
    else:
        selected_branch = branches.first()

    # Filter transactions to only show 'completed' ones by default,
    # or allow users to view 'voided'/'refunded' if needed via a filter.
    # For now, display all for demonstration, but production might filter.
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
        'intcomma': intcomma # Pass intcomma to context for use outside loop if needed
    }
    return render(request, 'home/revenue.html', context)


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
