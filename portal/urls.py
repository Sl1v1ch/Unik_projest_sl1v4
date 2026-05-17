from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('schedule/', views.schedule_view, name='schedule'),

    # Используем твои функции из views.py вместо встроенных
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('profile/', views.profile_view, name='profile'),
    path('tasks/', views.tasks_list_view, name='tasks_list'),
    path('subjects/', views.subjects_list_view, name='subjects_list'),
    path('subjects/<int:pk>/', views.subject_detail_view, name='subject_detail'),
    path('dashboard/', views.teacher_dashboard_view, name='teacher_dashboard'),
    path('admission/', views.admission_view, name='admission'),
    path('career/', views.career_view, name='career'),
    path('college/', views.college_view, name='college'),
    path('support/', views.support_view, name='support'),
    path('news/<int:pk>/', views.news_detail_view, name='news_detail'),
]
