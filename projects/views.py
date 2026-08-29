from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProjectForm, TaskForm
from .models import (
    Application,
    Project,
    Task,
    TransitionDocument,
    TransitionDocumentAttachment,
    TransitionSystem,
)


def project_list(request):
    projects = Project.objects.select_related("lead").annotate(
        todo_count=Count("tasks", filter=Q(tasks__status=Task.Status.TODO), distinct=True),
        in_progress_count=Count("tasks", filter=Q(tasks__status=Task.Status.IN_PROGRESS), distinct=True),
        done_count=Count("tasks", filter=Q(tasks__status=Task.Status.DONE), distinct=True),
        ticket_count=Count("tasks", distinct=True),
    )
    return render(request, "projects/project_list.html", {"projects": projects})


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
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
    applications = Application.objects.all()
    return render(request, "projects/application_list.html", {"applications": applications})


def application_detail(request, pk):
    application = get_object_or_404(Application, pk=pk)
    return render(request, "projects/application_detail.html", {"application": application})


def transition_list(request):
    documents = TransitionDocument.objects.prefetch_related("systems", "attachments")
    systems = TransitionSystem.objects.all()
    return render(
        request,
        "projects/transition_list.html",
        {
            "documents": documents,
            "systems": systems,
            "collected_count": sum(1 for d in documents if d.available),
        },
    )


def transition_detail(request, pk):
    document = get_object_or_404(
        TransitionDocument.objects.prefetch_related("systems", "attachments"), pk=pk
    )
    return render(request, "projects/transition_detail.html", {"document": document})


def _sync_transition_available(document):
    has_files = document.attachments.exists()
    if document.available != has_files:
        document.available = has_files
        document.save(update_fields=["available"])


def transition_document_attachments(request, pk):
    # Deliberately not prefetching "attachments" here (unlike transition_detail/
    # transition_list) — this view creates new attachments and then immediately
    # re-checks document.attachments in the same request, so a prefetch cache
    # populated before the create() would go stale and hide the new file.
    document = get_object_or_404(TransitionDocument, pk=pk)
    in_modal = bool(request.GET.get("modal"))

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        for uploaded_file in request.FILES.getlist("file"):
            TransitionDocumentAttachment.objects.create(document=document, file=uploaded_file)
        _sync_transition_available(document)
        if in_modal:
            return render(
                request, "projects/_transition_attachments.html", {"document": document, "in_modal": True}
            )
        return redirect("transition-detail", pk=pk)

    return render(
        request, "projects/_transition_attachments.html", {"document": document, "in_modal": in_modal}
    )


def transition_document_attachment_delete(request, pk, attachment_id):
    document = get_object_or_404(TransitionDocument, pk=pk)
    attachment = get_object_or_404(TransitionDocumentAttachment, pk=attachment_id, document=document)
    in_modal = bool(request.GET.get("modal"))

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        attachment.file.delete(save=False)
        attachment.delete()
        _sync_transition_available(document)
        if in_modal:
            return render(
                request, "projects/_transition_attachments.html", {"document": document, "in_modal": True}
            )
        return redirect("transition-detail", pk=pk)

    return redirect("transition-detail", pk=pk)
