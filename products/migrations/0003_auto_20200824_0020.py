# Generated by Django 3.0.7 on 2020-08-24 00:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_auto_20200822_0212'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productstock',
            name='product',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='productlines', to='products.ProductInfo'),
        ),
    ]
