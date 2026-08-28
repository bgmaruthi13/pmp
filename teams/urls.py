from django.urls import path

from . import views

urlpatterns = [
    path("", views.team_list, name="team-org"),
    path("<int:pk>/", views.employee_detail, name="employee-detail"),
]
