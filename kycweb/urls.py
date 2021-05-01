from os import name
from kycweb.models import BankingChestType
from django.urls import path
from django.views import static
from . import views

urlpatterns = \
    [
        #general
        path('home/', views.home, name="home"),
        path('', views.home, name="home"),

        #chests
        path('chests/', views.chests, name="chests"),
        path('new_chest/', views.ChestCreateView.as_view(), name="new_chest"),
        path('new_chest/bnk/', views.BankingChestCreateView.as_view(), name="new_banking_auth"),
        path('new_chest/wrk/', views.WorkChestCreateView.as_view(), name="new_work_auth"),
        path('delete/chest/<slug:slug>', views.DeleteChest.as_view(), name="delete_chest"),
        path('chests/view/<slug:slug>', views.ChestView.as_view(), name="chest"),
        path('extend/chest/', views.ChestView.extend_chest, name="extend_chest"),
        path('extend/auth/', views.ChestView.extend_auth, name="extend_auth"),

        #files
        path('check/id/', views.check_id, name="checkid"),
        path('check/kra/', views.check_kra, name="checkkra"),
        path('check/pic/', views.check_pic, name="checkpic"),
        path('delete/file/<int:fid>', views.FileOperations.delete_file, name="delete_file"),
        path('create/file/', views.FileOperations.create_file, name="create_file"),
        path('download/file/<int:fid>', views.FileOperations.download_file, name="download_file"),
        
        #perms
        path('switch/permissions/<int:reg_id>', views.ChestView.change_permissions, name="change_perm"),
        path('add/permissions/<slug:uid>', views.ChestView.add_permissions, name="add_permissions"),
        path('remove/permissions/<int:reg_id>', views.ChestView.remove_permissions, name="remove_permissions"),
        path('get/indv/perm/<int:pid>', views.ChestView.get_indiv_perm, name="get_indiv_perm"),

        #static
        path('demo/', static.serve),
        path('static/', static.serve),
        path('assets/js', static.serve)
    ]