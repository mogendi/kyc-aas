from os import name
from kycweb.models import BankingChestType
from django.urls import path
from django.views import static
from . import views

urlpatterns = \
    [
        path('home/', views.home, name="home"),
        path('', views.home, name="home"),
        path('chests/', views.chests, name="chests"),
        path('new_chest/', views.ChestCreateView.as_view(), name="new_chest"),
        path('new_chest/bnk/', views.BankingChestCreateView.as_view(), name="new_banking_auth"),
        path('new_chest/wrk/', views.WorkChestCreateView.as_view(), name="new_work_auth"),
        path('delete/chest/<slug:slug>', views.DeleteChest.as_view(), name="delete_chest"),
        path('chests/view/<slug:slug>', views.ChestView.as_view(), name="chest"),
        path('check/id/', views.check_id, name="checkid"),
        path('check/kra/', views.check_kra, name="checkkra"),
        #static
        path('demo/', static.serve),
        path('assets/js', static.serve)
    ]