import uuid

from django.db import models
from django.urls import reverse

from teams.models import Employee


class Area(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Project(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    lead = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="projects_led"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("project-detail", args=[self.pk])


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", "To Do"
        IN_PROGRESS = "in_progress", "In Progress"
        DONE = "done", "Done"

    class TicketType(models.TextChoices):
        PLANNED = "planned", "Planned"
        ADHOC = "adhoc", "Ad Hoc"

    ticket_id = models.CharField(max_length=20, unique=True, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks")
    ticket_type = models.CharField(max_length=10, choices=TicketType.choices, default=TicketType.PLANNED)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    assigned_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets_assigned"
    )
    assignee = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets_received"
    )
    due_date = models.DateField(null=True, blank=True)
    sdm_attention = models.BooleanField(default=False)
    remarks = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ticket_id} · {self.title}"

    def get_absolute_url(self):
        return reverse("ticket-detail", args=[self.pk])

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            last = Task.objects.order_by("-id").first()
            next_num = (last.id if last else 0) + 1
            self.ticket_id = f"TCK-{next_num:04d}"
        super().save(*args, **kwargs)


class Application(models.Model):
    class Sensitivity(models.TextChoices):
        CRITICAL = "2-critical", "2-Critical"
        HIGH = "3-high", "3-High"
        MEDIUM = "4-medium", "4-Medium"

    class ObjectType(models.TextChoices):
        APPLICATION = "application", "Application"
        SERVICE = "service", "Service"

    class ApplicationType(models.TextChoices):
        BUSINESS = "business_capabilities", "Business Capabilities"
        IT = "it_capabilities", "IT Capabilities"

    class ProcurementType(models.TextChoices):
        IN_HOUSE = "in_house", "In House Development"
        SOFTWARE_PACKAGE = "software_package", "Software Package"

    class RebuildConfidence(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    global_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=200)
    domain = models.CharField(
        max_length=150, blank=True,
        help_text="Business/functional domain, e.g. Tax Filing, Payments, Identity & KYC.",
    )
    sensitivity = models.CharField(max_length=20, choices=Sensitivity.choices, default=Sensitivity.HIGH)
    architecture_container = models.CharField(max_length=150, blank=True)
    gsc_owner = models.CharField(max_length=150, blank=True)
    it_perimeter_lvl2 = models.CharField(max_length=150, blank=True)
    it_perimeter_lvl3 = models.CharField(max_length=150, blank=True)
    object_type = models.CharField(max_length=20, choices=ObjectType.choices, default=ObjectType.APPLICATION)
    application_type = models.CharField(max_length=30, choices=ApplicationType.choices, blank=True)
    procurement_type = models.CharField(max_length=30, choices=ProcurementType.choices, blank=True)
    officer = models.CharField(max_length=150, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # -- Backup / disaster-recovery posture --
    p_level = models.CharField("P Level", max_length=20, blank=True)
    globalgov_lvl1 = models.CharField("GlobalGov lvl.1", max_length=150, blank=True)
    globalgov_lvl2 = models.CharField("GlobalGov lvl.2", max_length=150, blank=True)
    backup_status = models.CharField(max_length=150, blank=True)
    backup_solution = models.CharField(
        "Backup solution used", max_length=300, blank=True,
        help_text="e.g. Veeam, TSM, Commvault, BRMS.",
    )
    backup_coverage_level = models.CharField(
        "Backup coverage level", max_length=200, blank=True,
        help_text="e.g. Total, Partial, No backup.",
    )
    rebuild_confidence = models.CharField(
        "Confidence to rebuild if erased in production",
        max_length=10, choices=RebuildConfidence.choices, blank=True,
    )
    last_backup_date = models.CharField("Date of last backup", max_length=100, blank=True)
    last_restore_date = models.CharField("Date of last data restore", max_length=100, blank=True)
    last_rebuild_date = models.CharField(
        "Last date app rebuilt using the backup", max_length=100, blank=True,
        help_text="Free text, since sources record this as either a date or a note (e.g. 'Never').",
    )
    backup_limitations = models.TextField(
        "Known limitations or risks regarding backup/recoverability", blank=True,
    )
    description = models.TextField(blank=True)
    status = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("application-detail", args=[self.pk])


class TransitionSystem(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class TransitionDocument(models.Model):
    category = models.CharField(max_length=150)
    document = models.CharField(max_length=200)
    purpose = models.TextField(blank=True)
    owner = models.CharField(max_length=150, blank=True)
    systems = models.ManyToManyField(TransitionSystem, blank=True, related_name="documents")
    comments = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)
    available = models.BooleanField(
        "Document collected / digitized",
        default=False,
        help_text="Whether this document has actually been gathered and uploaded yet.",
    )

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.document

    def get_absolute_url(self):
        return reverse("transition-detail", args=[self.pk])
