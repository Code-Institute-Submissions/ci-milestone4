# Generated by Django 3.0.7 on 2020-09-16 00:06

from django.db import migrations
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contact', '0003_auto_20200902_1856'),
    ]

    operations = [
        migrations.AlterField(
            model_name='swarm',
            name='swarm_country',
            field=django_countries.fields.CountryField(default='GB', max_length=2),
        ),
    ]
