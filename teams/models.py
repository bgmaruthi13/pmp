from django.db import models
from django.urls import reverse


class Employee(models.Model):
    class Role(models.TextChoices):
        LEAD = "lead", "Project Lead"
        PLATFORM_LEAD = "platform_lead", "Platform Engineer Lead"
        PLATFORM_ENGINEER = "platform_engineer", "Platform Engineer"
        DATABASE_ENGINEER = "database_engineer", "Database Engineer"
        DEVOPS = "devops", "DevOps / Integration"
        SDM = "sdm", "Service Delivery Manager"

    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    role = models.CharField(max_length=30, choices=Role.choices)
    manager = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="reports"
    )
    azure_devops_query_url = models.URLField(
        blank=True,
        help_text=(
            "Shared query link for this person's work items, e.g. "
            "https://dev.azure.com/{org}/{project}/_workitems/query/{queryId}/"
        ),
    )

    class Meta:
        ordering = ["role", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("employee-detail", args=[self.pk])


class WorkItem(models.Model):
    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        AZURE_DEVOPS = "azure_devops", "Azure DevOps"
        EXCEL = "excel", "Excel / CSV Import"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="work_items")
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)
    external_id = models.CharField(max_length=50, blank=True)
    title = models.CharField(max_length=300)
    work_item_type = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    story_points = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    project_label = models.CharField(max_length=200, blank=True)
    area_path = models.CharField(max_length=200, blank=True)
    iteration_path = models.CharField(max_length=200, blank=True)
    created_date = models.DateField(null=True, blank=True)
    closed_date = models.DateField(null=True, blank=True)
    url = models.URLField(blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)

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
