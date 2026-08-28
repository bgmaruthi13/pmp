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

    class Meta:
        ordering = ["role", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("employee-detail", args=[self.pk])
