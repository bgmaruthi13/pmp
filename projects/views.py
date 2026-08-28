from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProjectForm, TaskForm
from .models import Application, Project, Task, TransitionDocument, TransitionSystem


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
    documents = TransitionDocument.objects.prefetch_related("systems")
    systems = TransitionSystem.objects.all()
    return render(
        request,
        "projects/transition_list.html",
        {"documents": documents, "systems": systems},
    )


def transition_detail(request, pk):
    document = get_object_or_404(TransitionDocument.objects.prefetch_related("systems"), pk=pk)
    return render(request, "projects/transition_detail.html", {"document": document})
