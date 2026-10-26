# attendance/models.py

from django.conf import settings
from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sub_departments",
    )

    def __str__(self):
        return self.name


class Employee(models.Model):
    employee_code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="employees",
    )
    manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="team_members",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_profile",
    )
    is_active = models.BooleanField(default=True)
    joining_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.employee_code} - {self.name}"


class ShiftRule(models.Model):
    name = models.CharField(max_length=100, unique=True)
    shift_start = models.TimeField()
    shift_end = models.TimeField()
    grace_minutes = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class AttendanceImportBatch(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]

    uploaded_file = models.FileField(
        upload_to="attendance_imports/",
        null=True,
        blank=True,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_import_batches",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="PENDING",
    )
    total_rows = models.PositiveIntegerField(default=0)
    successful_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    def __str__(self):
        return f"Batch {self.pk} - {self.status}"


class AttendanceLog(models.Model):
    PUNCH_CHOICES = [
        ("IN", "In"),
        ("OUT", "Out"),
        ("OTHER", "Other"),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="attendance_logs",
    )
    batch = models.ForeignKey(
        AttendanceImportBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_logs",
    )
    punch_date = models.DateField()
    punch_time = models.TimeField()
    punch_type = models.CharField(
        max_length=10,
        choices=PUNCH_CHOICES,
        default="OTHER",
    )
    device_location = models.CharField(max_length=100, blank=True)
    shift_rule = models.ForeignKey(
        ShiftRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_logs",
    )
    is_late = models.BooleanField(default=False)
    delay_minutes = models.PositiveIntegerField(default=0)
    is_duplicate = models.BooleanField(default=False)
    anomaly_type = models.CharField(max_length=100, blank=True)
    working_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.employee.employee_code} - "
            f"{self.punch_date} {self.punch_time}"
        )


class AttendanceCorrection(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("MANAGER_APPROVED", "Manager Approved"),
        ("MANAGER_REJECTED", "Manager Rejected"),
        ("FINALIZED", "Finalized"),
    ]

    attendance_log = models.ForeignKey(
        AttendanceLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="corrections",
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="corrections",
    )
    correction_date = models.DateField()
    requested_punch_time = models.TimeField(null=True, blank=True)
    requested_punch_type = models.CharField(max_length=10, blank=True)
    reason = models.TextField()
    supporting_document = models.FileField(
        upload_to="correction_documents/",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_corrections",
    )
    manager_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_corrections",
    )
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finalized_corrections",
    )
    manager_comment = models.TextField(blank=True)
    hr_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Correction {self.pk} - {self.status}"


class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="leave_requests",
    )
    leave_type = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="PENDING",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_leave_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.employee_code} - {self.leave_type}"


class RiskScore(models.Model):
    RISK_CHOICES = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="risk_scores",
    )
    score = models.FloatField()
    risk_level = models.CharField(max_length=10, choices=RISK_CHOICES)
    late_count = models.PositiveIntegerField(default=0)
    absent_count = models.PositiveIntegerField(default=0)
    correction_count = models.PositiveIntegerField(default=0)
    leave_count = models.PositiveIntegerField(default=0)
    average_delay_minutes = models.FloatField(default=0)
    model_name = models.CharField(max_length=100, blank=True)
    features = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.employee_code} - {self.risk_level}"


class EmployeeRemark(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="remarks",
    )
    remark = models.TextField()
    sentiment = models.CharField(max_length=20, blank=True)
    concern_category = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Remark by {self.employee.employee_code}"