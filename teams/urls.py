from django.urls import path

from . import views

urlpatterns = [
    path("", views.team_org, name="team-org"),
    path("<int:pk>/", views.employee_detail, name="employee-detail"),
]
