from django import forms

from .models import Project, Task


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name", "description", "lead"]


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            "title",
            "description",
            "area",
            "ticket_type",
            "status",
            "assigned_by",
            "assignee",
            "due_date",
            "sdm_attention",
            "remarks",
        ]
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"})}
