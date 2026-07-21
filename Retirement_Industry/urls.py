from django.urls import path
from Retirement_Industry import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path('enter_info', views.enter_info, name='enter_info'),
    path('load_sample', views.load_sample, name='load_sample'),
    path('dashboard', views.dashboard, name='dashboard'),
    path('expenses', views.expenses, name='expenses'),
    path('intelligence', views.intelligence, name='intelligence'),
    path('personality', views.personality, name='personality'),
    path('goals', views.goals, name='goals'),
    path('challenges', views.challenges, name='challenges'),
    path('portfolio', views.portfolio, name='portfolio'),
    path('coach', views.coach, name='coach'),
    path('profile', views.profile, name='profile'),
]
