from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('transaction_reports', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TransactionReportItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_time', models.DateTimeField()),
                ('amount', models.DecimalField(max_digits=12, decimal_places=2)),
                ('type', models.CharField(max_length=16, choices=[('success', 'Success'), ('refund', 'Refund')])),
                ('commission_percent', models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)),
                ('payable_amount', models.DecimalField(max_digits=12, decimal_places=2)),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='transaction_reports.TransactionReport')),
            ],
            options={'db_table': 'transaction_report_item'},
        ),
    ]
