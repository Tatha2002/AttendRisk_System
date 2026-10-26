from django.contrib import admin
from .models import (
    Department,
    Employee,
    ShiftRule,
    AttendanceImportBatch,
    AttendanceLog,
    AttendanceCorrection,
    LeaveRequest,
    RiskScore,
    EmployeeRemark,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "parent")
    search_fields = ("name", "code")
    list_filter = ("parent",)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "employee_code", "name", "department",
        "manager", "is_active",
    )
    search_fields = ("employee_code", "name", "email", "phone")
    list_filter = ("department", "is_active")
    readonly_fields = ("id",)


@admin.register(ShiftRule)
class ShiftRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "shift_start", "shift_end",
                    "grace_minutes", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(AttendanceImportBatch)
class AttendanceImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "id", "uploaded_at", "uploaded_by", "status",
        "total_rows", "successful_rows", "failed_rows",
    )
    list_filter = ("status", "uploaded_at")
    search_fields = ("id", "error_message")
    readonly_fields = (
        "uploaded_at", "total_rows",
        "successful_rows", "failed_rows",
    )


@admin.register(AttendanceLog)
class AttendanceLogAdmin(admin.ModelAdmin):
    list_display = (
        "employee", "punch_date", "punch_time",
        "punch_type", "is_late", "delay_minutes",
    )
    list_filter = (
        "employee__department", "punch_date",
        "punch_type", "is_late",
    )
    search_fields = (
        "employee__employee_code",
        "employee__name",
        "device_location",
    )
    date_hierarchy = "punch_date"
    readonly_fields = ("created_at",)


@admin.register(AttendanceCorrection)
class AttendanceCorrectionAdmin(admin.ModelAdmin):
    list_display = (
        "employee", "correction_date",
        "status", "requested_by", "created_at",
    )
    list_filter = (
        "status", "correction_date",
        "employee__department",
    )
    search_fields = (
        "employee__employee_code",
        "employee__name",
    )
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Correction Details", {
            "fields": (
                "employee", "attendance_log", "correction_date",
                "requested_punch_time", "requested_punch_type",
                "reason", "supporting_document",
            )
        }),
        ("Approval Workflow", {
            "fields": (
                "status", "requested_by", "manager_reviewed_by",
                "manager_comment", "finalized_by", "hr_comment",
            )
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = (
        "employee", "leave_type", "start_date",
        "end_date", "status",
    )
    list_filter = (
        "status", "leave_type", "start_date",
        "employee__department",
    )
    search_fields = ("employee__employee_code", "employee__name")


@admin.register(RiskScore)
class RiskScoreAdmin(admin.ModelAdmin):
    list_display = (
        "employee", "score", "risk_level", "generated_at",
    )
    list_filter = ("risk_level", "generated_at")
    search_fields = ("employee__employee_code", "employee__name")
    readonly_fields = ("generated_at",)


@admin.register(EmployeeRemark)
class EmployeeRemarkAdmin(admin.ModelAdmin):
    list_display = (
        "employee", "sentiment", "concern_category", "created_at",
    )
    list_filter = ("sentiment", "concern_category", "created_at")
    search_fields = ("employee__employee_code", "remark")
    readonly_fields = ("created_at",)