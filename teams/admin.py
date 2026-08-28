import re

import openpyxl
from django import forms
from django.contrib import admin, messages
from django.db.models import Max
from django.shortcuts import redirect, render
from django.urls import path

from .models import AzureDevOpsSettings, Employee, Role, SupportTicket, WorkItem

MAX_IMPORT_ROWS = 500

IMPORT_FIELDS = [
    {"key": "name", "label": "Name", "required": True},
    {"key": "email", "label": "Email", "required": False},
    {"key": "roles", "label": "Roles (comma-separated)", "required": True},
    {"key": "manager", "label": "Manager (by name)", "required": False},
]


def _guess_column(headers, key):
    candidates = {key, key.rstrip("s")}
    for header in headers:
        h = header.lower()
        if any(c in h for c in candidates):
            return header
    return ""


def _resolve_roles(roles_raw):
    """Split a comma/slash/semicolon-separated cell into Role objects, creating any new ones."""
    names = [r.strip() for r in re.split(r"[,;/]", roles_raw) if r.strip()]
    roles = []
    for name in names:
        role = Role.objects.filter(name__iexact=name).first()
        if not role:
            next_order = (Role.objects.aggregate(Max("order"))["order__max"] or 0) + 1
            role = Role.objects.create(name=name, order=next_order)
        roles.append(role)
    return roles


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "employee_count")
    ordering = ("order", "name")

    @admin.display(description="Employees")
    def employee_count(self, obj):
        return obj.employees.count()


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("name", "roles_list", "manager", "email")
    list_filter = ("roles",)
    search_fields = ("name", "email")
    filter_horizontal = ("roles",)
    change_list_template = "admin/teams/employee/change_list.html"

    @admin.display(description="Roles")
    def roles_list(self, obj):
        return obj.roles_display() or "—"

    def get_urls(self):
        custom = [
            path("import/", self.admin_site.admin_view(self.import_view), name="teams_employee_import"),
            path(
                "import/map/",
                self.admin_site.admin_view(self.import_map_view),
                name="teams_employee_import_map",
            ),
        ]
        return custom + super().get_urls()

    def _admin_context(self, request, **extra):
        return {**self.admin_site.each_context(request), "opts": self.model._meta, **extra}

    def import_view(self, request):
        if request.method == "POST":
            upload = request.FILES.get("file")
            if not upload:
                messages.error(request, "Choose an .xlsx file to upload.")
                return redirect("admin:teams_employee_import")

            try:
                workbook = openpyxl.load_workbook(upload, read_only=True, data_only=True)
                worksheet = workbook.active
                rows_iter = worksheet.iter_rows(values_only=True)
                header_row = next(rows_iter)
            except Exception:
                messages.error(request, "Could not read that file. Please upload a valid .xlsx file.")
                return redirect("admin:teams_employee_import")

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
                return redirect("admin:teams_employee_import")

            request.session["team_import_headers"] = headers
            request.session["team_import_rows"] = data_rows
            return redirect("admin:teams_employee_import_map")

        context = self._admin_context(request, title="Import Team from Excel")
        return render(request, "admin/teams/employee/import_upload.html", context)

    def import_map_view(self, request):
        headers = request.session.get("team_import_headers")
        rows = request.session.get("team_import_rows")
        if not headers or not rows:
            messages.error(request, "Upload a file first.")
            return redirect("admin:teams_employee_import")

        if request.method == "POST":
            mapping = {f["key"]: request.POST.get(f"map_{f['key']}", "") for f in IMPORT_FIELDS}
            missing_required = [f["label"] for f in IMPORT_FIELDS if f["required"] and not mapping[f["key"]]]
            if missing_required:
                messages.error(request, f"Map a column to: {', '.join(missing_required)}.")
                context = self._admin_context(
                    request,
                    title="Map Columns",
                    headers=headers,
                    rows=rows[:8],
                    fields=IMPORT_FIELDS,
                    mapping=mapping,
                )
                return render(request, "admin/teams/employee/import_map.html", context)

            col_index = {header: i for i, header in enumerate(headers)}

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
                roles_raw = cell(row, "roles")
                if not name or not roles_raw:
                    skipped += 1
                    continue
                role_objs = _resolve_roles(roles_raw)
                if not role_objs:
                    skipped += 1
                    continue

                employee, was_created = Employee.objects.update_or_create(
                    name=name,
                    defaults={"email": cell(row, "email")},
                )
                created += was_created
                updated += not was_created
                employee.roles.set(role_objs)

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
                summary += f" Skipped {skipped} row(s) missing a required Name/Roles value."
            messages.success(request, summary)
            return redirect("admin:teams_employee_changelist")

        mapping = {f["key"]: _guess_column(headers, f["key"]) for f in IMPORT_FIELDS}
        context = self._admin_context(
            request,
            title="Map Columns",
            headers=headers,
            rows=rows[:8],
            fields=IMPORT_FIELDS,
            mapping=mapping,
        )
        return render(request, "admin/teams/employee/import_map.html", context)


@admin.register(AzureDevOpsSettings)
class AzureDevOpsSettingsAdmin(admin.ModelAdmin):
    list_display = ("organization_url", "has_token")

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "personal_access_token":
            kwargs["widget"] = forms.PasswordInput(render_value=True)
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    @admin.display(description="PAT configured", boolean=True)
    def has_token(self, obj):
        return bool(obj.personal_access_token)

    def has_add_permission(self, request):
        return not AzureDevOpsSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = AzureDevOpsSettings.load()
        return redirect("admin:teams_azuredevopssettings_change", obj.pk)


@admin.register(WorkItem)
class WorkItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "employee",
        "assigned_to_raw",
        "source",
        "work_item_type",
        "state",
        "priority",
        "story_points",
        "closed_date",
    )
    list_filter = ("source", "work_item_type", "state", "priority")
    search_fields = ("title", "external_id", "employee__name", "assigned_to_raw", "tags")
    autocomplete_fields = ("employee",)


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "employee",
        "assigned_to_raw",
        "source",
        "work_item_type",
        "state",
        "priority",
        "closed_date",
        "related_work_item",
    )
    list_filter = ("source", "work_item_type", "state", "priority")
    search_fields = ("title", "external_id", "employee__name", "assigned_to_raw", "tags")
    autocomplete_fields = ("employee", "related_work_item")
