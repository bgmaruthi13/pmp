from datetime import date

from django.db import models
from django.urls import reverse


def _duration_display(start_date):
    """Years/months between start_date and today, formatted as e.g. "3 yrs 2 mo" —
    computed on the fly so it never needs to be manually kept up to date."""
    if not start_date:
        return None
    today = date.today()
    months = (today.year - start_date.year) * 12 + (today.month - start_date.month)
    if today.day < start_date.day:
        months -= 1
    months = max(months, 0)
    years, months = divmod(months, 12)
    if years and months:
        return f"{years} yr{'s' if years != 1 else ''} {months} mo"
    if years:
        return f"{years} yr{'s' if years != 1 else ''}"
    return f"{months} mo"

DEFAULT_ROLES = [
    "Project Lead",
    "Platform Engineer Lead",
    "Platform Engineer",
    "Database Engineer",
    "DevOps / Integration",
    "Developer",
    "Service Delivery Manager",
]


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Employee(models.Model):
    class EmploymentType(models.TextChoices):
        PERMANENT = "permanent", "Permanent"
        CONTRACT = "contract", "Contract"

    name = models.CharField(max_length=150)
    emp_id = models.CharField("EMP ID", max_length=20, blank=True)
    email = models.EmailField(blank=True)
    photo = models.ImageField(upload_to="employee_photos/", blank=True, null=True)
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, blank=True,
        help_text="Whether this person is a permanent employee or on contract.",
    )
    career_start_date = models.DateField(
        "Career start date",
        null=True,
        blank=True,
        help_text="When this person's professional career began — used to compute total years of experience.",
    )
    designation = models.CharField(
        max_length=150, blank=True, help_text="Job title / grade, e.g. Lead Software Engineer."
    )
    country = models.CharField(
        max_length=100, blank=True, help_text="Where this person is based, e.g. India."
    )
    roles = models.ManyToManyField(Role, related_name="employees", blank=True)
    projects = models.ManyToManyField(
        "projects.Project", related_name="team_members", blank=True
    )
    manager = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="reports"
    )
    line_manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="line_reports",
        verbose_name="Line reporting manager",
        help_text="Skip-level / dotted-line manager, when different from the direct manager.",
    )
    doj = models.DateField("Date of joining", null=True, blank=True)
    awards = models.TextField(blank=True)
    rtb_efficiency = models.DecimalField(
        "RTB efficiency %",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Applies to this person's team, when they're set as someone's manager or line manager.",
    )
    gsc_efficiency = models.DecimalField(
        "GSC efficiency %",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Applies to this person's team, when they're set as someone's manager or line manager.",
    )
    ai_efficiency = models.DecimalField(
        "AI efficiency %",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Applies to this person's team, when they're set as someone's manager or line manager.",
    )
    azure_devops_query_url = models.URLField(
        blank=True,
        help_text=(
            "Shared query link for this person's work items, e.g. "
            "https://dev.azure.com/{org}/{project}/_workitems/query/{queryId}/"
        ),
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("employee-detail", args=[self.pk])

    def roles_display(self):
        return ", ".join(r.name for r in self.roles.all())

    def org_experience_display(self):
        return _duration_display(self.doj)

    def total_experience_display(self):
        return _duration_display(self.career_start_date)


class EmployeeNote(models.Model):
    class Category(models.TextChoices):
        WFH_EXCEPTION = "wfh_exception", "WFH Exception"
        ACHIEVEMENT = "achievement", "Achievement"
        ESCALATION = "escalation", "Escalation"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="notes")
    category = models.CharField(max_length=20, choices=Category.choices)
    date = models.DateField(null=True, blank=True)
    description = models.TextField()
    work_item_ref = models.CharField(
        "Linked user story / ticket",
        max_length=300,
        blank=True,
        help_text="e.g. an Azure DevOps work item number, or a full link to the ticket.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.get_category_display()}: {self.description[:40]}"

    def work_item_is_link(self):
        return self.work_item_ref.lower().startswith(("http://", "https://"))


def employee_note_attachment_path(instance, filename):
    return f"employee_notes/{instance.note.employee_id}/{instance.note_id}/{filename}"


class EmployeeNoteAttachment(models.Model):
    note = models.ForeignKey(EmployeeNote, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to=employee_note_attachment_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.filename()

    def filename(self):
        return self.file.name.rsplit("/", 1)[-1]


class WorkItem(models.Model):
    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        AZURE_DEVOPS = "azure_devops", "Azure DevOps"
        EXCEL = "excel", "Excel / CSV Import"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="work_items")
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)
    external_id = models.CharField(max_length=50, blank=True)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    work_item_type = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    story_points = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    project_label = models.CharField(max_length=200, blank=True)
    area_path = models.CharField(max_length=200, blank=True)
    iteration_path = models.CharField(max_length=200, blank=True)
    priority = models.PositiveSmallIntegerField(null=True, blank=True)
    tags = models.CharField(max_length=300, blank=True)
    assigned_to_raw = models.CharField(
        "Assigned to (as imported)",
        max_length=200,
        blank=True,
        help_text="The raw assignee name/email from the source, kept for traceability.",
    )
    created_date = models.DateField(null=True, blank=True)
    closed_date = models.DateField(null=True, blank=True)
    url = models.URLField(blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-closed_date", "-created_date"]

    def __str__(self):
        return self.title


class SupportTicket(models.Model):
    """Helpdesk / incident-style support tickets - tracked separately from user
    stories (WorkItem) since they're a different kind of work with their own page,
    even though the record shape and import/sync mechanics are the same."""

    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        AZURE_DEVOPS = "azure_devops", "Azure DevOps"
        EXCEL = "excel", "Excel / CSV Import"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="support_tickets")
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)
    external_id = models.CharField(max_length=50, blank=True)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    work_item_type = models.CharField("Ticket type", max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    story_points = models.DecimalField("Effort", max_digits=6, decimal_places=1, null=True, blank=True)
    project_label = models.CharField(max_length=200, blank=True)
    area_path = models.CharField(max_length=200, blank=True)
    iteration_path = models.CharField(max_length=200, blank=True)
    priority = models.PositiveSmallIntegerField(null=True, blank=True)
    tags = models.CharField(max_length=300, blank=True)
    assigned_to_raw = models.CharField(
        "Assigned to (as imported)",
        max_length=200,
        blank=True,
        help_text="The raw assignee name/email from the source, kept for traceability.",
    )
    created_date = models.DateField(null=True, blank=True)
    closed_date = models.DateField(null=True, blank=True)
    url = models.URLField(blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    related_work_item = models.ForeignKey(
        WorkItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="related_tickets",
        help_text="Optional: the change/user story this ticket led to, if any. Set manually — not auto-matched.",
    )

    class Meta:
        ordering = ["-closed_date", "-created_date"]

    def __str__(self):
        return self.title


class AzureDevOpsSettings(models.Model):
    organization_url = models.URLField(
        blank=True, help_text="e.g. https://dev.azure.com/your-organization"
    )
    personal_access_token = models.CharField(
        max_length=300, blank=True, help_text="Shared PAT used for all Azure DevOps queries."
    )
    team_query_url = models.URLField(
        "Team-wide user stories query URL",
        blank=True,
        help_text=(
            "Shared query link returning user stories for the whole team (across assignees), "
            "used by the Analysis tab. e.g. https://dev.azure.com/{org}/{project}/_workitems/query/{queryId}/"
        ),
    )
    auto_sync_enabled = models.BooleanField(
        "Automatically keep user stories in sync",
        default=False,
        help_text=(
            "When on, the Analysis tab re-syncs itself in the background at most once per "
            "interval below. python manage.py sync_azure_devops does the same sync and can be "
            "wired up to an external daily cron for a more reliable schedule."
        ),
    )
    auto_sync_interval_hours = models.PositiveIntegerField(default=24)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_sync_success = models.BooleanField(default=False)
    last_sync_error = models.TextField(blank=True)
    last_sync_item_count = models.PositiveIntegerField(null=True, blank=True)

    support_query_url = models.URLField(
        "Support tickets query URL",
        blank=True,
        help_text=(
            "Shared query link returning support tickets for the whole team (across assignees), "
            "used by the Support tab. e.g. https://dev.azure.com/{org}/{project}/_workitems/query/{queryId}/"
        ),
    )
    support_auto_sync_enabled = models.BooleanField(
        "Automatically keep support tickets in sync", default=False
    )
    support_auto_sync_interval_hours = models.PositiveIntegerField(default=24)
    support_last_synced_at = models.DateTimeField(null=True, blank=True)
    support_last_sync_success = models.BooleanField(default=False)
    support_last_sync_error = models.TextField(blank=True)
    support_last_sync_item_count = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Azure DevOps settings"
        verbose_name_plural = "Azure DevOps settings"

    def __str__(self):
        return "Azure DevOps settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
