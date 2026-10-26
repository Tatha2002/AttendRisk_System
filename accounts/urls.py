from django import views
from django.urls import path
from . import views

urlpatterns = [
    path("register/",views.register_view,name="register"),
    path("login/",views.login_view,name="login"),
    path("refresh-token/",views.refresh_token_view,name="refresh_token"),
    path("dashboard/",views.dashboard,name="dashboard"),
    path("logout/",views.logout_view,name="logout"),

]