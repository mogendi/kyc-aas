from re import U
from django.contrib import admin
from .models import Usr, Chest, ChestRegistry, FileInstances, Corporation, HitsRegistry

admin.site.register([Usr, Chest, ChestRegistry, FileInstances, Corporation, HitsRegistry])
