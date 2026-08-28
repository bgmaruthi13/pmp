"""Team-wide Azure DevOps / import sync logic, shared by the Analysis and
Support views and the sync_azure_devops management command."""

from django.utils import timezone

from .azure_devops import AzureDevOpsError, fetch_work_items
from .models import Employee, SupportTicket, WorkItem


def employee_lookup_maps():
    employees = list(Employee.objects.all())
    by_email = {e.email.strip().lower(): e for e in employees if e.email}
    by_name = {e.name.strip().lower(): e for e in employees}
    return by_email, by_name


def match_employee(by_email, by_name, email="", name=""):
    email = (email or "").strip().lower()
    name = (name or "").strip().lower()
    if email and email in by_email:
        return by_email[email]
    if name and name in by_name:
        return by_name[name]
    return None


def import_team_records(items, model, source, upsert):
    """Match each item's assignee to an Employee and save it as an instance of
    `model` (WorkItem or SupportTicket - both share the same relevant field names).
    upsert=True keeps at most one row per (employee, source, external_id) - safe for
    Azure DevOps, which has stable IDs. upsert=False always inserts a new row - used
    for Excel/CSV imports, whose rows may not carry a unique external_id."""
    by_email, by_name = employee_lookup_maps()
    matched = 0
    unmatched = []
    employees_touched = set()

    for raw_item in items:
        item = dict(raw_item)
        assigned_name = item.pop("assigned_to_name", "")
        assigned_email = item.pop("assigned_to_email", "")
        employee = match_employee(by_email, by_name, assigned_email, assigned_name)
        if not employee:
            label = assigned_name or assigned_email or "(unassigned)"
            unmatched.append(f"{label} — {item.get('title', '')[:40]}")
            continue

        item["assigned_to_raw"] = assigned_name or assigned_email
        external_id = item.pop("external_id", "")
        if upsert and external_id:
            model.objects.update_or_create(
                employee=employee, source=source, external_id=external_id, defaults=item
            )
        else:
            model.objects.create(employee=employee, source=source, external_id=external_id, **item)
        matched += 1
        employees_touched.add(employee.pk)

    return {"matched": matched, "unmatched": unmatched, "employee_count": len(employees_touched)}


def import_team_work_items(items, source, upsert):
    return import_team_records(items, WorkItem, source, upsert)


def run_team_ado_sync(settings_obj):
    """Run the team-wide Azure DevOps sync for user stories (WorkItem) and persist
    the outcome on settings_obj. Returns (result_dict_or_None, error_message_or_None)."""
    if not settings_obj.team_query_url:
        return None, "No query URL is configured."
    if not settings_obj.personal_access_token:
        return None, (
            "No shared PAT is configured. Ask an admin to set one under "
            "Admin > Teams > Azure DevOps settings."
        )

    try:
        fetched = fetch_work_items(settings_obj.team_query_url, settings_obj.personal_access_token)
    except AzureDevOpsError as exc:
        settings_obj.last_synced_at = timezone.now()
        settings_obj.last_sync_success = False
        settings_obj.last_sync_error = str(exc)
        settings_obj.save(update_fields=["last_synced_at", "last_sync_success", "last_sync_error"])
        return None, str(exc)

    result = import_team_records(fetched, WorkItem, WorkItem.Source.AZURE_DEVOPS, upsert=True)
    settings_obj.last_synced_at = timezone.now()
    settings_obj.last_sync_success = True
    settings_obj.last_sync_error = ""
    settings_obj.last_sync_item_count = result["matched"]
    settings_obj.save(
        update_fields=["last_synced_at", "last_sync_success", "last_sync_error", "last_sync_item_count"]
    )
    return result, None


def run_support_ado_sync(settings_obj):
    """Run the team-wide Azure DevOps sync for support tickets (SupportTicket) and
    persist the outcome on settings_obj. Returns (result_dict_or_None, error_message_or_None)."""
    if not settings_obj.support_query_url:
        return None, "No query URL is configured."
    if not settings_obj.personal_access_token:
        return None, (
            "No shared PAT is configured. Ask an admin to set one under "
            "Admin > Teams > Azure DevOps settings."
        )

    try:
        fetched = fetch_work_items(settings_obj.support_query_url, settings_obj.personal_access_token)
    except AzureDevOpsError as exc:
        settings_obj.support_last_synced_at = timezone.now()
        settings_obj.support_last_sync_success = False
        settings_obj.support_last_sync_error = str(exc)
        settings_obj.save(
            update_fields=["support_last_synced_at", "support_last_sync_success", "support_last_sync_error"]
        )
        return None, str(exc)

    result = import_team_records(fetched, SupportTicket, SupportTicket.Source.AZURE_DEVOPS, upsert=True)
    settings_obj.support_last_synced_at = timezone.now()
    settings_obj.support_last_sync_success = True
    settings_obj.support_last_sync_error = ""
    settings_obj.support_last_sync_item_count = result["matched"]
    settings_obj.save(
        update_fields=[
            "support_last_synced_at",
            "support_last_sync_success",
            "support_last_sync_error",
            "support_last_sync_item_count",
        ]
    )
    return result, None
