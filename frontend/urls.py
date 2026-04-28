from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('home/', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('projects/', views.projects, name='projects'),
    path('projects/create/', views.create_project, name='create_project'),
    path('search/', views.search, name='search'),
]