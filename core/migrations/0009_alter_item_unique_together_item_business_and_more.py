from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_alter_user_gender'),
    ]

    operations = [
        # Step 1: Remove old constraint that references 'branch'
        migrations.AlterUniqueTogether(
            name='item',
            unique_together=set(),  # clear it first
        ),

        # Step 2: Remove the 'branch' field (safe now)
        migrations.RemoveField(
            model_name='item',
            name='branch',
        ),

        # Step 3: Add new 'business' field
        migrations.AddField(
            model_name='item',
            name='business',
            field=models.ForeignKey(to='core.business', on_delete=django.db.models.deletion.CASCADE, related_name='items', default=1),
            preserve_default=False,
        ),

        # Step 4: Apply new constraint
        migrations.AlterUniqueTogether(
            name='item',
            unique_together={('business', 'name', 'type')},
        ),
    ]
