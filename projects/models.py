import uuid

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

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
    application = models.ForeignKey(
        "Application", on_delete=models.SET_NULL, null=True, blank=True, related_name="projects"
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

    versions = GenericRelation("DocumentVersion")

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


class TransitionDocumentTemplate(models.Model):
    """The shared definition of one checklist item — its name, category, purpose,
    owner, and relevant systems. Every project's checklist row (TransitionDocument)
    points at one of these instead of keeping its own copy, so editing or archiving
    a template here is what makes an add/edit/delete apply across every project at
    once, instead of needing to be repeated per project."""

    category = models.CharField(max_length=150)
    document = models.CharField(max_length=200)
    purpose = models.TextField(blank=True)
    owner = models.CharField(max_length=150, blank=True)
    systems = models.ManyToManyField(TransitionSystem, blank=True, related_name="template_documents")
    order = models.PositiveIntegerField(default=0)
    archived = models.BooleanField(
        default=False,
        help_text=(
            "Archived templates no longer appear on any project's active checklist, but any files "
            "already uploaded against them are kept rather than deleted."
        ),
    )

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.document


class TransitionDocument(models.Model):
    template = models.ForeignKey(
        TransitionDocumentTemplate,
        on_delete=models.CASCADE,
        null=True,
        related_name="documents",
        help_text="The shared checklist-item definition this row is a per-project instance of.",
    )
    comments = models.CharField(max_length=200, blank=True)
    available = models.BooleanField(
        "Document collected / digitized",
        default=False,
        help_text="Whether this document has actually been gathered and uploaded yet.",
    )
    project = models.ForeignKey(
        "Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transition_documents",
        help_text="The project (application) this transition checklist item belongs to. Each project has its own independent checklist — nothing here is shared across projects.",
    )

    versions = GenericRelation("DocumentVersion")

    class Meta:
        ordering = ["project__name", "template__order", "id"]

    def __str__(self):
        return self.document

    def get_absolute_url(self):
        return reverse("transition-detail", args=[self.pk])

    @property
    def category(self):
        return self.template.category if self.template_id else ""

    @property
    def document(self):
        return self.template.document if self.template_id else ""

    @property
    def purpose(self):
        return self.template.purpose if self.template_id else ""

    @property
    def owner(self):
        return self.template.owner if self.template_id else ""

    @property
    def systems(self):
        return self.template.systems if self.template_id else TransitionSystem.objects.none()


class DocumentActivity(models.TextChoices):
    INTRODUCTION = "introduction", "Introduction"
    GOVERNANCE = "governance", "Governance & Transition Management"
    APP_TECHNICAL = "app_technical", "Application & Technical Documentation"
    INTEGRATION = "integration", "Integration & Interdependency Landscape"
    OPERATIONS = "operations", "Operations & Support"
    KNOWLEDGE_TRANSFER = "knowledge_transfer", "Knowledge Transfer"
    COMPLIANCE = "compliance", "Compliance & Administrative"
    AUDIT = "audit", "Audit & Compliance Checklist"
    DEPLOYMENT = "deployment", "Deployment"
    RISK = "risk", "Risk"


def document_version_path(instance, filename):
    """Auto-generate a clean, consistent stored filename instead of using
    whatever the uploader's file happened to be called locally — the parent's
    title, the version number (already assigned by save() before this runs),
    and the upload date. e.g. raci-matrix-v3-20260829.xlsx"""
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    slug = slugify(instance.parent_label())[:60] or "document"
    date_str = timezone.now().strftime("%Y%m%d")
    clean_name = f"{slug}-v{instance.version}-{date_str}"
    if ext:
        clean_name = f"{clean_name}.{ext}"
    return f"document_versions/{instance.content_type_id}/{instance.object_id}/{clean_name}"


class DocumentVersion(models.Model):
    """A single uploaded file, versioned against whatever it belongs to (an
    Application or a TransitionDocument today) via a generic relation, so both
    kinds of documents share one upload/version-history mechanism. Each upload
    is tagged with the activity that produced it and gets the next version
    number for that parent object, regardless of activity."""

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    parent = GenericForeignKey("content_type", "object_id")
    activity = models.CharField(max_length=30, choices=DocumentActivity.choices)
    version = models.PositiveIntegerField(editable=False, default=0)
    file = models.FileField(upload_to=document_version_path)
    original_filename = models.CharField(
        max_length=255, blank=True,
        help_text="The file name as the uploader had it, kept for reference — the stored file itself is renamed to a consistent versioned name.",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]

    def __str__(self):
        return f"v{self.version} ({self.get_activity_display()})"

    def filename(self):
        return self.file.name.rsplit("/", 1)[-1]

    def parent_label(self):
        parent = self.parent
        if parent is None:
            return "document"
        return getattr(parent, "document", None) or getattr(parent, "name", None) or "document"

    def save(self, *args, **kwargs):
        if not self.version:
            last = (
                DocumentVersion.objects.filter(content_type=self.content_type, object_id=self.object_id)
                .order_by("-version")
                .first()
            )
            self.version = (last.version if last else 0) + 1
        if self.file and not self.original_filename:
            self.original_filename = self.file.name.rsplit("/", 1)[-1]
        super().save(*args, **kwargs)
