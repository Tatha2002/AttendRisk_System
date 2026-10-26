
from datetime import datetime, time
from datetime import datetime, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from .forms import AttendanceUploadForm, AttendanceCorrectionForm
from .models import (
    AttendanceImportBatch,
    Employee,
    AttendanceLog,
    ShiftRule,
    AttendanceCorrection,
)

from scripts.attendance_processor import process_attendance_file

from datetime import date
from django.db.models import Q
from django.core.paginator import Paginator

from django.shortcuts import get_object_or_404
from django.db import transaction

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .models import AttendanceCorrection, Employee


def is_hr_user(user):
    """
    Allow only HR users and Django superusers to upload attendance CSV files.
    """
    role = str(getattr(user, "role", "")).upper().replace(" ", "_")
    return user.is_superuser or role == "HR"


def save_attendance_records(records, batch):
    """
    Save valid attendance punches for employees who already exist
    in the database.

    Returns:
        saved_count: Number of attendance punches saved.
        failed_count: Number of records skipped because the employee
                      does not exist.
    """
    saved_count = 0
    failed_count = 0

    with transaction.atomic():
        for record in records:
            # Skip leave records; leave requests will be handled separately.
            punch_type = str(record.get("punch_type", "")).upper()

            if punch_type == "LEAVE" or record.get("leave_type"):
                continue

            try:
                employee = Employee.objects.get(
                    employee_code=record["employee_code"]
                )
            except Employee.DoesNotExist:
                failed_count += 1
                continue

            # Get the attendance date.
            punch_date = record.get("_date")

            if not punch_date:
                punch_date = datetime.strptime(
                    str(record["punch_date"]),
                    "%Y-%m-%d",
                ).date()

            # Get the attendance time.
            punch_time = record.get("_time")

            if not punch_time:
                punch_time = datetime.strptime(
                    str(record["punch_time"]),
                    "%H:%M",
                ).time()

            # Get the shift start time.
            shift_start = record.get("_shift_start")

            if not shift_start:
                shift_start = time.fromisoformat(
                    str(record["shift_start"])
                )

            # Get the shift end time.
            shift_end = record.get("_shift_end")

            if not shift_end:
                shift_end = time.fromisoformat(
                    str(record["shift_end"])
                )

            grace_minutes = record.get("_grace_minutes", 15)

            # Create or reuse a shift rule.
            shift_name = (
                f"{shift_start.strftime('%H:%M')}-"
                f"{shift_end.strftime('%H:%M')}"
            )

            shift_rule, _ = ShiftRule.objects.get_or_create(
                name=shift_name,
                defaults={
                    "shift_start": shift_start,
                    "shift_end": shift_end,
                    "grace_minutes": grace_minutes,
                },
            )

            # Save the attendance punch.
            AttendanceLog.objects.create(
                employee=employee,
                batch=batch,
                punch_date=punch_date,
                punch_time=punch_time,
                punch_type=punch_type,
                device_location=record.get("device_location", ""),
                shift_rule=shift_rule,
                is_late=record.get("is_late", False),
                delay_minutes=record.get("delay_minutes", 0),
                remarks=record.get("remarks", ""),
            )

            saved_count += 1

    return saved_count, failed_count


@login_required
@require_http_methods(["GET", "POST"])
def attendance_upload(request):
    """
    Allow HR users to upload and process attendance CSV files.
    """
    if not is_hr_user(request.user):
        return HttpResponseForbidden(
            "Only HR users can upload attendance files."
        )

    if request.method == "POST":
        form = AttendanceUploadForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            batch = form.save(commit=False)
            batch.uploaded_by = request.user
            batch.status = "PROCESSING"
            batch.save()

            try:
                # Process the uploaded CSV file.
                result = process_attendance_file(
                    batch.uploaded_file.path
                )

                # Save processed attendance records to the database.
                saved_count, failed_count = save_attendance_records(
                    result["records"],
                    batch,
                )

                # Update import batch statistics.
                batch.status = "COMPLETED"
                batch.total_rows = result["total_rows"]
                batch.successful_rows = saved_count
                batch.failed_rows = failed_count
                batch.error_message = ""
                batch.save()

                messages.success(
                    request,
                    (
                        "CSV processed successfully. "
                        f"Total rows: {result['total_rows']}. "
                        f"Saved attendance punches: {saved_count}. "
                        f"Rows not imported: {failed_count}. "
                        f"Anomalies: {result['anomalies']}."
                    ),
                )

                return redirect("attendance-upload")

            except Exception as exc:
                batch.status = "FAILED"
                batch.error_message = str(exc)
                batch.save()

                messages.error(
                    request,
                    "CSV processing failed. Check the batch status "
                    "in Django admin.",
                )

    else:
        form = AttendanceUploadForm()

    # Show the latest 10 import batches.
    batches = AttendanceImportBatch.objects.order_by(
        "-uploaded_at"
    )[:10]

    return render(
        request,
        "attendance/upload.html",
        {
            "form": form,
            "batches": batches,
        },
    )


@login_required
@require_http_methods(["GET"])
def attendance_list(request):
    role = str(getattr(request.user, "role", "")).upper().replace(" ", "_")

    allowed_roles = {"HR", "HR_ADMIN", "ADMIN", "MANAGER"}

    if not (request.user.is_superuser or role in allowed_roles):
        return HttpResponseForbidden(
            "Only HR Admin and Managers can view attendance records."
        )

    records = AttendanceLog.objects.select_related(
        "employee",
        "employee__department",
        "shift_rule",
    ).order_by("-punch_date", "-punch_time")

    # Search by employee code, name, or email
    search = request.GET.get("search", "").strip()

    if search:
        records = records.filter(
            Q(employee__employee_code__icontains=search)
            | Q(employee__name__icontains=search)
            | Q(employee__email__icontains=search)
        )

    # Filter by date
    selected_date = request.GET.get("date", "").strip()

    if selected_date:
        try:
            date.fromisoformat(selected_date)
            records = records.filter(punch_date=selected_date)
        except ValueError:
            selected_date = ""

    # Optional late-punch filter
    late_only = request.GET.get("late", "") == "1"

    if late_only:
        records = records.filter(is_late=True)

    paginator = Paginator(records, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "search": search,
        "selected_date": selected_date,
        "late_only": late_only,
        "total_records": paginator.count,
    }

    return render(
        request,
        "attendance/attendance_list.html",
        context,
    )


@login_required
@require_http_methods(["GET", "POST"])
def correction_request(request):
    # Find the employee profile linked to the logged-in user.
    employee = Employee.objects.filter(
        user_id=request.user.pk
    ).first()

    # Temporary debugging information.
    print("Logged-in user ID:", request.user.pk)
    print("Logged-in username:", request.user.get_username())
    print("Logged-in email:", getattr(request.user, "email", None))
    print("Linked employee:", employee)

    if employee is None:
        return HttpResponseForbidden(
            "Your user account is not linked to an employee profile. "
            f"Logged-in user ID: {request.user.pk}"
        )

    if request.method == "POST":
        form = AttendanceCorrectionForm(
            request.POST,
            request.FILES,
        )
    else:
        form = AttendanceCorrectionForm(
            initial={"employee": employee}
        )

    # Employees can select only their own profile and attendance logs.
    form.fields["employee"].queryset = Employee.objects.filter(
        pk=employee.pk
    )

    form.fields["attendance_log"].queryset = AttendanceLog.objects.filter(
        employee=employee
    )

    if request.method == "POST":
        if form.is_valid():
            correction = form.save(commit=False)
            correction.employee = employee
            correction.requested_by = request.user
            correction.status = "PENDING"
            correction.save()

            messages.success(
                request,
                "Your attendance correction request was submitted successfully.",
            )
            return redirect("correction-request")

    return render(
        request,
        "attendance/correction_form.html",
        {
            "form": form,
            "employee": employee,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def manager_correction_review(request):
    role = str(
        getattr(request.user, "role", "")
    ).upper().replace(" ", "_")

    if not (request.user.is_superuser or role == "MANAGER"):
        return HttpResponseForbidden(
            "Only Managers can review correction requests."
        )

    # Find the manager's employee profile
    manager_employee = Employee.objects.filter(
        user=request.user
    ).first()

    if manager_employee is None and not request.user.is_superuser:
        return HttpResponseForbidden(
            "Your account is not linked to a manager profile."
        )

    # Managers can review requests from their assigned employees.
    # Superusers can review all requests for administrative testing.
    corrections = AttendanceCorrection.objects.select_related(
        "employee",
        "attendance_log",
        "requested_by",
    ).filter(status="PENDING")

    if not request.user.is_superuser:
        corrections = corrections.filter(
            employee__manager=manager_employee
        )

    if request.method == "POST":
        correction_id = request.POST.get("correction_id")
        decision = request.POST.get("decision")
        comment = request.POST.get("manager_comment", "").strip()

        if decision not in {"approve", "reject"}:
            messages.error(request, "Invalid review decision.")
            return redirect("manager-correction-review")

        with transaction.atomic():
            correction = get_object_or_404(
                corrections.select_for_update(),
                pk=correction_id,
            )

            correction.status = (
                "MANAGER_APPROVED"
                if decision == "approve"
                else "MANAGER_REJECTED"
            )
            correction.manager_reviewed_by = request.user
            correction.manager_comment = comment
            correction.save(
                update_fields=[
                    "status",
                    "manager_reviewed_by",
                    "manager_comment",
                    "updated_at",
                ]
            )

        messages.success(
            request,
            f"Correction request #{correction.pk} "
            f"was {decision}d successfully."
        )
        return redirect("manager-correction-review")

    return render(
        request,
        "attendance/correction_review.html",
        {"corrections": corrections.order_by("created_at")},
    )



@login_required
@require_http_methods(["GET", "POST"])
def hr_correction_finalize(request):
    if not is_hr_user(request.user):
        return HttpResponseForbidden(
            "Only HR Admin can finalize corrections."
        )

    approved_corrections = AttendanceCorrection.objects.filter(
        status="MANAGER_APPROVED"
    ).select_related(
        "employee",
        "attendance_log",
        "manager_reviewed_by",
    ).order_by("created_at")

    if request.method == "POST":
        correction_id = request.POST.get("correction_id")

        with transaction.atomic():
            correction = get_object_or_404(
                AttendanceCorrection.objects.select_for_update(),
                pk=correction_id,
                status="MANAGER_APPROVED",
            )

            # Validate that the original punch belongs to this employee.
            attendance_log = correction.attendance_log

            if (
                attendance_log
                and attendance_log.employee_id != correction.employee_id
            ):
                messages.error(
                    request,
                    "The attendance log does not belong to this employee."
                )
                return redirect("hr-correction-finalize")

            if attendance_log is None:
                # A missing punch requires an active shift rule.
                shift_rule = ShiftRule.objects.filter(
                    is_active=True
                ).order_by("id").first()

                if shift_rule is None:
                    messages.error(
                        request,
                        "Create an active shift rule before adding a missing punch."
                    )
                    return redirect("hr-correction-finalize")

                attendance_log = AttendanceLog(
                    employee=correction.employee,
                    batch=None,
                    shift_rule=shift_rule,
                    device_location="HR correction",
                )

            attendance_log.punch_date = correction.correction_date
            attendance_log.punch_time = correction.requested_punch_time
            attendance_log.punch_type = correction.requested_punch_type

            # Recalculate lateness for IN punches.
            attendance_log.is_late = False
            attendance_log.delay_minutes = 0

            if (
                attendance_log.punch_type == "IN"
                and attendance_log.shift_rule
            ):
                scheduled_start = datetime.combine(
                    attendance_log.punch_date,
                    attendance_log.shift_rule.shift_start,
                )
                actual_start = datetime.combine(
                    attendance_log.punch_date,
                    attendance_log.punch_time,
                )
                allowed_start = scheduled_start + timedelta(
                    minutes=attendance_log.shift_rule.grace_minutes
                )

                if actual_start > allowed_start:
                    attendance_log.is_late = True
                    attendance_log.delay_minutes = int(
                        (actual_start - allowed_start).total_seconds() // 60
                    )

            attendance_log.save()

            correction.attendance_log = attendance_log
            correction.status = "FINALIZED"
            correction.finalized_by = request.user
            correction.hr_comment = (
                request.POST.get("hr_comment", "").strip()
            )
            correction.save(
                update_fields=[
                    "attendance_log",
                    "status",
                    "finalized_by",
                    "hr_comment",
                    "updated_at",
                ]
            )

        messages.success(
            request,
            f"Correction #{correction_id} finalized successfully."
        )
        return redirect("hr-correction-finalize")

    return render(
        request,
        "attendance/hr_correction_finalize.html",
        {"corrections": approved_corrections},
    )



@login_required
def manager_correction_review(request):
    # Only Managers and superusers can access this page.
    role = str(getattr(request.user, "role", "") or "")
    role = role.strip().upper().replace("-", "_").replace(" ", "_")

    if not (request.user.is_superuser or role == "MANAGER"):
        messages.error(request, "Only Managers can review corrections.")
        return redirect("home")  # Replace if your home URL has another name.

    # Find the Employee profile linked to the logged-in Manager.
    manager_employee = Employee.objects.filter(
        user=request.user
    ).first()

    if not manager_employee and not request.user.is_superuser:
        messages.error(
            request,
            "Your Manager account is not linked to an Employee profile."
        )
        return redirect("home")

    # Managers see requests belonging to their assigned employees.
    pending_requests = AttendanceCorrection.objects.filter(
        status="PENDING"
    ).select_related("employee")

    if not request.user.is_superuser:
        pending_requests = pending_requests.filter(
            employee__manager=manager_employee
        )

    pending_requests = pending_requests.order_by("-id")

    return render(
        request,
        "attendance/manager_correction_review.html",
        {"corrections": pending_requests},
    )


@login_required
@require_POST
def manager_review_correction_action(request, correction_id):
    role = str(getattr(request.user, "role", "") or "")
    role = role.strip().upper().replace("-", "_").replace(" ", "_")

    if not (request.user.is_superuser or role == "MANAGER"):
        messages.error(request, "Only Managers can review corrections.")
        return redirect("home")

    manager_employee = Employee.objects.filter(
        user=request.user
    ).first()

    if not manager_employee and not request.user.is_superuser:
        messages.error(
            request,
            "Your Manager account is not linked to an Employee profile."
        )
        return redirect("home")

    # Restrict the request to pending items assigned to this Manager.
    corrections = AttendanceCorrection.objects.filter(status="PENDING")

    if not request.user.is_superuser:
        corrections = corrections.filter(
            employee__manager=manager_employee
        )

    correction = get_object_or_404(corrections, pk=correction_id)

    decision = request.POST.get("decision", "").strip().upper()
    manager_comment = request.POST.get("manager_comment", "").strip()

    if decision not in ("APPROVE", "REJECT"):
        messages.error(request, "Invalid review action.")
        return redirect("manager-correction-review")

    correction.status = (
        "MANAGER_APPROVED"
        if decision == "APPROVE"
        else "MANAGER_REJECTED"
    )
    correction.manager_reviewed_by = request.user
    correction.manager_comment = manager_comment
    correction.save(
        update_fields=[
            "status",
            "manager_reviewed_by",
            "manager_comment",
        ]
    )

    messages.success(
        request,
        "Correction approved."
        if decision == "APPROVE"
        else "Correction rejected.",
    )

    return redirect("manager-correction-review")
