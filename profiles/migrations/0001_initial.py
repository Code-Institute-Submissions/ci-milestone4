# Generated by Django 3.0.7 on 2020-08-26 13:40

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_countries.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_tel', models.CharField(blank=True, max_length=20, null=True)),
                ('user_street_address1', models.CharField(blank=True, max_length=80, null=True)),
                ('user_street_address2', models.CharField(blank=True, max_length=80, null=True)),
                ('user_city', models.CharField(blank=True, max_length=40, null=True)),
                ('user_county', models.CharField(blank=True, max_length=80, null=True)),
                ('user_country', django_countries.fields.CountryField(blank=True, max_length=2, null=True)),
                ('user_postcode', models.CharField(blank=True, max_length=20, null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
