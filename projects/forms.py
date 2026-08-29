from django import forms

from .models import Project, Task, TransitionDocumentTemplate


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name", "description", "lead", "application"]


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


class TransitionDocumentTemplateForm(forms.ModelForm):
    class Meta:
        model = TransitionDocumentTemplate
        fields = ["category", "document", "purpose", "owner", "systems", "order"]
        widgets = {
            "purpose": forms.Textarea(attrs={"rows": 3}),
            "systems": forms.CheckboxSelectMultiple(),
        }
