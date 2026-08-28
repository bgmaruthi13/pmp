from django.contrib import admin

from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "manager", "email")
    list_filter = ("role",)
    search_fields = ("name", "email")
