
from django.db.models import Q

from rest_framework import generics
from rest_framework.permissions import BasePermission, IsAuthenticated

from .models import Employee, AttendanceImportBatch
from .serializers import (
    EmployeeSerializer,
    AttendanceImportBatchSerializer,
)


def get_user_role(user):
    """
    Normalize the user's role for permission checks.
    Adjust this if your project stores roles differently.
    """
    return str(getattr(user, "role", "")).upper().replace(" ", "_")


class IsHROrManager(BasePermission):
    """
    Allow HR Admins, Managers, and Django superusers.
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        role = get_user_role(user)

        return (
            user.is_superuser
            or role in {"HR", "HR_ADMIN", "ADMIN", "MANAGER"}
        )


class EmployeeListAPI(generics.ListAPIView):
    """
    GET /api/attendance/employees/

    Optional filters:
    ?search=EMP001
    ?active=true
    """

    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated, IsHROrManager]

    def get_queryset(self):
        queryset = Employee.objects.select_related(
            "department",
            "manager",
        ).order_by("employee_code")

        search = self.request.query_params.get("search", "").strip()
        active = self.request.query_params.get("active", "").lower()

        if search:
            queryset = queryset.filter(
                Q(employee_code__icontains=search)
                | Q(name__icontains=search)
                | Q(email__icontains=search)
            )

        if active in {"true", "false"}:
            queryset = queryset.filter(active=(active == "true"))

        return queryset


class AttendanceImportBatchListAPI(generics.ListAPIView):
    """
    GET /api/attendance/import-batches/

    Optional filter:
    ?status=COMPLETED
    """

    serializer_class = AttendanceImportBatchSerializer
    permission_classes = [IsAuthenticated, IsHROrManager]

    def get_queryset(self):
        queryset = AttendanceImportBatch.objects.select_related(
            "uploaded_by"
        ).order_by("-uploaded_at")

        status = self.request.query_params.get("status", "").upper()

        allowed_statuses = {
            "PENDING",
            "PROCESSING",
            "COMPLETED",
            "FAILED",
        }

        if status:
            if status not in allowed_statuses:
                return queryset.none()

            queryset = queryset.filter(status=status)

        return queryset
