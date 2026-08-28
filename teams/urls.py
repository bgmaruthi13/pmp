from django.urls import path

from . import views

urlpatterns = [
    path("", views.team_list, name="team-org"),
    path("<int:pk>/projects/edit/", views.employee_projects_edit, name="employee-projects-edit"),
    path("<int:pk>/work/", views.employee_work, name="employee-work"),
    path("<int:pk>/work/import/", views.employee_import_upload, name="employee-import-upload"),
    path("<int:pk>/work/import/map/", views.employee_import_map, name="employee-import-map"),
    path("<int:pk>/", views.employee_detail, name="employee-detail"),
]
