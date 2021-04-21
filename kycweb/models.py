from enum import unique
import re
from typing import Pattern
from django.core.files.base import File
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
import random, string, os
from django.db.models.base import Model

from django.db.models.deletion import CASCADE, SET, SET_NULL
from django.db.models.fields.related import ForeignKey

def upload_folder(instance, filename):
    return '{0}'.format(instance.chest.chest_dir)

'''
Extending the standars user class
to a model that can be validated using
custom IDs and that can share their data
user pods they've created
''' 
class Usr(models.Model):
    #linking to default django usr model
    def_usr = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cust_usr')
    #extra user info/ validators
    profile_pic = models.ImageField(upload_to="profile_pics", default='static/default_pfp.jpg', blank=True)
    phone_regex = RegexValidator(regex=r'^07[0-9]{8}', message="Phone number must be entered in the format: '0799999999'.")
    phone_number = models.CharField(validators=[phone_regex], max_length=14, blank=True)
    #unique usr ID for accessing other chests
    ctx_id = models.CharField(max_length=14, blank=True)
    #usr diretory for files
    data_dir = models.CharField(max_length=400, blank=True)
    #full name: could be filled by the generic 
    #auth models
    full_name = models.CharField(max_length=500, blank=True, null=True)
    #birthdate: could also be filled by the generic auth models
    bdate = models.CharField(max_length=20, blank=True, null=True)
    #addr could be filled out by the generic auth models
    addr = models.CharField(max_length=500, blank=True, null=True)
    
    def save(self, *args, **kwargs):
        if self.data_dir is None or len(self.data_dir) < 1:
            self.data_dir = "users/{0}/".format(self.def_usr.id)
            os.makedirs(self.data_dir)
        if len(self.ctx_id)<1:
            ltrs = string.ascii_lowercase
            self.ctx_id = ''.join(random.choice(ltrs) for i in range(12))
        super(Usr, self).save(*args, **kwargs)

    def __str__(self):
        return self.def_usr.username

'''
Data chests where data is stored
and access is controlled by the user that created it
users can either create a registry for individual 
users or corps to access (accessed differently)
''' 
class Chest(models.Model):
    #User facing ID for chests
    chest_ID = models.CharField(max_length=20, blank=False)
    chest_name = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(Usr, related_name="Chest", on_delete=models.CASCADE)
    chest_dir = models.CharField(max_length=400)
    chest_size = models.CharField(max_length=100, blank=False)

    def set_size(self):
        ttl_size = 0
        for dir, dir_nm, fn in os.walk(self.chest_dir):
            for f in fn:
                fp = os.path.join(dir, f)
                if not os.path.islink(fp):
                    ttl_size += os.path.getsize(fp)
        self.chest_size = ttl_size

    # Each chest gets its own subdirectory on creation
    def save(self, *args, **kwargs):
        if len(self.chest_ID)<1:
            ltrs = string.ascii_lowercase
            self.chest_ID = ''.join(random.choice(ltrs) for i in range(12))
            if len(self.chest_name) < 1:
                self.chest_name = self.chest_ID
        if self.chest_dir is None or len(self.chest_dir) < 1:
            self.chest_dir = "{0}{1}".format(self.created_by.data_dir, self.chest_ID)
            os.makedirs(self.chest_dir)
        self.set_size()
        super(Chest, self).save(*args, **kwargs)

    def __str__(self):
        return self.chest_name

'''
File instances, to allow a chest to have
multiple files
'''
class FileInstances(models.Model):
    chest = models.ForeignKey(Chest, related_name="File", blank=False, on_delete=models.CASCADE)
    upload_path = models.CharField(max_length=400, blank=True, null=True)
    file_type = models.CharField(max_length=400, blank=True, null=True)

    # Whenever a new file instance is created
    # the chest size needs to be updated
    def save(self, *args, **kwargs):
        if len(self.upload_path) < 1:
            self.upload_path = self.chest.chest_dir
            nbytes = sum(os.path.getsize(f) for f in os.listdir(self.chest.chest_dir) if os.path.isfile(f))
            self.chest.chestsize = str(nbytes)
        super(FileInstances, self).save(*args, **kwargs)

    def __str__(self):
        return self.upload_path
'''
Corporation Require a single chest to handle 
its verification information as well as sys
identification fields. Technically a generic chest type
just like banking and work types, though some verification
is required for this to be valid.
'''
class Corporation(models.Model):
    key = models.CharField(max_length=14)
    name = models.CharField(max_length=100, blank=False)
    chest = models.ForeignKey(Chest, on_delete=models.CASCADE, blank=True, default=None)

    def save(self, *args, **kwargs):
        ltrs = string.ascii_lowercase
        self.key = ''.join(random.choice(ltrs) for i in 12)
        super(Chest, self).save(*args, **kwargs)

'''
Auth level for users of the system. Depending on the auth level
users can either do: banking transactions, or can be 
accepted by corporations oboarding systems
'''
class AuthLevel(models.Model):
    # each application has a specified chest instance
    # this points to what the user is authed for
    chest = models.ForeignKey(Chest, on_delete=CASCADE) 
    # The Auth level can either be:
    # none             - no auth related information is provided 
    # banking-[1-3]    - will accept banking applications,
    # work             - will accept HR related applications,
    level = models.CharField(max_length=256, default="none")
    user = models.ForeignKey(Usr, related_name="user", on_delete=models.CASCADE)
    # decides if applications can access the user chests 
    enabled = models.BooleanField(verbose_name="external auth enabled")

    def __str__(self) -> str:
        return self.level + " " + "for" + " " + self.user.def_usr.username
    
'''
registry of all hits to a specific chest
whenever a user/ company decides to 
access a chest, the access is registered.
this is to ensure before a view ofa chest
is generated the access credentials are checked
'''
class HitsRegistry(models.Model):
    # Needs 2 foreign keys to the accessing entity
    # and the chest
    usr = models.ForeignKey(Usr, blank=True, null=True, on_delete=models.SET_NULL)
    chest = models.ForeignKey(Chest, on_delete=models.CASCADE)
    corporation = models.ForeignKey(Corporation, blank=True, on_delete=models.CASCADE)
    tstmp = models.DateTimeField(auto_now_add=True) #access timestamp

'''
registry for all the users that can access
a specified chest (added by the chest creator)
permissions model kind of.
'''
class ChestRegistry(models.Model):
    # needs 2 foreign keys for a user/coorp
    # and the specified chest
    usr = models.ForeignKey(Usr, blank=True, on_delete=models.CASCADE)
    chest = models.ForeignKey(Chest, on_delete=models.CASCADE)
    corporation = models.ForeignKey(Corporation, blank=True, on_delete=models.CASCADE)
    # control whether or not the user has access
    # controls whether SPECIFIC users/applications can access certain chests
    # the more general auth models are protected by "AUTHLEVEL" this
    # could also be seen as a block functionality, certain applications
    # can explicitly be banned from using certain chests
    access = models.BooleanField(verbose_name="user access", default=True)

'''
a generic chest type that is specifically meant for storing
auth information related to banking applications
'''
class BankingChestType(models.Model):
    # link to the abstract chest type
    abstract_chest = models.ForeignKey(Chest, on_delete=CASCADE, related_name="bnk_chest_info")
    # banking auth application need specific documents
    # that maybe required at certain points
    bnk_id = ForeignKey(FileInstances, on_delete=SET_NULL, null=True, blank=True, related_name="bnk_id")
    kra = ForeignKey(FileInstances, on_delete=SET_NULL, null=True, blank=True, related_name="kra")
    utility = ForeignKey(FileInstances, on_delete=SET_NULL, null=True, blank=True, related_name="utility")

    def gen_auth_level(self):
        if self.bnk_id is None:
            AuthLevel.objects.create(
                level="none", user=self.abstract_chest.created_by, enabled=False)
        elif self.kra is None:
            AuthLevel.objects.create(
                level="banking1", user=self.abstract_chest.created_by, enabled=False)
        elif self.utility is None:
            AuthLevel.objects.create(
                level="banking2", user=self.abstract_chest.created_by, enabled=False)
        else:
            AuthLevel.objects.create(
                level="banking3", user=self.abstract_chest.created_by, enabled=False)
    
    def __str__(self):
        return self.abstract_chest.chest_name

'''
a generic chest type specifically meant to store
auth information for HR related applications
'''
class WorkChestType(models.Model):
    # link to the abstract chest type
    abstract_chest = models.ForeignKey(Chest, on_delete=CASCADE, related_name="work_chest_info")
    # banking auth application need specific documents
    # that maybe required at certain points
    wrk_id = ForeignKey(FileInstances, on_delete=SET_NULL, blank=True, null=True, related_name="work_id")
    kra  = ForeignKey(FileInstances, on_delete=SET_NULL, blank=True, null=True, related_name="work_kra")
    nhif = ForeignKey(FileInstances, on_delete=SET_NULL, blank=True, null=True, related_name="nhif")
    nssf = ForeignKey(FileInstances, on_delete=SET_NULL, blank=True, null=True, related_name="nssf")
    cogc = ForeignKey(FileInstances, on_delete=SET_NULL,  blank=True, null=True, related_name="cogc")


''' 
For generic extentions, if a new auth model is created, this
info is needed for a couple of operations: 
  1. Extraction of patterned information
  2. Validation via an endpoint (or 'trusted') if 
     the field is empty
Therefore a validation pattern for other documents can be created.
A few assumptions are made, the validator accepts www-formurl-encode
and expects the pattern to be POSTed to it.
- If a validator exists but not a pattern, it'll be assumed that the
  file itself is posted to the validator.
- If a validator doesn't exist but there's a pattern, the successfull extraction of
  the pattern assumes the document is valid.
- If neither a validator nor a pattern exists, the input will be accepted as 
  trivially true.
- Whether or not the validator accepts the input context give is assumes
  to be reflected by the return status code. 
The identifier is essentially what the validator expects the pattern to 
be called in its namespace. if its null, it'll be assumed that the 
file name is the identifier (this is undefined behaviourally).
'''
class Validator(models.Model):
    # Identifier for the validator
    name       = models.CharField(max_length=256, unique=True)
    validator  = models.CharField(max_length=256, null=True, blank=True)
    pattern    = models.CharField(max_length=256, null=True, blank=True)
    identifier = models.CharField(max_length=256, blank=True, null=True)

    def __str__(self) -> str:
        return self.name