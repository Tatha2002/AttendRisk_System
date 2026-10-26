from django import forms
from .models import AttendanceImportBatch, AttendanceCorrection


class AttendanceUploadForm(forms.ModelForm):
    class Meta:
        model = AttendanceImportBatch
        fields = ["uploaded_file"]

    def clean_uploaded_file(self):
        uploaded_file = self.cleaned_data["uploaded_file"]

        if not uploaded_file:
            raise forms.ValidationError("Please select a CSV file.")

        if not uploaded_file.name.lower().endswith(".csv"):
            raise forms.ValidationError(
                "Only CSV files are supported."
            )

        if uploaded_file.size == 0:
            raise forms.ValidationError(
                "The uploaded file is empty."
            )

        return uploaded_file


class AttendanceCorrectionForm(forms.ModelForm):
    class Meta:
        model = AttendanceCorrection
        fields = [
            "employee",
            "attendance_log",
            "correction_date",
            "requested_punch_time",
            "requested_punch_type",
            "reason",
            "supporting_document",
        ]

        widgets = {
            "correction_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "requested_punch_time": forms.TimeInput(
                attrs={"type": "time"}
            ),
            "reason": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()

        attendance_log = cleaned_data.get("attendance_log")
        employee = cleaned_data.get("employee")

        if (
            attendance_log
            and employee
            and attendance_log.employee_id != employee.id
        ):
            self.add_error(
                "attendance_log",
                "The attendance log must belong to the selected employee.",
            )

        return cleaned_data