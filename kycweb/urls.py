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
        path('chests/', views.GeneralChests.chests, name="chests"),
        path('new_chest/', views.ChestCreateView.as_view(), name="new_chest"),
        path('new_chest/bnk/', views.BankingChestCreateView.as_view(), name="new_banking_auth"),
        path('new_chest/wrk/', views.WorkChestCreateView.as_view(), name="new_work_auth"),
        path('delete/chest/<slug:slug>', views.DeleteChest.as_view(), name="delete_chest"),
        path('chests/view/<slug:slug>', views.ChestView.as_view(), name="chest"),
        path('extend/chest/', views.ChestView.extend_chest, name="extend_chest"),
        path('extend/auth/', views.ChestView.extend_auth, name="extend_auth"),
        path('open/chest/', views.GeneralChests.open_chest, name="open_chest"),
        path('search/chest/', views.GeneralChests.search_chest, name="search_chest"),
        path('view/all/hits/', views.GeneralChests.view_hits, name="view_hits"),

        #corporations
        path('companies/', views.GeneralCompany.as_view(), name="search_view"),
        path('companies/search/', views.GeneralCompany.search, name="search"),
        path('companies/add/perm/get/', views.GeneralCompany.add_perm_get, name="add_perm_get"),
        path('companies/add/perm/', views.GeneralCompany.add_perm, name="add_perm"),
        path('companies/rem/perm/get/', views.GeneralCompany.rem_perm_get, name="rem_perm_get"),
        path('companies/rem/perm/', views.GeneralCompany.rem_perm, name="rem_perm"),
        path('companies/rem/perm/all/', views.GeneralCompany.rem_perm_all, name="rem_perm_all"),
        path('companies/dash/', views.CompanyOperations.as_view(), name="company_dash"),
        path('companies/info/', views.CompanyOperations.corp_info, name="company_info"),
        path('companies/dash/open/', views.CompanyOperations.get_form, name="company_dash_open"),
        path('company/new/host/', views.CompanyOperations.new_host, name="new_host"),
        path('company/toggle/key/', views.CompanyOperations.toggle_key, name="toggle_key"),
        path('company/remove/host/', views.CompanyOperations.rem_host, name="remove_host"),
        path('company/toggle/uses/', views.CompanyOperations.toggle_uses, name="toggle_uses"),
        path('company/auth/', views.GeneralValidator.get_auth_create_view, name="company_auth"),

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

        #validators
        path('validate/id/', views.DefaultValidators.validate_id, name="validate_id"),
        path('validate/kra/', views.DefaultValidators.validate_kra, name="validate_kra"),
        path('validator/create/', views.GeneralValidator.as_view(), name="create_validator"),
        path('validator/auth/', views.GeneralValidator.get_auth_form, name="validate_user"),
        path('validator/view/', views.GeneralValidator.get_auth_view, name="authenticator_view"),
        path('auth/delete/', views.GeneralValidator.del_auth, name="authenticator_del"),
        path('validator/verify/', views.GeneralValidator.verify, name="verify"),
        path('validator/new/instance/', views.GeneralValidator.new_instance, name="new_instance"),
        path('validator/delete/', views.GeneralValidator.delete_val, name="delete_val"),

        #static
        path('demo/', static.serve),
        path('static/', static.serve),
        path('assets/js', static.serve),

        #test
        path('test/vid/', views.video_capture, name="test_vid"),
        path('capture/stream/id/', views.face_detect_a, name="stream")
    ]