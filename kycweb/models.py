import re
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
import random, string, os

from django.db.models.deletion import CASCADE

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
        super(Chest, self).save(*args, **kwargs)

    def __str__(self):
        return self.chest_name

'''
registry for all the users that can access
a specified chest (added by the chest creator)
'''
class ChestRegistry(models.Model):
    #needs 2 foreign keys for a user
    #and the specified chest
    usr = models.ForeignKey(Usr, on_delete=models.CASCADE)
    chest = models.ForeignKey(Chest, on_delete=models.CASCADE)
    #control whether or not the user has access
    access = models.BooleanField(verbose_name="user access", default=True)

'''
registry of all hits to a specific chest
whenever a user/ company decides to 
access a chest, the access is registered
'''
class HitsRegistry(models.Model):
    # Needs 2 foreign keys to the accessing entity
    # and the chest
    # TODO: The accessing entity is just users for now
    usr = models.ForeignKey(Usr, on_delete=models.CASCADE)
    Chest = models.ForeignKey(Chest, on_delete=models.CASCADE)
    tstmp = models.DateTimeField(auto_now_add=True) #access timestamp


'''
File instances, to allow a chest to have
multiple files
'''
class FileInstances(models.Model):
    chest = models.ForeignKey(Chest, related_name="File", blank=False, on_delete=models.CASCADE)
    upload_path = models.CharField(max_length=400, blank=True)
    file_type = models.CharField(max_length=400, blank=True)

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
identification fields
'''
class Corporation(models.Model):
    key = models.CharField(max_length=14)
    name = models.CharField(max_length=100, blank=False)
    chest = models.ForeignKey(Chest, on_delete=models.CASCADE, blank=True, default=None)

    def save(self, *args, **kwargs):
        ltrs = string.ascii_lowercase
        self.key = ''.join(random.choice(ltrs) for i in 12)
        super(Chest, self).save(*args, **kwargs)