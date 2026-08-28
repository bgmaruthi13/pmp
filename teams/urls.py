from django.urls import path

from . import views

urlpatterns = [
    path("", views.team_list, name="team-org"),
    path("<int:pk>/work/analysis/", views.employee_analysis_fragment, name="employee-analysis"),
    path("<int:pk>/work/azure-devops/", views.employee_ado_sync, name="employee-ado-sync"),
    path("<int:pk>/work/import/", views.employee_import_upload, name="employee-import-upload"),
    path("<int:pk>/work/import/map/", views.employee_import_map, name="employee-import-map"),
    path("<int:pk>/", views.employee_detail, name="employee-detail"),
]
