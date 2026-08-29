from django.contrib import admin

from .models import Application, Area, Project, Task, TransitionDocument, TransitionSystem


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0
    readonly_fields = ("ticket_id",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "lead", "created_at")
    search_fields = ("name",)
    inlines = [TaskInline]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("ticket_id", "title", "project", "area", "ticket_type", "status", "assignee", "due_date")
    list_filter = ("status", "ticket_type", "project", "area")
    search_fields = ("ticket_id", "title")
    readonly_fields = ("ticket_id",)


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("name", "sensitivity", "application_type", "procurement_type", "officer", "country")
    list_filter = ("sensitivity", "application_type", "procurement_type")
    search_fields = ("name", "officer")


@admin.register(TransitionSystem)
class TransitionSystemAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(TransitionDocument)
class TransitionDocumentAdmin(admin.ModelAdmin):
    list_display = ("document", "category", "owner", "available", "order")
    list_filter = ("category", "available")
    filter_horizontal = ("systems",)
