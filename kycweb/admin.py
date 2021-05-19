from re import U
from django.contrib import admin
from .models import ( Usr, Chest, ChestRegistry, FileInstances, 
                      Corporation, HitsRegistry, BankingChestType, 
                      WorkChestType, AuthLevel, Validator, HostRegistry,
                      CorpKeyUses, NatId, KRAPinCert, Authenticator, ValInstance) 

admin.site.register([Usr, Chest, ChestRegistry, FileInstances, 
                     Corporation, HitsRegistry, BankingChestType, 
                     WorkChestType, AuthLevel, Validator,
                     HostRegistry, CorpKeyUses, NatId, KRAPinCert, Authenticator, ValInstance])