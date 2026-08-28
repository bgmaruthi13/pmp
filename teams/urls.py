from django.urls import path

from . import views

urlpatterns = [
    path("", views.team_list, name="team-org"),
    path("efficiency/", views.team_efficiency, name="team-efficiency"),
    path("<int:pk>/edit/", views.employee_edit, name="employee-edit"),
    path("<int:pk>/projects/edit/", views.employee_projects_edit, name="employee-projects-edit"),
    path("<int:pk>/work/", views.employee_work, name="employee-work"),
    path("<int:pk>/work/import/", views.employee_import_upload, name="employee-import-upload"),
    path("<int:pk>/work/import/map/", views.employee_import_map, name="employee-import-map"),
    path("<int:pk>/notes/<str:category>/", views.employee_notes, name="employee-notes"),
    path("<int:pk>/notes/<str:category>/<int:note_id>/edit/", views.employee_note_edit, name="employee-note-edit"),
    path("<int:pk>/notes/<str:category>/<int:note_id>/delete/", views.employee_note_delete, name="employee-note-delete"),
    path("<int:pk>/", views.employee_detail, name="employee-detail"),
]
