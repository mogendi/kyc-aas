# Generated by Django 3.1.7 on 2021-04-21 07:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kycweb', '0003_auto_20210418_1106'),
    ]

    operations = [
        migrations.AddField(
            model_name='fileinstances',
            name='identifier',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.AddField(
            model_name='fileinstances',
            name='pattern',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.AddField(
            model_name='fileinstances',
            name='validator',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
    ]
