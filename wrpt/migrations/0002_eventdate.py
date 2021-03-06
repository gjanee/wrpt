# Generated by Django 2.1.7 on 2019-03-08 02:53

import django.core.validators
from django.db import migrations, models
import wrpt.models


class Migration(migrations.Migration):

    dependencies = [
        ('wrpt', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='eventdate',
            name='seq',
        ),
        migrations.AlterField(
            model_name='count',
            name='activeValue',
            field=models.IntegerField(blank=True, help_text='Number of students who walked/biked/scootered/etc', null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Active value'),
        ),
        migrations.AlterField(
            model_name='count',
            name='inactiveValue',
            field=models.IntegerField(blank=True, help_text='Number of students who carpooled/bused', null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Inactive value'),
        ),
        migrations.AlterField(
            model_name='eventdate',
            name='date',
            field=models.DateField(),
        ),
        migrations.AlterField(
            model_name='school',
            name='name',
            field=models.CharField(help_text='Ex: Adams, Goleta Valley JH, Citywide Walk & Roll Challenge', max_length=100, unique=True, validators=[wrpt.models.notBlankValidator]),
        ),
    ]
