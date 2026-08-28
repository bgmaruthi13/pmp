from django.urls import path

from . import views

urlpatterns = [
    path("", views.team_list, name="team-org"),
    path("headcount/", views.team_headcount, name="team-headcount"),
    path("efficiency/", views.team_efficiency, name="team-efficiency"),
    path("analysis/", views.analysis_home, name="team-analysis"),
    path("analysis/export/", views.analysis_export, name="analysis-export"),
    path("analysis/import/", views.analysis_import_upload, name="analysis-import-upload"),
    path("analysis/import/map/", views.analysis_import_map, name="analysis-import-map"),
    path("support/", views.support_analysis_home, name="support-analysis"),
    path("support/export/", views.support_export, name="support-export"),
    path("support/import/", views.support_import_upload, name="support-import-upload"),
    path("support/import/map/", views.support_import_map, name="support-import-map"),
    path("settings/", views.admin_settings, name="admin-settings"),
    path("<int:pk>/edit/", views.employee_edit, name="employee-edit"),
    path("<int:pk>/projects/edit/", views.employee_projects_edit, name="employee-projects-edit"),
    path("<int:pk>/work/", views.employee_work, name="employee-work"),
    path("<int:pk>/work/import/", views.employee_import_upload, name="employee-import-upload"),
    path("<int:pk>/work/import/map/", views.employee_import_map, name="employee-import-map"),
    path("<int:pk>/notes/<str:category>/", views.employee_notes, name="employee-notes"),
    path("<int:pk>/notes/<str:category>/<int:note_id>/edit/", views.employee_note_edit, name="employee-note-edit"),
    path("<int:pk>/notes/<str:category>/<int:note_id>/delete/", views.employee_note_delete, name="employee-note-delete"),
    path(
        "<int:pk>/notes/<str:category>/<int:note_id>/attachments/",
        views.employee_note_attachment_add,
        name="employee-note-attachment-add",
    ),
    path(
        "<int:pk>/notes/<str:category>/<int:note_id>/attachments/<int:attachment_id>/delete/",
        views.employee_note_attachment_delete,
        name="employee-note-attachment-delete",
    ),
    path("<int:pk>/", views.employee_detail, name="employee-detail"),
]
