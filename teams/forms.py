from django import forms

from .models import Employee, EmployeeNote


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            "name",
            "emp_id",
            "email",
            "designation",
            "country",
            "manager",
            "line_manager",
            "doj",
            "awards",
            "rtb_efficiency",
            "gsc_efficiency",
            "ai_efficiency",
        ]
        widgets = {
            "doj": forms.DateInput(attrs={"type": "date"}),
            "awards": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, employee=None, **kwargs):
        super().__init__(*args, **kwargs)
        if employee is not None:
            self.fields["manager"].queryset = Employee.objects.exclude(pk=employee.pk)
            self.fields["line_manager"].queryset = Employee.objects.exclude(pk=employee.pk)


class EmployeeNoteForm(forms.ModelForm):
    class Meta:
        model = EmployeeNote
        fields = ["date", "description", "work_item_ref"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 2}),
            "work_item_ref": forms.TextInput(attrs={"placeholder": "e.g. US-4231 or a link to the ticket"}),
        }
