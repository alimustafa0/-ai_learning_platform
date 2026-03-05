# users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('profile/', views.profile_view, name='profile_view'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    
    # Public profile and social URLs
    path('u/<str:username>/', views.public_profile, name='public_profile'),
    path('follow/<int:user_id>/', views.toggle_follow, name='toggle_follow'),
    path('following/', views.following_list, name='following_list'),
    path('followers/', views.followers_list, name='followers_list'),
    path('feed/', views.activity_feed, name='activity_feed'),
]