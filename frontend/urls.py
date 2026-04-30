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
    path('projects/<int:project_id>/', views.overview, name='overview'),
    path('projects/<int:project_id>/documents/', views.documents, name='documents'),
    path('projects/<int:project_id>/processing/', views.processing, name='processing'),
    path('documents/<int:doc_id>/', views.generated_document, name='generated_document'),
]