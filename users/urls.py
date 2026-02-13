# users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('profile/', views.profile_view, name='profile_view'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
]