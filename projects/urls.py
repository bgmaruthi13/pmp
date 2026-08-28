from django.urls import path

from . import views

urlpatterns = [
    path("", views.project_list, name="project-list"),
    path("new/", views.project_create, name="project-create"),
    path("tracker/", views.ticket_tracker, name="ticket-tracker"),
    path("applications/", views.application_list, name="application-list"),
    path("transition/", views.transition_list, name="transition-list"),
    path("<int:pk>/", views.project_detail, name="project-detail"),
    path("<int:project_pk>/tasks/new/", views.task_create, name="task-create"),
    path("tasks/<int:pk>/edit/", views.task_update, name="task-update"),
]
