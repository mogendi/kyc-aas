# Generated by Django 3.1.7 on 2021-05-01 10:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('kycweb', '0015_auto_20210501_0855'),
    ]

    operations = [
        migrations.AlterField(
            model_name='corporation',
            name='chest',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='kycweb.chest'),
        ),
    ]
