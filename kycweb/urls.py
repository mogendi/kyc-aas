from django.urls import path
from django.views import static
from . import views

urlpatterns = \
    [
        path('home/', views.home, name="home"),
        path('', views.home, name="home"),
        path('chests/', views.chests, name="chests"),
        path('new_chest/', views.ChestCreateView.as_view(), name="new_chest"),
        path('check/id/', views.check_id, name="checkid"),
        #static
        path('demo/', static.serve),
        path('assets/js', static.serve)
    ]