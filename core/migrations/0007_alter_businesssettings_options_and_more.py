# Generated by Django 5.2.1 on 2025-06-21 07:23

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_remove_transaction_items_remove_transaction_quantity_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='businesssettings',
            options={'verbose_name_plural': 'Business Settings'},
        ),
        migrations.RemoveField(
            model_name='businesssettings',
            name='loyalty_points_per_visit',
        ),
        migrations.AddField(
            model_name='businesssettings',
            name='loyalty_points_per_ugx_spent',
            field=models.DecimalField(decimal_places=2, default=100.0, help_text='Amount in UGX a customer needs to spend to earn 1 loyalty point.', max_digits=10),
        ),
        migrations.AddField(
            model_name='coupon',
            name='times_used',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='transaction',
            name='serviced_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='serviced_transactions', to='core.branchemployee'),
        ),
        migrations.AddField(
            model_name='transactionitem',
            name='employee',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='item_sales', to='core.branchemployee'),
        ),
        migrations.AlterField(
            model_name='businesssettings',
            name='business',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='settings', to='core.business'),
        ),
        migrations.AlterField(
            model_name='businesssettings',
            name='coupon_discount_percent',
            field=models.DecimalField(decimal_places=2, default=10.0, help_text='Default percentage discount for coupons if not overridden by specific coupon settings.', max_digits=5, validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(100.0)]),
        ),
        migrations.AlterField(
            model_name='businesssettings',
            name='coupon_min_spend',
            field=models.DecimalField(decimal_places=2, default=0.0, help_text='Minimum transaction amount required for any coupon to be applied (0 for no minimum).', max_digits=10),
        ),
        migrations.AlterField(
            model_name='businesssettings',
            name='loyalty_discount_percent',
            field=models.DecimalField(decimal_places=2, default=5.0, help_text='Percentage discount applied when loyalty points are redeemed (e.g., 5 for 5%).', max_digits=5, validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(100.0)]),
        ),
        migrations.AlterField(
            model_name='businesssettings',
            name='loyalty_points_required_for_discount',
            field=models.IntegerField(default=500, help_text='Number of loyalty points required for a customer to qualify for a discount.'),
        ),
        migrations.AlterField(
            model_name='party',
            name='phone',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
    ]
