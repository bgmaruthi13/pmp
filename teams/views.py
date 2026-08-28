from django.db.models import Count
from django.shortcuts import get_object_or_404, render

from .models import Employee


def team_org(request):
    employees = (
        Employee.objects.select_related("manager")
        .annotate(ticket_count=Count("tickets_received"))
        .order_by("role", "name")
    )
    groups = []
    for role_value, role_label in Employee.Role.choices:
        members = [e for e in employees if e.role == role_value]
        if members:
            groups.append(
                {
                    "label": role_label,
                    "members": members,
                    "total": sum(m.ticket_count for m in members),
                }
            )
    grand_total = sum(g["total"] for g in groups)
    return render(request, "teams/team_org.html", {"groups": groups, "grand_total": grand_total})


def employee_detail(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    tickets = employee.tickets_received.select_related("project").order_by("-created_at")
    return render(request, "teams/employee_detail.html", {"employee": employee, "tickets": tickets})
