from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import ProjectForm, TaskForm
from .models import (
    Application,
    DocumentActivity,
    DocumentVersion,
    Project,
    Task,
    TransitionDocument,
    TransitionSystem,
)


def project_list(request):
    projects = Project.objects.select_related("lead", "application").annotate(
        todo_count=Count("tasks", filter=Q(tasks__status=Task.Status.TODO), distinct=True),
        in_progress_count=Count("tasks", filter=Q(tasks__status=Task.Status.IN_PROGRESS), distinct=True),
        done_count=Count("tasks", filter=Q(tasks__status=Task.Status.DONE), distinct=True),
        ticket_count=Count("tasks", distinct=True),
    )
    return render(request, "projects/project_list.html", {"projects": projects})


def project_detail(request, pk):
    project = get_object_or_404(Project.objects.select_related("application"), pk=pk)
    columns = [
        {"label": status.label, "tasks": project.tasks.filter(status=status.value).select_related("assignee")}
        for status in Task.Status
    ]
    return render(request, "projects/project_detail.html", {"project": project, "columns": columns})


@login_required
def project_create(request):
    form = ProjectForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        project = form.save()
        return redirect(project)
    return render(request, "projects/project_form.html", {"form": form})


@login_required
def task_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    form = TaskForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        task = form.save(commit=False)
        task.project = project
        task.save()
        return redirect(project)
    return render(request, "projects/task_form.html", {"form": form, "project": project})


@login_required
def task_update(request, pk):
    task = get_object_or_404(Task, pk=pk)
    form = TaskForm(request.POST or None, instance=task)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect(task.project)
    return render(request, "projects/task_form.html", {"form": form, "project": task.project})


def ticket_tracker(request):
    tickets = Task.objects.select_related("project", "area", "assignee", "assigned_by")
    ticket_type = request.GET.get("type")
    if ticket_type in {Task.TicketType.PLANNED, Task.TicketType.ADHOC}:
        tickets = tickets.filter(ticket_type=ticket_type)
    return render(
        request,
        "projects/ticket_tracker.html",
        {"tickets": tickets, "active_type": ticket_type or "all"},
    )


def ticket_detail(request, pk):
    ticket = get_object_or_404(
        Task.objects.select_related("project", "area", "assignee", "assigned_by"), pk=pk
    )
    return render(request, "projects/ticket_detail.html", {"ticket": ticket})


def application_list(request):
    applications = Application.objects.prefetch_related("projects")
    return render(request, "projects/application_list.html", {"applications": applications})


def application_detail(request, pk):
    application = get_object_or_404(Application, pk=pk)
    context = {"application": application}
    context.update(_document_versions_context(application))
    return render(request, "projects/application_detail.html", context)


def transition_list(request):
    documents = TransitionDocument.objects.select_related("project", "template").prefetch_related(
        "template__systems", "versions"
    )
    selected_project = None
    project_id = request.GET.get("project")
    if project_id:
        selected_project = get_object_or_404(Project, pk=project_id)
        documents = documents.filter(project=selected_project)
    systems = TransitionSystem.objects.all()
    return render(
        request,
        "projects/transition_list.html",
        {
            "documents": documents,
            "systems": systems,
            "collected_count": sum(1 for d in documents if d.available),
            "selected_project": selected_project,
        },
    )


def transition_detail(request, pk):
    document = get_object_or_404(
        TransitionDocument.objects.select_related("template").prefetch_related("template__systems"), pk=pk
    )
    context = {"document": document}
    context.update(_document_versions_context(document))
    return render(request, "projects/transition_detail.html", context)


# -- Shared document-version upload/history, usable against either a
# TransitionDocument or an Application via Django's content-type framework, so
# both kinds of documents share one upload mechanism and one version history
# instead of maintaining two separate attachment systems. --

_VERSION_URL_NAMES = {
    TransitionDocument: ("transition-document-versions", "transition-document-version-delete"),
    Application: ("application-document-versions", "application-document-version-delete"),
}


def _document_versions_context(parent, in_modal=False):
    upload_url_name, delete_url_name = _VERSION_URL_NAMES[type(parent)]
    if isinstance(parent, TransitionDocument):
        parent_title = parent.document
        parent_subtitle = parent.category
    else:
        parent_title = parent.name
        parent_subtitle = parent.domain or parent.architecture_container

    version_rows = [
        {"version": v, "delete_url": reverse(delete_url_name, args=[parent.pk, v.pk])}
        for v in parent.versions.order_by("-version")
    ]
    return {
        "parent_title": parent_title,
        "parent_subtitle": parent_subtitle,
        "version_rows": version_rows,
        "activities": DocumentActivity.choices,
        "in_modal": in_modal,
        "upload_action": reverse(upload_url_name, args=[parent.pk]),
    }


def _sync_available(parent):
    """TransitionDocument tracks a simple "collected" flag alongside its version
    history; Application doesn't have that field, so this is a no-op for it."""
    if hasattr(parent, "available"):
        has_versions = parent.versions.exists()
        if parent.available != has_versions:
            parent.available = has_versions
            parent.save(update_fields=["available"])


def _handle_document_versions_upload(request, parent, detail_url_name):
    # Deliberately re-fetched without prefetching "versions" by the caller —
    # this view creates new versions and then immediately re-checks
    # parent.versions in the same request, so a prefetch cache populated
    # before the create() would go stale and hide the new file.
    in_modal = bool(request.GET.get("modal"))

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        activity = request.POST.get("activity") or DocumentActivity.values[0]
        content_type = ContentType.objects.get_for_model(type(parent))
        for uploaded_file in request.FILES.getlist("file"):
            DocumentVersion.objects.create(
                content_type=content_type, object_id=parent.pk, activity=activity, file=uploaded_file
            )
        _sync_available(parent)
        if in_modal:
            return render(
                request, "projects/_document_versions.html", _document_versions_context(parent, in_modal=True)
            )
        return redirect(detail_url_name, pk=parent.pk)

    return render(
        request, "projects/_document_versions.html", _document_versions_context(parent, in_modal=in_modal)
    )


def _handle_document_version_delete(request, parent, version, detail_url_name):
    in_modal = bool(request.GET.get("modal"))

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        version.file.delete(save=False)
        version.delete()
        _sync_available(parent)
        if in_modal:
            return render(
                request, "projects/_document_versions.html", _document_versions_context(parent, in_modal=True)
            )
        return redirect(detail_url_name, pk=parent.pk)

    return redirect(detail_url_name, pk=parent.pk)


def transition_document_versions(request, pk):
    document = get_object_or_404(TransitionDocument, pk=pk)
    return _handle_document_versions_upload(request, document, "transition-detail")


def transition_document_version_delete(request, pk, version_id):
    document = get_object_or_404(TransitionDocument, pk=pk)
    version = get_object_or_404(
        DocumentVersion,
        pk=version_id,
        content_type=ContentType.objects.get_for_model(TransitionDocument),
        object_id=pk,
    )
    return _handle_document_version_delete(request, document, version, "transition-detail")


def application_document_versions(request, pk):
    application = get_object_or_404(Application, pk=pk)
    return _handle_document_versions_upload(request, application, "application-detail")


def application_document_version_delete(request, pk, version_id):
    application = get_object_or_404(Application, pk=pk)
    version = get_object_or_404(
        DocumentVersion,
        pk=version_id,
        content_type=ContentType.objects.get_for_model(Application),
        object_id=pk,
    )
    return _handle_document_version_delete(request, application, version, "application-detail")
