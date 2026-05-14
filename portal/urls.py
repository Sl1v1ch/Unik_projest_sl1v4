from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('schedule/', views.schedule_view, name='schedule'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('tasks/', views.tasks_list_view, name='tasks_list'),
    path('subjects/', views.subjects_list_view, name='subjects_list'),
    path('subjects/<int:pk>/', views.subject_detail_view, name='subject_detail'),
]