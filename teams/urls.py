from django.urls import path

from . import views

urlpatterns = [
    path("", views.team_list, name="team-org"),
    path("import/", views.team_import_upload, name="team-import"),
    path("import/map/", views.team_import_map, name="team-import-map"),
    path("<int:pk>/", views.employee_detail, name="employee-detail"),
]
