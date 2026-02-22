from django.contrib import admin
from django.urls import path
from Retirement_Industry import views

urlpatterns = [
    path('', views.index, name = 'index'),
    path('login', views.login, name = 'login'),
    path('profile', views.profile, name = 'profile'),
    path('enter_info', views.enter_info, name = 'enter_info'),
    path('dashboard', views.dashboard, name = 'dashboard'),
    path('expense', views.pay, name = 'pay'),
    path('wallet', views.wallet, name = 'wallet')
]
