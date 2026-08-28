import base64
from datetime import datetime
from urllib.parse import urlparse

import requests

API_VERSION = "7.1"
TIMEOUT = 20
BATCH_SIZE = 200

FIELDS = [
    "System.Id",
    "System.Title",
    "System.WorkItemType",
    "System.State",
    "System.TeamProject",
    "System.AreaPath",
    "System.IterationPath",
    "System.AssignedTo",
    "System.Tags",
    "System.CreatedDate",
    "Microsoft.VSTS.Scheduling.StoryPoints",
    "Microsoft.VSTS.Common.Priority",
    "Microsoft.VSTS.Common.ClosedDate",
]


class AzureDevOpsError(Exception):
    pass


def parse_query_url(query_url):
    """Extract (base_url, organization, project, query_id) from a shared ADO query link,
    e.g. https://dev.azure.com/{org}/{project}/_workitems/query/{queryId}/"""
    parsed = urlparse(query_url)
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 4 or "_workitems" not in parts or "query" not in parts:
        raise AzureDevOpsError(
            "Could not parse that query URL. Expected something like "
            "https://dev.azure.com/{org}/{project}/_workitems/query/{queryId}/"
        )
    organization = parts[0]
    project = parts[1]
    query_index = parts.index("query")
    if query_index + 1 >= len(parts):
        raise AzureDevOpsError("That URL doesn't contain a query ID.")
    query_id = parts[query_index + 1]
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    return base_url, organization, project, query_id


def _auth_header(pat):
    token = base64.b64encode(f":{pat}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _parse_assigned_to(value):
    """AssignedTo comes back as an IdentityRef dict on most orgs, or a plain
    "Display Name <email>" string on some legacy ones."""
    if isinstance(value, dict):
        name = value.get("displayName", "") or ""
        email = value.get("uniqueName") or value.get("mail") or ""
        return name, email
    if isinstance(value, str) and value:
        if "<" in value and value.endswith(">"):
            name, _, rest = value.partition("<")
            return name.strip(), rest.rstrip(">").strip()
        return value, ""
    return "", ""


def fetch_work_items(query_url, pat):
    """Run a shared WIQL query and return a list of work item field dicts."""
    if not pat:
        raise AzureDevOpsError(
            "No Azure DevOps PAT is configured. Ask an admin to set one under "
            "Admin > Teams > Azure DevOps settings."
        )

    base_url, organization, project, query_id = parse_query_url(query_url)
    headers = _auth_header(pat)

    wiql_url = f"{base_url}/{organization}/{project}/_apis/wit/wiql/{query_id}?api-version={API_VERSION}"
    try:
        resp = requests.get(wiql_url, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise AzureDevOpsError(f"Could not reach Azure DevOps: {exc}") from exc

    if resp.status_code == 401:
        raise AzureDevOpsError("Azure DevOps rejected the PAT (401 Unauthorized).")
    if resp.status_code == 404:
        raise AzureDevOpsError("Query not found (404). Check the organization/project/query ID in the URL.")
    if not resp.ok:
        raise AzureDevOpsError(f"Azure DevOps returned {resp.status_code}: {resp.text[:300]}")

    payload = resp.json()
    ids = [item["id"] for item in payload.get("workItems", [])]
    if not ids and payload.get("workItemRelations"):
        seen = set()
        for rel in payload["workItemRelations"]:
            target = rel.get("target")
            if target and target["id"] not in seen:
                seen.add(target["id"])
                ids.append(target["id"])

    if not ids:
        return []

    batch_url = f"{base_url}/{organization}/_apis/wit/workitemsbatch?api-version={API_VERSION}"
    items = []
    for start in range(0, len(ids), BATCH_SIZE):
        chunk = ids[start : start + BATCH_SIZE]
        try:
            resp = requests.post(
                batch_url,
                headers={**headers, "Content-Type": "application/json"},
                json={"ids": chunk, "fields": FIELDS},
                timeout=TIMEOUT,
            )
        except requests.RequestException as exc:
            raise AzureDevOpsError(f"Could not reach Azure DevOps: {exc}") from exc
        if not resp.ok:
            raise AzureDevOpsError(f"Azure DevOps returned {resp.status_code}: {resp.text[:300]}")

        for entry in resp.json().get("value", []):
            fields = entry.get("fields", {})
            work_item_id = entry.get("id")
            assigned_to_name, assigned_to_email = _parse_assigned_to(fields.get("System.AssignedTo"))
            items.append(
                {
                    "external_id": str(work_item_id or ""),
                    "title": fields.get("System.Title", ""),
                    "work_item_type": fields.get("System.WorkItemType", ""),
                    "state": fields.get("System.State", ""),
                    "project_label": fields.get("System.TeamProject", ""),
                    "area_path": fields.get("System.AreaPath", ""),
                    "iteration_path": fields.get("System.IterationPath", ""),
                    "story_points": fields.get("Microsoft.VSTS.Scheduling.StoryPoints"),
                    "priority": fields.get("Microsoft.VSTS.Common.Priority"),
                    "tags": fields.get("System.Tags", ""),
                    "created_date": _parse_date(fields.get("System.CreatedDate")),
                    "closed_date": _parse_date(fields.get("Microsoft.VSTS.Common.ClosedDate")),
                    "url": f"{base_url}/{organization}/{project}/_workitems/edit/{work_item_id}",
                    "assigned_to_name": assigned_to_name,
                    "assigned_to_email": assigned_to_email,
                }
            )
    return items
