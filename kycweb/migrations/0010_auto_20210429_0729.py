# Generated by Django 3.1.7 on 2021-04-29 07:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kycweb', '0009_auto_20210429_0723'),
    ]

    operations = [
        migrations.AddField(
            model_name='authlevel',
            name='app',
            field=models.CharField(default='none', max_length=256),
        ),
        migrations.AlterField(
            model_name='authlevel',
            name='level',
            field=models.IntegerField(default=0, verbose_name='Auth level'),
        ),
    ]