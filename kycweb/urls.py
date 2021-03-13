from django.urls import path
from django.views import static
from . import views

urlpatterns = \
    [
        path('home/', views.home, name="home"),
        path('assets/js', static.serve)
    ]