# Generated by Django 2.0.1 on 2018-03-17 14:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0008_preferences_is_only_auth'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='log',
            name='date_time',
        ),
        migrations.AddField(
            model_name='log',
            name='date',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
    ]