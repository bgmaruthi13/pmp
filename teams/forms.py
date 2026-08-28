from django import forms

from .models import Employee


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            "name",
            "emp_id",
            "email",
            "designation",
            "manager",
            "line_manager",
            "doj",
            "wfh_exceptions",
            "achievements",
            "escalations",
            "awards",
            "rtb_efficiency",
            "gsc_efficiency",
            "ai_efficiency",
        ]
        widgets = {
            "doj": forms.DateInput(attrs={"type": "date"}),
            "achievements": forms.Textarea(attrs={"rows": 2}),
            "escalations": forms.Textarea(attrs={"rows": 2}),
            "awards": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, employee=None, **kwargs):
        super().__init__(*args, **kwargs)
        if employee is not None:
            self.fields["manager"].queryset = Employee.objects.exclude(pk=employee.pk)
            self.fields["line_manager"].queryset = Employee.objects.exclude(pk=employee.pk)
