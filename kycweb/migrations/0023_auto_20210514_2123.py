# Generated by Django 3.1.7 on 2021-05-14 21:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('kycweb', '0022_auto_20210514_1300'),
    ]

    operations = [
        migrations.AddField(
            model_name='krapincert',
            name='file',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='kra_file_source', to='kycweb.fileinstances'),
        ),
        migrations.AddField(
            model_name='natid',
            name='file',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='id_file_source', to='kycweb.fileinstances'),
        ),
    ]
