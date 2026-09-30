from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from telemetry import views

urlpatterns = [
    path("", views.device_list, name="devices"),
    path("devices/<str:device_id>/", views.device_detail, name="device"),
    path("login/", auth_views.LoginView.as_view(template_name="telemetry/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("v1/telemetry", views.ingest, name="ingest"),
    path("health/", views.health, name="health"),
    path("admin/", admin.site.urls),
]
