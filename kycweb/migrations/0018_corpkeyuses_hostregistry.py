# Generated by Django 3.1.7 on 2021-05-09 10:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('kycweb', '0017_auto_20210503_1830'),
    ]

    operations = [
        migrations.CreateModel(
            name='HostRegistry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('host', models.CharField(blank=True, max_length=500, null=True)),
                ('corp', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='kycweb.corporation')),
            ],
        ),
        migrations.CreateModel(
            name='CorpKeyUses',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tstmp', models.DateTimeField(auto_now_add=True)),
                ('host', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='kycweb.hostregistry')),
            ],
        ),
    ]