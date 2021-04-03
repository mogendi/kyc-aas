from django.test import TestCase
from django.contrib.auth.models import User
from .models import Usr, Chest, FileInstances, Chest, ChestRegistry, HitsRegistry

class UsrTestCase(TestCase):
    def setUp(self):
        pass

    def test_usr_directory(self):
        usr = Usr.objects.get(phone_number="0799762766")
        dir_ = "usr/{0}".format(usr.def_usr.id)
        self.assertEqual(usr.data_dir, dir_)