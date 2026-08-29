from django.urls import path

from . import views

urlpatterns = [
    path("", views.project_list, name="project-list"),
    path("new/", views.project_create, name="project-create"),
    path("tracker/", views.ticket_tracker, name="ticket-tracker"),
    path("tickets/<int:pk>/", views.ticket_detail, name="ticket-detail"),
    path("applications/", views.application_list, name="application-list"),
    path("applications/<int:pk>/", views.application_detail, name="application-detail"),
    path(
        "applications/<int:pk>/versions/",
        views.application_document_versions,
        name="application-document-versions",
    ),
    path(
        "applications/<int:pk>/versions/<int:version_id>/delete/",
        views.application_document_version_delete,
        name="application-document-version-delete",
    ),
    path("transition/", views.transition_list, name="transition-list"),
    path("transition/templates/new/", views.transition_template_create, name="transition-template-create"),
    path(
        "transition/templates/<int:pk>/edit/",
        views.transition_template_edit,
        name="transition-template-edit",
    ),
    path(
        "transition/templates/<int:pk>/archive/",
        views.transition_template_archive,
        name="transition-template-archive",
    ),
    path("transition/<int:pk>/", views.transition_detail, name="transition-detail"),
    path(
        "transition/<int:pk>/versions/",
        views.transition_document_versions,
        name="transition-document-versions",
    ),
    path(
        "transition/<int:pk>/versions/<int:version_id>/delete/",
        views.transition_document_version_delete,
        name="transition-document-version-delete",
    ),
    path("<int:pk>/", views.project_detail, name="project-detail"),
    path("<int:project_pk>/tasks/new/", views.task_create, name="task-create"),
    path("tasks/<int:pk>/edit/", views.task_update, name="task-update"),
]
