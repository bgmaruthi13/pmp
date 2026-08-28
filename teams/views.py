import openpyxl
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Employee

MAX_IMPORT_ROWS = 500

IMPORT_FIELDS = [
    {"key": "name", "label": "Name", "required": True},
    {"key": "email", "label": "Email", "required": False},
    {"key": "role", "label": "Role", "required": True},
    {"key": "manager", "label": "Manager (by name)", "required": False},
]


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


@login_required
def team_import_upload(request):
    if request.method == "POST":
        upload = request.FILES.get("file")
        if not upload:
            messages.error(request, "Choose an .xlsx file to upload.")
            return redirect("team-import")

        try:
            workbook = openpyxl.load_workbook(upload, read_only=True, data_only=True)
            worksheet = workbook.active
            rows_iter = worksheet.iter_rows(values_only=True)
            header_row = next(rows_iter)
        except Exception:
            messages.error(request, "Could not read that file. Please upload a valid .xlsx file.")
            return redirect("team-import")

        headers = [str(cell).strip() if cell is not None else "" for cell in header_row]
        data_rows = []
        for row in rows_iter:
            if all(cell is None for cell in row):
                continue
            data_rows.append(["" if cell is None else str(cell).strip() for cell in row])
            if len(data_rows) >= MAX_IMPORT_ROWS:
                break

        if not any(headers) or not data_rows:
            messages.error(request, "That file needs a header row and at least one data row.")
            return redirect("team-import")

        request.session["team_import_headers"] = headers
        request.session["team_import_rows"] = data_rows
        return redirect("team-import-map")

    return render(request, "teams/import_upload.html")


def _guess_column(headers, key):
    for header in headers:
        if key in header.lower():
            return header
    return ""


def _role_lookup():
    lookup = {}
    for value, label in Employee.Role.choices:
        lookup[value.lower()] = value
        lookup[label.lower()] = value
        lookup[value.replace("_", " ").lower()] = value
    return lookup


@login_required
def team_import_map(request):
    headers = request.session.get("team_import_headers")
    rows = request.session.get("team_import_rows")
    if not headers or not rows:
        messages.error(request, "Upload a file first.")
        return redirect("team-import")

    if request.method == "POST":
        mapping = {f["key"]: request.POST.get(f"map_{f['key']}", "") for f in IMPORT_FIELDS}
        missing_required = [f["label"] for f in IMPORT_FIELDS if f["required"] and not mapping[f["key"]]]
        if missing_required:
            messages.error(request, f"Map a column to: {', '.join(missing_required)}.")
            return render(
                request,
                "teams/import_map.html",
                {"headers": headers, "rows": rows[:8], "fields": IMPORT_FIELDS, "mapping": mapping},
            )

        col_index = {header: i for i, header in enumerate(headers)}
        role_lookup = _role_lookup()

        def cell(row, key):
            header = mapping[key]
            idx = col_index.get(header)
            if not header or idx is None or idx >= len(row):
                return ""
            return row[idx]

        created, updated, skipped = 0, 0, 0
        pending_managers = {}
        for row in rows:
            name = cell(row, "name")
            role_raw = cell(row, "role")
            if not name or not role_raw:
                skipped += 1
                continue
            role_value = role_lookup.get(role_raw.strip().lower())
            if not role_value:
                skipped += 1
                continue

            employee, was_created = Employee.objects.update_or_create(
                name=name,
                defaults={"role": role_value, "email": cell(row, "email")},
            )
            created += was_created
            updated += not was_created

            manager_name = cell(row, "manager")
            if manager_name:
                pending_managers[employee.pk] = manager_name

        for employee_pk, manager_name in pending_managers.items():
            manager = Employee.objects.filter(name=manager_name).exclude(pk=employee_pk).first()
            if manager:
                Employee.objects.filter(pk=employee_pk).update(manager=manager)

        del request.session["team_import_headers"]
        del request.session["team_import_rows"]

        summary = f"Imported {created} new and updated {updated} existing team member(s)."
        if skipped:
            summary += f" Skipped {skipped} row(s) missing a required Name/Role value."
        messages.success(request, summary)
        return redirect("team-org")

    mapping = {f["key"]: _guess_column(headers, f["key"]) for f in IMPORT_FIELDS}
    return render(
        request,
        "teams/import_map.html",
        {"headers": headers, "rows": rows[:8], "fields": IMPORT_FIELDS, "mapping": mapping},
    )
