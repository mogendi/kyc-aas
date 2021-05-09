# Generated by Django 3.1.7 on 2021-04-23 19:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('kycweb', '0005_auto_20210421_0833'),
    ]

    operations = [
        migrations.AddField(
            model_name='authlevel',
            name='chest',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='kycweb.chest'),
        ),
        migrations.AddField(
            model_name='chest',
            name='auth_chest',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='validator',
            name='auth',
            field=models.BooleanField(default=False, verbose_name='Allow auth for this validator'),
        ),
        migrations.AlterField(
            model_name='authlevel',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='auth_user', to='kycweb.usr'),
        ),
        migrations.AlterField(
            model_name='validator',
            name='name',
            field=models.CharField(max_length=256, unique=True),
        ),
    ]
