from django.urls import path, include
from django.urls.resolvers import URLPattern
from . import views
from rest_framework import routers


router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('check/auth/', views.query_auth, name="check_auth"),
    path('get/user/document/', views.get_document, name="get_document")    
]