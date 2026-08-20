from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProjectForm, TaskForm
from .models import Project, Task


def project_list(request):
    projects = Project.objects.all()
    return render(request, "projects/project_list.html", {"projects": projects})


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    columns = [
        {"label": status.label, "tasks": project.tasks.filter(status=status.value)}
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
