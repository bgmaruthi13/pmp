from django.shortcuts import get_object_or_404, render

from .models import Employee


def team_list(request):
    employees = (
        Employee.objects.select_related("manager")
        .prefetch_related("tickets_received__project", "projects_led")
        .order_by("role", "name")
    )
    rows = []
    for employee in employees:
        tickets = list(employee.tickets_received.all())
        projects = {t.project.name for t in tickets}
        projects.update(p.name for p in employee.projects_led.all())
        rows.append(
            {
                "employee": employee,
                "projects": sorted(projects),
                "ticket_count": len(tickets),
            }
        )
    return render(request, "teams/team_list.html", {"rows": rows})


def employee_detail(request, pk):
    employee = get_object_or_404(
        Employee.objects.select_related("manager").prefetch_related("reports", "projects_led"),
        pk=pk,
    )
    tickets = employee.tickets_received.select_related("project").order_by("-created_at")
    projects = {t.project for t in tickets}
    projects.update(employee.projects_led.all())
    return render(
        request,
        "teams/employee_detail.html",
        {"employee": employee, "tickets": tickets, "projects": sorted(projects, key=lambda p: p.name)},
    )
