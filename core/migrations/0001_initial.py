# Generated by Django 5.2.1 on 2025-06-25 14:14

import django.contrib.auth.models
import django.contrib.auth.validators
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Branch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('location', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('full_name', models.CharField(blank=True, max_length=100)),
                ('phone', models.CharField(blank=True, max_length=15)),
                ('address', models.TextField(blank=True)),
                ('gender', models.CharField(choices=[('M', 'Male'), ('F', 'Female')], max_length=1)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='BranchEmployee',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active', max_length=20)),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='employees', to='core.branch')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Business',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('contact', models.CharField(max_length=15)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('owner', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='branch',
            name='business',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='branches', to='core.business'),
        ),
        migrations.CreateModel(
            name='BusinessSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('loyalty_points_per_ugx_spent', models.DecimalField(decimal_places=2, default=100.0, help_text='Amount in UGX a customer needs to spend to earn 1 loyalty point.', max_digits=10)),
                ('enable_loyalty_point_earning', models.BooleanField(default=True, help_text='Allow customers to earn loyalty points on purchases.')),
                ('enable_loyalty_point_redemption', models.BooleanField(default=False, help_text='Allow customers to redeem loyalty points for discounts.')),
                ('loyalty_points_required_for_redemption', models.IntegerField(default=500, help_text='Minimum loyalty points a customer must have to redeem for a discount.')),
                ('loyalty_redemption_discount_type', models.CharField(choices=[('percentage', 'Percentage'), ('fixed', 'Fixed Amount')], default='percentage', help_text='Type of discount when loyalty points are redeemed.', max_length=10)),
                ('loyalty_redemption_discount_value', models.DecimalField(decimal_places=2, default=5.0, help_text='Value of discount (e.g., 5 for 5% or 5000 for UGX 5000). If Percentage, value should be 0-100.', max_digits=10)),
                ('loyalty_redemption_max_discount_amount', models.DecimalField(blank=True, decimal_places=2, default=0.0, help_text='Maximum fixed amount discount (UGX) a loyalty redemption can provide. Leave 0 or blank for no max.', max_digits=10, null=True)),
                ('loyalty_redemption_is_branch_specific', models.BooleanField(default=False, help_text='If checked, loyalty points can only be redeemed at the branch where they were earned.')),
                ('enable_coupon_codes', models.BooleanField(default=False, help_text='Allow the use of coupon codes in transactions.')),
                ('coupon_loyalty_requirement_type', models.CharField(choices=[('none', 'No loyalty requirement'), ('min_spend', 'Minimum total spend'), ('min_visits', 'Minimum visits'), ('both', 'Minimum spend AND visits'), ('either', 'Minimum spend OR visits')], default='none', help_text="How loyalty affects coupon eligibility. 'Both' means customer must meet both criteria. 'Either' means customer meets at least one.", max_length=20)),
                ('loyalty_min_spend_for_coupon', models.DecimalField(blank=True, decimal_places=2, default=0.0, help_text="Minimum total amount a customer must have spent to be eligible for a coupon. Required if loyalty requirement is not 'none'.", max_digits=10, null=True)),
                ('loyalty_min_visits_for_coupon', models.IntegerField(blank=True, default=0, help_text="Minimum number of visits a customer must have made to be eligible for a coupon. Required if loyalty requirement is not 'none'.", null=True)),
                ('coupon_is_branch_specific', models.BooleanField(default=False, help_text='If checked, coupon codes can only be used at branches explicitly assigned to the coupon.')),
                ('business', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='settings', to='core.business')),
            ],
            options={
                'verbose_name_plural': 'Business Settings',
            },
        ),
        migrations.CreateModel(
            name='Coupon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=50, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('discount_type', models.CharField(choices=[('percentage', 'Percentage'), ('fixed', 'Fixed Amount')], default='percentage', max_length=10)),
                ('discount_value', models.DecimalField(decimal_places=2, help_text='If percentage, value is 0-100. If fixed, value is actual amount.', max_digits=10)),
                ('minimum_spend', models.DecimalField(decimal_places=2, default=0.0, help_text='Minimum transaction amount required for this coupon to apply.', max_digits=10)),
                ('is_active', models.BooleanField(default=True)),
                ('valid_from', models.DateTimeField(default=django.utils.timezone.now)),
                ('valid_until', models.DateTimeField(blank=True, null=True)),
                ('usage_limit', models.IntegerField(blank=True, help_text='Maximum number of times this coupon can be used overall. Leave blank for unlimited.', null=True)),
                ('times_used', models.IntegerField(default=0)),
                ('business', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='coupons', to='core.business')),
                ('valid_branches', models.ManyToManyField(blank=True, help_text="Branches where this coupon is valid. If left blank and 'Coupon is branch specific' is checked in Business Settings, this coupon will be invalid.", related_name='coupons', to='core.branch')),
            ],
            options={
                'ordering': ['-valid_from'],
            },
        ),
        migrations.CreateModel(
            name='ExpenseCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='expense_categories', to='core.business')),
            ],
            options={
                'unique_together': {('business', 'name')},
            },
        ),
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('service', 'Service'), ('product', 'Product')], max_length=20)),
                ('name', models.CharField(max_length=100)),
                ('selling_price', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0.0)])),
                ('cost_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0.0)])),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='core.business')),
            ],
            options={
                'unique_together': {('business', 'name', 'type')},
            },
        ),
        migrations.CreateModel(
            name='Party',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gender', models.CharField(blank=True, choices=[('Male', 'Male'), ('Female', 'Female')], max_length=50, null=True)),
                ('type', models.CharField(choices=[('customer', 'Customer'), ('supplier', 'Supplier')], max_length=10)),
                ('full_name', models.CharField(max_length=100)),
                ('phone', models.CharField(blank=True, max_length=15, null=True)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('address', models.TextField(blank=True, null=True)),
                ('company', models.CharField(blank=True, max_length=150, null=True)),
                ('loyalty_points', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('branch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.branch')),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parties', to='core.business')),
            ],
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('completed', 'Completed'), ('voided', 'Voided'), ('refunded', 'Refunded')], default='completed', help_text='Overall status of the transaction (e.g., Completed, Voided, Refunded).', max_length=20)),
                ('voided_at', models.DateTimeField(blank=True, null=True)),
                ('refund_amount', models.DecimalField(decimal_places=2, default=0.0, help_text="Amount refunded for this transaction (if status is 'refunded').", max_digits=10)),
                ('transaction_type', models.CharField(choices=[('revenue', 'Customer Purchase'), ('expense', 'Expense')], max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('payment_method', models.CharField(choices=[('Cash', 'Cash'), ('Card', 'Card'), ('MobileMoney', 'Mobile Money')], max_length=20)),
                ('is_paid', models.BooleanField(default=False)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('discount_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('loyalty_points_earned', models.IntegerField(default=0)),
                ('loyalty_points_redeemed', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('expense_name', models.CharField(blank=True, max_length=200, null=True)),
                ('branch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='core.branch')),
                ('coupon', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.coupon')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('expense_category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.expensecategory')),
                ('party', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.party')),
                ('serviced_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='serviced_transactions', to='core.branchemployee')),
                ('voided_by', models.ForeignKey(blank=True, help_text='User who voided this transaction.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='voided_transactions', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='TransactionItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('employee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='item_sales', to='core.branchemployee')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.item')),
                ('transaction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transaction_items', to='core.transaction')),
            ],
        ),
        migrations.CreateModel(
            name='UserRole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='roles', to='core.business')),
            ],
        ),
        migrations.AddField(
            model_name='branchemployee',
            name='role',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.userrole'),
        ),
        migrations.AlterUniqueTogether(
            name='branch',
            unique_together={('business', 'name', 'location')},
        ),
        migrations.AlterUniqueTogether(
            name='branchemployee',
            unique_together={('user', 'branch', 'role')},
        ),
    ]
