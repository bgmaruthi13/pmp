import csv
import io
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

import openpyxl
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from projects.models import Project

from .azure_devops import AzureDevOpsError, fetch_work_items
from .forms import EmployeeForm, EmployeeNoteForm
from .models import AzureDevOpsSettings, Employee, EmployeeNote, EmployeeNoteAttachment, WorkItem
from .sync import import_team_work_items, run_team_ado_sync

NOTE_CATEGORY_LABELS = dict(EmployeeNote.Category.choices)


def _clean_ado_item(item):
    """Pop the assignment-matching keys out of a fetch_work_items() dict, leaving only
    valid WorkItem field values (with assigned_to_raw filled in for traceability)."""
    item = dict(item)
    name = item.pop("assigned_to_name", "")
    email = item.pop("assigned_to_email", "")
    item["assigned_to_raw"] = name or email
    return item

MAX_WORK_IMPORT_ROWS = 1000

WORK_IMPORT_FIELDS = [
    {"key": "title", "label": "Title", "required": True},
    {"key": "work_item_type", "label": "Type", "required": False},
    {"key": "state", "label": "State", "required": False},
    {"key": "story_points", "label": "Story Points", "required": False},
    {"key": "area_path", "label": "Area Path", "required": False},
    {"key": "iteration_path", "label": "Iteration Path", "required": False},
    {"key": "created_date", "label": "Created Date", "required": False},
    {"key": "closed_date", "label": "Closed Date", "required": False},
    {"key": "external_id", "label": "External ID", "required": False},
    {"key": "url", "label": "URL", "required": False},
]

ANALYSIS_IMPORT_FIELDS = WORK_IMPORT_FIELDS + [
    {"key": "assignee", "label": "Assignee (name or email)", "required": True},
]


def team_list(request):
    employees = (
        Employee.objects.select_related("manager", "line_manager")
        .prefetch_related("tickets_received", "roles", "projects", "notes")
        .order_by("name")
    )
    rows = []
    for employee in employees:
        notes = list(employee.notes.all())
        rows.append(
            {
                "employee": employee,
                "projects": sorted(employee.projects.all(), key=lambda p: p.name),
                "ticket_count": len(employee.tickets_received.all()),
                "wfh_count": sum(1 for n in notes if n.category == EmployeeNote.Category.WFH_EXCEPTION),
                "achievement_count": sum(1 for n in notes if n.category == EmployeeNote.Category.ACHIEVEMENT),
                "escalation_count": sum(1 for n in notes if n.category == EmployeeNote.Category.ESCALATION),
            }
        )
    return render(request, "teams/team_list.html", {"rows": rows})


def _blended_efficiency(employee):
    values = [v for v in [employee.rtb_efficiency, employee.gsc_efficiency, employee.ai_efficiency] if v is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def team_efficiency(request):
    employees = Employee.objects.select_related("manager", "line_manager").prefetch_related("work_items")

    groups = {}
    for employee in employees:
        lead = employee.line_manager or employee.manager
        key = lead.pk if lead else 0
        group = groups.setdefault(key, {"manager": lead, "members": []})
        group["members"].append(employee)

    result_groups = []
    for group in groups.values():
        members = sorted(group["members"], key=lambda e: e.name)
        rows = []
        for employee in members:
            items = list(employee.work_items.all())
            rows.append(
                {
                    "employee": employee,
                    "item_count": len(items),
                    "points": sum((i.story_points or 0) for i in items),
                }
            )
        manager = group["manager"]
        result_groups.append(
            {
                "manager": manager,
                "manager_blended": _blended_efficiency(manager) if manager else None,
                "rows": rows,
                "team_size": len(members),
            }
        )

    result_groups.sort(key=lambda g: (g["manager"] is None, g["manager"].name if g["manager"] else ""))
    return render(request, "teams/efficiency.html", {"groups": result_groups})


@login_required
def employee_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == "POST":
        form = EmployeeForm(request.POST, instance=employee, employee=employee)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated {employee.name}.")
            return redirect("team-org")
    else:
        form = EmployeeForm(instance=employee, employee=employee)
    return render(request, "teams/employee_edit_modal.html", {"employee": employee, "form": form})


def employee_detail(request, pk):
    employee = get_object_or_404(
        Employee.objects.select_related("manager").prefetch_related("reports", "roles", "projects"),
        pk=pk,
    )
    tickets = employee.tickets_received.select_related("project").order_by("-created_at")
    return render(
        request,
        "teams/employee_detail.html",
        {"employee": employee, "tickets": tickets, "projects": employee.projects.all()},
    )


@login_required
def employee_projects_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    all_projects = Project.objects.order_by("name")

    if request.method == "POST":
        selected_ids = request.POST.getlist("projects")
        employee.projects.set(all_projects.filter(pk__in=selected_ids))
        messages.success(request, f"Updated projects for {employee.name}.")
        return redirect("team-org")

    current_ids = set(employee.projects.values_list("pk", flat=True))
    return render(
        request,
        "teams/projects_edit.html",
        {"employee": employee, "all_projects": all_projects, "current_ids": current_ids},
    )


def _analysis_for(employee, items):
    monthly_counts = Counter()
    for item in items:
        d = item.closed_date or item.created_date
        if d:
            monthly_counts[d.strftime("%Y-%m")] += 1
    max_count = max(monthly_counts.values(), default=0)
    monthly_series = [
        {"month": month, "count": count, "pct": round(count / max_count * 100) if max_count else 0}
        for month, count in sorted(monthly_counts.items())
    ]

    type_counts = Counter(i.work_item_type or "Unspecified" for i in items).most_common()
    state_counts = Counter(i.state or "Unspecified" for i in items).most_common()
    total_points = sum((i.story_points or 0) for i in items)

    return {
        "items": items[:50],
        "total_items": len(items),
        "monthly_series": monthly_series,
        "type_counts": type_counts,
        "state_counts": state_counts,
        "total_points": total_points,
        "prompt": _build_analysis_prompt(employee, items, monthly_series, type_counts, total_points),
    }


def _build_analysis_prompt(employee, items, monthly_series, type_counts, total_points):
    if not items:
        return (
            f"No work items are on file yet for {employee.name}. Sync from Azure DevOps or import "
            "an Excel/CSV file for this person, then reopen this analysis."
        )

    dated = [i.closed_date or i.created_date for i in items if (i.closed_date or i.created_date)]
    span = f" from {min(dated):%b %Y} to {max(dated):%b %Y}" if dated else ""
    type_lines = "\n".join(f"- {t}: {c}" for t, c in type_counts)
    monthly_lines = "\n".join(f"- {m['month']}: {m['count']} item(s)" for m in monthly_series)
    sample_titles = "\n".join(f"- [{i.work_item_type or 'Item'}] {i.title}" for i in items[:25])

    roles = employee.roles_display() or "role unspecified"
    return (
        f"Analyze {employee.name}'s ({roles}) delivery history{span}, "
        f"based on {len(items)} tracked work item(s) totalling {total_points or 0} story points.\n\n"
        f"Work item types:\n{type_lines}\n\n"
        f"Monthly delivery:\n{monthly_lines}\n\n"
        f"Sample tickets:\n{sample_titles}\n\n"
        "Please summarize: (1) the kinds of tickets/user stories this person typically works on, "
        "(2) an effort analysis (volume and story points per month, and any trend), and "
        "(3) an overall narrative summary of this developer's contribution since the start of the project."
    )


def employee_work(request, pk):
    employee = get_object_or_404(Employee.objects.prefetch_related("roles"), pk=pk)
    settings_obj = AzureDevOpsSettings.load()
    ado_error = None

    default_source = (
        "azure_devops" if (settings_obj.personal_access_token and employee.azure_devops_query_url) else "excel"
    )
    source = request.GET.get("source") or default_source
    if source not in ("azure_devops", "excel"):
        source = default_source

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        if request.POST.get("action") == "ado_sync":
            source = "azure_devops"
            query_url = request.POST.get("query_url", "").strip()
            employee.azure_devops_query_url = query_url
            employee.save(update_fields=["azure_devops_query_url"])

            if not query_url:
                ado_error = "Add a query URL first."
            elif not settings_obj.personal_access_token:
                ado_error = "No shared PAT is configured. Ask an admin to set one under Admin > Teams > Azure DevOps settings."
            else:
                try:
                    fetched = fetch_work_items(query_url, settings_obj.personal_access_token)
                except AzureDevOpsError as exc:
                    ado_error = str(exc)
                else:
                    employee.work_items.filter(source=WorkItem.Source.AZURE_DEVOPS).delete()
                    WorkItem.objects.bulk_create(
                        WorkItem(employee=employee, source=WorkItem.Source.AZURE_DEVOPS, **_clean_ado_item(item))
                        for item in fetched
                    )
                    messages.success(request, f"Synced {len(fetched)} work item(s) from Azure DevOps.")
                    return redirect(f"{reverse('employee-work', args=[pk])}?source=azure_devops")

    source_value = WorkItem.Source.AZURE_DEVOPS if source == "azure_devops" else WorkItem.Source.EXCEL
    items = list(employee.work_items.filter(source=source_value))

    context = {
        "employee": employee,
        "source": source,
        "ado_error": ado_error,
        "pat_configured": bool(settings_obj.personal_access_token),
        **_analysis_for(employee, items),
    }
    return render(request, "teams/work.html", context)


def _read_tabular_file(upload):
    name = (upload.name or "").lower()
    if name.endswith(".csv"):
        text = io.TextIOWrapper(upload.file, encoding="utf-8-sig", errors="replace")
        rows = [row for row in csv.reader(text)]
        if not rows:
            raise ValueError("That CSV file is empty.")
        headers = [cell.strip() for cell in rows[0]]
        data_rows = [[cell.strip() for cell in row] for row in rows[1:] if any(cell.strip() for cell in row)]
        return headers, data_rows

    try:
        workbook = openpyxl.load_workbook(upload, read_only=True, data_only=True)
        worksheet = workbook.active
        rows_iter = worksheet.iter_rows(values_only=True)
        header_row = next(rows_iter)
    except Exception as exc:
        raise ValueError("Could not read that file. Please upload a valid .xlsx or .csv file.") from exc

    headers = [str(cell).strip() if cell is not None else "" for cell in header_row]
    data_rows = []
    for row in rows_iter:
        if all(cell is None for cell in row):
            continue
        data_rows.append(["" if cell is None else str(cell).strip() for cell in row])
    return headers, data_rows


def _guess_work_column(headers, key):
    key_variants = {key.lower(), key.replace("_", " ").lower()}
    for header in headers:
        h = header.lower()
        if any(variant in h for variant in key_variants):
            return header
    return ""


@login_required
def employee_import_upload(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == "POST":
        upload = request.FILES.get("file")
        if not upload:
            messages.error(request, "Choose an .xlsx or .csv file to upload.")
            return redirect("employee-import-upload", pk=pk)

        try:
            headers, data_rows = _read_tabular_file(upload)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("employee-import-upload", pk=pk)

        if not any(headers) or not data_rows:
            messages.error(request, "That file needs a header row and at least one data row.")
            return redirect("employee-import-upload", pk=pk)

        request.session["work_import_headers"] = headers
        request.session["work_import_rows"] = data_rows[:MAX_WORK_IMPORT_ROWS]
        return redirect("employee-import-map", pk=pk)

    return render(request, "teams/work_import_upload.html", {"employee": employee})


def _parse_work_date(value):
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_story_points(value):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


@login_required
def employee_import_map(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    headers = request.session.get("work_import_headers")
    rows = request.session.get("work_import_rows")
    if not headers or not rows:
        messages.error(request, "Upload a file first.")
        return redirect("employee-import-upload", pk=pk)

    if request.method == "POST":
        mapping = {f["key"]: request.POST.get(f"map_{f['key']}", "") for f in WORK_IMPORT_FIELDS}
        missing_required = [f["label"] for f in WORK_IMPORT_FIELDS if f["required"] and not mapping[f["key"]]]
        if missing_required:
            messages.error(request, f"Map a column to: {', '.join(missing_required)}.")
            return render(
                request,
                "teams/work_import_map.html",
                {"employee": employee, "headers": headers, "rows": rows[:8], "fields": WORK_IMPORT_FIELDS, "mapping": mapping},
            )

        col_index = {header: i for i, header in enumerate(headers)}

        def cell(row, key):
            header = mapping[key]
            idx = col_index.get(header)
            if not header or idx is None or idx >= len(row):
                return ""
            return row[idx]

        created = 0
        for row in rows:
            title = cell(row, "title")
            if not title:
                continue
            WorkItem.objects.create(
                employee=employee,
                source=WorkItem.Source.EXCEL,
                title=title,
                work_item_type=cell(row, "work_item_type"),
                state=cell(row, "state"),
                story_points=_parse_story_points(cell(row, "story_points")),
                area_path=cell(row, "area_path"),
                iteration_path=cell(row, "iteration_path"),
                created_date=_parse_work_date(cell(row, "created_date")),
                closed_date=_parse_work_date(cell(row, "closed_date")),
                external_id=cell(row, "external_id"),
                url=cell(row, "url"),
            )
            created += 1

        del request.session["work_import_headers"]
        del request.session["work_import_rows"]
        messages.success(request, f"Imported {created} work item(s) for {employee.name}.")
        return redirect(f"{reverse('employee-work', args=[pk])}?source=excel")

    mapping = {f["key"]: _guess_work_column(headers, f["key"]) for f in WORK_IMPORT_FIELDS}
    return render(
        request,
        "teams/work_import_map.html",
        {"employee": employee, "headers": headers, "rows": rows[:8], "fields": WORK_IMPORT_FIELDS, "mapping": mapping},
    )


def _notes_list_context(employee, category, form=None):
    return {
        "employee": employee,
        "category": category,
        "category_label": NOTE_CATEGORY_LABELS[category],
        "notes": employee.notes.filter(category=category),
        "form": form or EmployeeNoteForm(),
    }


def employee_notes(request, pk, category):
    employee = get_object_or_404(Employee, pk=pk)
    if category not in NOTE_CATEGORY_LABELS:
        raise Http404("Unknown note category.")

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        form = EmployeeNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.employee = employee
            note.category = category
            note.save()
            return render(request, "teams/_notes_list.html", _notes_list_context(employee, category))
        return render(request, "teams/_notes_list.html", _notes_list_context(employee, category, form))

    return render(request, "teams/_notes_list.html", _notes_list_context(employee, category))


def employee_note_edit(request, pk, category, note_id):
    employee = get_object_or_404(Employee, pk=pk)
    if category not in NOTE_CATEGORY_LABELS:
        raise Http404("Unknown note category.")
    note = get_object_or_404(EmployeeNote, pk=note_id, employee=employee, category=category)

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        form = EmployeeNoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            return render(request, "teams/_notes_list.html", _notes_list_context(employee, category))
    else:
        form = EmployeeNoteForm(instance=note)

    return render(
        request,
        "teams/_note_edit_form.html",
        {
            "employee": employee,
            "category": category,
            "category_label": NOTE_CATEGORY_LABELS[category],
            "note": note,
            "form": form,
        },
    )


def employee_note_delete(request, pk, category, note_id):
    employee = get_object_or_404(Employee, pk=pk)
    if category not in NOTE_CATEGORY_LABELS:
        raise Http404("Unknown note category.")
    note = get_object_or_404(EmployeeNote, pk=note_id, employee=employee, category=category)

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        note.delete()
        return render(request, "teams/_notes_list.html", _notes_list_context(employee, category))

    return redirect("employee-notes", pk=pk, category=category)


def employee_note_attachment_add(request, pk, category, note_id):
    employee = get_object_or_404(Employee, pk=pk)
    if category not in NOTE_CATEGORY_LABELS:
        raise Http404("Unknown note category.")
    note = get_object_or_404(EmployeeNote, pk=note_id, employee=employee, category=category)

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        for uploaded_file in request.FILES.getlist("file"):
            EmployeeNoteAttachment.objects.create(note=note, file=uploaded_file)
        return render(request, "teams/_notes_list.html", _notes_list_context(employee, category))

    return redirect("employee-notes", pk=pk, category=category)


def employee_note_attachment_delete(request, pk, category, note_id, attachment_id):
    employee = get_object_or_404(Employee, pk=pk)
    if category not in NOTE_CATEGORY_LABELS:
        raise Http404("Unknown note category.")
    note = get_object_or_404(EmployeeNote, pk=note_id, employee=employee, category=category)
    attachment = get_object_or_404(EmployeeNoteAttachment, pk=attachment_id, note=note)

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        attachment.file.delete(save=False)
        attachment.delete()
        return render(request, "teams/_notes_list.html", _notes_list_context(employee, category))

    return redirect("employee-notes", pk=pk, category=category)


def _flash_import_result(request, result):
    if result["matched"] == 0 and not result["unmatched"]:
        messages.warning(request, "No user stories were found.")
        return
    base = f"Imported {result['matched']} item(s) across {result['employee_count']} employee(s)."
    if result["unmatched"]:
        preview = "; ".join(result["unmatched"][:8])
        more = f" (+{len(result['unmatched']) - 8} more)" if len(result["unmatched"]) > 8 else ""
        messages.warning(
            request,
            f"{base} {len(result['unmatched'])} item(s) skipped — no employee matched: {preview}{more}",
        )
    else:
        messages.success(request, base)


def _analysis_summary():
    employees = Employee.objects.prefetch_related("work_items").order_by("name")
    rows = []
    total_items = 0
    total_points = 0
    for employee in employees:
        items = list(employee.work_items.all())
        if not items:
            continue
        points = sum((i.story_points or 0) for i in items)
        rows.append({"employee": employee, "item_count": len(items), "points": points})
        total_items += len(items)
        total_points += points
    rows.sort(key=lambda r: -r["item_count"])
    return {
        "rows": rows,
        "total_items": total_items,
        "total_points": total_points,
        "employee_count": len(rows),
    }


def analysis_home(request):
    settings_obj = AzureDevOpsSettings.load()
    ado_error = None

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        result, error = run_team_ado_sync(settings_obj)
        if error:
            ado_error = error
        else:
            _flash_import_result(request, result)
            return redirect("team-analysis")

    else:
        due = (
            settings_obj.last_synced_at is None
            or timezone.now() - settings_obj.last_synced_at
            >= timedelta(hours=settings_obj.auto_sync_interval_hours)
        )
        if settings_obj.auto_sync_enabled and settings_obj.team_query_url and settings_obj.personal_access_token and due:
            run_team_ado_sync(settings_obj)
            settings_obj.refresh_from_db()

    return render(
        request,
        "teams/analysis.html",
        {
            "settings_obj": settings_obj,
            "ado_error": ado_error,
            "pat_configured": bool(settings_obj.personal_access_token),
            "summary": _analysis_summary(),
        },
    )


def admin_settings(request):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    if not request.user.is_staff:
        raise PermissionDenied("Admin settings are staff-only.")

    settings_obj = AzureDevOpsSettings.load()

    if request.method == "POST":
        if request.POST.get("action") == "sync_now":
            result, error = run_team_ado_sync(settings_obj)
            if error:
                messages.error(request, f"Sync failed: {error}")
            else:
                _flash_import_result(request, result)
            return redirect("admin-settings")

        settings_obj.organization_url = request.POST.get("organization_url", "").strip()
        settings_obj.personal_access_token = request.POST.get("personal_access_token", "").strip()
        settings_obj.team_query_url = request.POST.get("team_query_url", "").strip()
        settings_obj.auto_sync_enabled = bool(request.POST.get("auto_sync_enabled"))
        try:
            interval = int(request.POST.get("auto_sync_interval_hours", "24"))
        except ValueError:
            interval = 24
        settings_obj.auto_sync_interval_hours = max(1, interval)
        settings_obj.save()
        messages.success(request, "Settings saved.")
        return redirect("admin-settings")

    return render(request, "teams/admin_settings.html", {"settings_obj": settings_obj})


@login_required
def analysis_import_upload(request):
    if request.method == "POST":
        upload = request.FILES.get("file")
        if not upload:
            messages.error(request, "Choose an .xlsx or .csv file to upload.")
            return redirect("analysis-import-upload")

        try:
            headers, data_rows = _read_tabular_file(upload)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("analysis-import-upload")

        if not any(headers) or not data_rows:
            messages.error(request, "That file needs a header row and at least one data row.")
            return redirect("analysis-import-upload")

        request.session["analysis_import_headers"] = headers
        request.session["analysis_import_rows"] = data_rows[:MAX_WORK_IMPORT_ROWS]
        return redirect("analysis-import-map")

    return render(request, "teams/analysis_import_upload.html")


@login_required
def analysis_import_map(request):
    headers = request.session.get("analysis_import_headers")
    rows = request.session.get("analysis_import_rows")
    if not headers or not rows:
        messages.error(request, "Upload a file first.")
        return redirect("analysis-import-upload")

    if request.method == "POST":
        mapping = {f["key"]: request.POST.get(f"map_{f['key']}", "") for f in ANALYSIS_IMPORT_FIELDS}
        missing_required = [f["label"] for f in ANALYSIS_IMPORT_FIELDS if f["required"] and not mapping[f["key"]]]
        if missing_required:
            messages.error(request, f"Map a column to: {', '.join(missing_required)}.")
            return render(
                request,
                "teams/analysis_import_map.html",
                {"headers": headers, "rows": rows[:8], "fields": ANALYSIS_IMPORT_FIELDS, "mapping": mapping},
            )

        col_index = {header: i for i, header in enumerate(headers)}

        def cell(row, key):
            header = mapping[key]
            idx = col_index.get(header)
            if not header or idx is None or idx >= len(row):
                return ""
            return row[idx]

        items = []
        for row in rows:
            title = cell(row, "title")
            if not title:
                continue
            assignee = cell(row, "assignee")
            items.append(
                {
                    "title": title,
                    "work_item_type": cell(row, "work_item_type"),
                    "state": cell(row, "state"),
                    "story_points": _parse_story_points(cell(row, "story_points")),
                    "area_path": cell(row, "area_path"),
                    "iteration_path": cell(row, "iteration_path"),
                    "created_date": _parse_work_date(cell(row, "created_date")),
                    "closed_date": _parse_work_date(cell(row, "closed_date")),
                    "external_id": cell(row, "external_id"),
                    "url": cell(row, "url"),
                    "assigned_to_name": assignee,
                    "assigned_to_email": assignee,
                }
            )

        result = import_team_work_items(items, source=WorkItem.Source.EXCEL, upsert=False)
        del request.session["analysis_import_headers"]
        del request.session["analysis_import_rows"]
        _flash_import_result(request, result)
        return redirect("team-analysis")

    mapping = {f["key"]: _guess_work_column(headers, f["key"]) for f in ANALYSIS_IMPORT_FIELDS}
    return render(
        request,
        "teams/analysis_import_map.html",
        {"headers": headers, "rows": rows[:8], "fields": ANALYSIS_IMPORT_FIELDS, "mapping": mapping},
    )
