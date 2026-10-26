# scripts/attendance_processor.py

import argparse
import logging
import re
import time

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# 1. Paths and configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_INPUT = BASE_DIR / "sample_data" / "attendance_input.csv"
REPORT_DIR = BASE_DIR / "reports"

REQUIRED_COLUMNS = {
    "employee_code",
    "employee_name",
    "department",
    "punch_date",
    "punch_time",
    "device_location",
    "punch_type",
    "shift_start",
    "shift_end",
    "leave_type",
    "manager_code",
    "remarks",
}

# Immutable set of standard shift rules.
# Each item contains (shift_start, shift_end, grace_minutes).
SHIFT_RULES = frozenset({
    ("09:00", "18:00", 15),
    ("10:00", "19:00", 15),
})

EMPLOYEE_CODE_PATTERN = re.compile(r"^EMP\d{3,6}$")
MANAGER_CODE_PATTERN = re.compile(r"^MGR\d{3,6}$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


# --------------------------------------------------
# 2. Custom exception
# --------------------------------------------------

class InvalidAttendanceRow(Exception):
    """Raised when an attendance record contains invalid data."""


# --------------------------------------------------
# 3. Decorator for timing and logging
# --------------------------------------------------

def log_execution(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        logging.info("Started: %s", func.__name__)

        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start_time
            logging.info(
                "Finished: %s in %.3f seconds",
                func.__name__,
                elapsed,
            )

    return wrapper


# --------------------------------------------------
# 4. Read CSV or Excel
# --------------------------------------------------

def read_attendance_file(file_path):
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Attendance file not found: {file_path}"
        )

    if file_path.suffix.lower() != ".csv":
        raise ValueError(
            "Unsupported file format. Please upload a CSV file."
        )

    dataframe = pd.read_csv(
        file_path,
        dtype=str,
        keep_default_na=False,
    )

    if dataframe.empty:
        raise ValueError("The uploaded attendance CSV is empty.")

    dataframe.columns = [
        str(column).strip().lower()
        for column in dataframe.columns
    ]

    if len(set(dataframe.columns)) != len(dataframe.columns):
        raise ValueError(
            "Duplicate column names found after normalization."
        )

    missing_columns = REQUIRED_COLUMNS - set(dataframe.columns)

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    return dataframe


# --------------------------------------------------
# 5. String normalization
# --------------------------------------------------

def normalize_text(value):
    return str(value).strip()


def normalize_department(value):
    # String methods and slicing are used here.
    value = normalize_text(value)
    value = " ".join(value.split())

    if not value:
        return "Unknown"

    return value[:1].upper() + value[1:].lower()


def normalize_punch_type(value):
    value = normalize_text(value).upper()

    # Support common variations.
    if value in {"IN", "ENTRY", "CHECK-IN", "CHECKIN"}:
        return "IN"

    if value in {"OUT", "EXIT", "CHECK-OUT", "CHECKOUT"}:
        return "OUT"

    if value in {"LEAVE", "ON LEAVE"}:
        return "LEAVE"

    return value


def normalize_location(value):
    value = normalize_text(value)
    value = " ".join(value.split())

    if not value:
        return "Unknown"

    # Normalize the first character using slicing.
    return value[:1].upper() + value[1:].lower()


# --------------------------------------------------
# 6. Validation helpers
# --------------------------------------------------

def parse_date(value):
    value = normalize_text(value)

    if not DATE_PATTERN.fullmatch(value):
        raise InvalidAttendanceRow(
            "Invalid punch_date format; expected YYYY-MM-DD."
        )

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise InvalidAttendanceRow(
            "Invalid calendar date."
        ) from exc


def parse_time(value, field_name):
    value = normalize_text(value)

    if not TIME_PATTERN.fullmatch(value):
        raise InvalidAttendanceRow(
            f"Invalid {field_name} format; expected HH:MM."
        )

    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise InvalidAttendanceRow(
            f"Invalid time in {field_name}."
        ) from exc


def validate_and_normalize(row):
    """
    Validate a single row and return a normalized dictionary.
    Raise InvalidAttendanceRow if a required value is invalid.
    """

    record = {
        column: normalize_text(row.get(column, ""))
        for column in REQUIRED_COLUMNS
    }

    if not record["employee_code"]:
        raise InvalidAttendanceRow("Employee code is missing.")

    record["employee_code"] = record["employee_code"].upper()

    if not EMPLOYEE_CODE_PATTERN.fullmatch(
        record["employee_code"]
    ):
        raise InvalidAttendanceRow(
            "Employee code must match EMP followed by 3-6 digits."
        )

    manager_code = record["manager_code"].upper()

    if manager_code and not MANAGER_CODE_PATTERN.fullmatch(
        manager_code
    ):
        raise InvalidAttendanceRow(
            "Manager code must match MGR followed by 3-6 digits."
        )

    if not record["employee_name"]:
        raise InvalidAttendanceRow("Employee name is missing.")

    if not record["department"]:
        raise InvalidAttendanceRow("Department is missing.")

    if not record["device_location"]:
        record["device_location"] = "Unknown"

    punch_date = parse_date(record["punch_date"])
    punch_type = normalize_punch_type(record["punch_type"])

    if punch_type not in {"IN", "OUT", "LEAVE"}:
        raise InvalidAttendanceRow(
            "Punch type must be IN, OUT, or LEAVE."
        )

    shift_start = parse_time(
        record["shift_start"], "shift_start"
    )
    shift_end = parse_time(
        record["shift_end"], "shift_end"
    )

    if shift_start == shift_end:
        raise InvalidAttendanceRow(
            "Shift start and end cannot be identical."
        )

    if punch_type != "LEAVE":
        punch_time = parse_time(
            record["punch_time"], "punch_time"
        )
    else:
        # Leave rows do not represent a biometric punch.
        punch_time = None

    department = normalize_department(record["department"])
    location = normalize_location(record["device_location"])

    # Default grace period for shifts not in the standard rules.
    grace_minutes = 15

    shift_key = (
        shift_start.strftime("%H:%M"),
        shift_end.strftime("%H:%M"),
    )

    for start, end, grace in SHIFT_RULES:
        if shift_key == (start, end):
            grace_minutes = grace
            break

    return {
        **record,
        "employee_code": record["employee_code"],
        "manager_code": manager_code,
        "department": department,
        "device_location": location,
        "punch_type": punch_type,
        "punch_date": punch_date.isoformat(),
        "punch_time": (
            punch_time.strftime("%H:%M")
            if punch_time else ""
        ),
        "shift_start": shift_start.strftime("%H:%M"),
        "shift_end": shift_end.strftime("%H:%M"),
        "leave_type": record["leave_type"].upper(),
        "remarks": record["remarks"],
        "_date": punch_date,
        "_time": punch_time,
        "_shift_start": shift_start,
        "_shift_end": shift_end,
        "_grace_minutes": grace_minutes,
    }


# --------------------------------------------------
# 7. Recursive department hierarchy traversal
# --------------------------------------------------

def traverse_department_hierarchy(hierarchy, parent="ROOT"):
    """
    Recursively visit a nested dictionary of departments.

    Example:
    {
        "ROOT": {
            "IT": {"Backend": {}, "Frontend": {}},
            "HR": {}
        }
    }
    """

    visited = []

    def visit(node, parent_name):
        for department, children in node.items():
            visited.append({
                "department": department,
                "parent": parent_name,
            })

            if isinstance(children, dict):
                visit(children, department)

    if parent in hierarchy and isinstance(hierarchy[parent], dict):
        visit(hierarchy[parent], parent)
    else:
        visit(hierarchy, parent)

    return visited


# --------------------------------------------------
# 8. Main attendance processor
# --------------------------------------------------

@log_execution
def process_attendance_file(file_path=DEFAULT_INPUT):
    dataframe = read_attendance_file(file_path)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    valid_records = []
    anomaly_records = []
    correction_records = []

    # Set for exact duplicate-punch detection.
    seen_punches = set()

    # Dictionary-based summary counters.
    summary_counters = defaultdict(Counter)

    # Iterating row by row avoids requiring vectorized
    # operations for every validation rule.
    record_iterator = iter(dataframe.to_dict("records"))

    for row_number, row in enumerate(record_iterator, start=2):
        try:
            record = validate_and_normalize(row)

            employee_code = record["employee_code"]
            punch_date = record["punch_date"]
            punch_type = record["punch_type"]

            if punch_type == "LEAVE":
                summary_counters[
                    (employee_code, punch_date)
                ]["leave_rows"] += 1

                valid_records.append(record)
                continue

            # The duplicate key intentionally excludes remarks.
            duplicate_key = (
                employee_code,
                punch_date,
                record["punch_time"],
                punch_type,
                record["device_location"],
            )

            if duplicate_key in seen_punches:
                anomaly_records.append({
                    "row_number": row_number,
                    "employee_code": employee_code,
                    "employee_name": record["employee_name"],
                    "punch_date": punch_date,
                    "punch_time": record["punch_time"],
                    "anomaly_type": "DUPLICATE_PUNCH",
                    "details": "Duplicate biometric punch detected.",
                })

                correction_records.append({
                    "row_number": row_number,
                    "employee_code": employee_code,
                    "employee_name": record["employee_name"],
                    "punch_date": punch_date,
                    "issue": "DUPLICATE_PUNCH",
                    "details": "Verify and remove duplicate punch.",
                })

                summary_counters[
                    (employee_code, punch_date)
                ]["duplicate_count"] += 1

                continue

            seen_punches.add(duplicate_key)

            # Calculate late arrival.
            if punch_type == "IN":
                actual_minutes = (
                    record["_time"].hour * 60
                    + record["_time"].minute
                )

                shift_minutes = (
                    record["_shift_start"].hour * 60
                    + record["_shift_start"].minute
                )

                delay = max(0, actual_minutes - shift_minutes)

                record["delay_minutes"] = delay
                record["is_late"] = (
                    delay > record["_grace_minutes"]
                )

                if record["is_late"]:
                    anomaly_records.append({
                        "row_number": row_number,
                        "employee_code": employee_code,
                        "employee_name": record["employee_name"],
                        "punch_date": punch_date,
                        "punch_time": record["punch_time"],
                        "anomaly_type": "LATE_ARRIVAL",
                        "details": (
                            f"{delay} minutes after shift start; "
                            f"grace period is "
                            f"{record['_grace_minutes']} minutes."
                        ),
                    })

                    summary_counters[
                        (employee_code, punch_date)
                    ]["late_count"] += 1

            valid_records.append(record)

            summary_counters[
                (employee_code, punch_date)
            ]["punch_count"] += 1

        except InvalidAttendanceRow as exc:
            anomaly_records.append({
                "row_number": row_number,
                "employee_code": row.get("employee_code", ""),
                "employee_name": row.get("employee_name", ""),
                "punch_date": row.get("punch_date", ""),
                "punch_time": row.get("punch_time", ""),
                "anomaly_type": "INVALID_ROW",
                "details": str(exc),
            })

            correction_records.append({
                "row_number": row_number,
                "employee_code": row.get("employee_code", ""),
                "employee_name": row.get("employee_name", ""),
                "punch_date": row.get("punch_date", ""),
                "issue": "INVALID_ROW",
                "details": str(exc),
            })

    # Group accepted records by employee and date.
    daily_groups = defaultdict(list)

    for record in valid_records:
        daily_groups[
            (record["employee_code"], record["punch_date"])
        ].append(record)

    daily_summaries = []

    for (employee_code, punch_date), records in daily_groups.items():
        punches_in = [
            record for record in records
            if record["punch_type"] == "IN"
        ]

        punches_out = [
            record for record in records
            if record["punch_type"] == "OUT"
        ]

        first_in = min(
            (record["_time"] for record in punches_in),
            default=None,
        )

        last_out = max(
            (record["_time"] for record in punches_out),
            default=None,
        )

        missing_punches = []

        if punches_in and not punches_out:
            missing_punches.append("OUT")
        elif punches_out and not punches_in:
            missing_punches.append("IN")

        working_hours = ""

        if first_in and last_out:
            start_minutes = first_in.hour * 60 + first_in.minute
            end_minutes = last_out.hour * 60 + last_out.minute

            # Basic same-day shift calculation.
            if end_minutes >= start_minutes:
                working_hours = round(
                    (end_minutes - start_minutes) / 60, 2
                )

        employee_name = records[0]["employee_name"]
        department = records[0]["department"]

        daily_summaries.append({
            "employee_code": employee_code,
            "employee_name": employee_name,
            "department": department,
            "punch_date": punch_date,
            "first_in": first_in.strftime("%H:%M") if first_in else "",
            "last_out": last_out.strftime("%H:%M") if last_out else "",
            "punch_count": len(punches_in) + len(punches_out),
            "late_count": summary_counters[
                (employee_code, punch_date)
            ]["late_count"],
            "duplicate_count": summary_counters[
                (employee_code, punch_date)
            ]["duplicate_count"],
            "leave_rows": summary_counters[
                (employee_code, punch_date)
            ]["leave_rows"],
            "working_hours": working_hours,
            "missing_punches": ", ".join(missing_punches),
        })

        if missing_punches:
            details = (
                "Missing " + ", ".join(missing_punches) + " punch."
            )

            anomaly_records.append({
                "row_number": "",
                "employee_code": employee_code,
                "employee_name": employee_name,
                "punch_date": punch_date,
                "punch_time": "",
                "anomaly_type": "MISSING_PUNCH",
                "details": details,
            })

            correction_records.append({
                "row_number": "",
                "employee_code": employee_code,
                "employee_name": employee_name,
                "punch_date": punch_date,
                "issue": "MISSING_PUNCH",
                "details": details,
            })

    # Required comprehension-based filtered summary.
    late_employee_summaries = [
        summary
        for summary in daily_summaries
        if summary["late_count"] > 0
    ]

    # Write all required output reports.
    pd.DataFrame(daily_summaries).to_csv(
        REPORT_DIR / "daily_summary.csv",
        index=False,
    )

    pd.DataFrame(
        anomaly_records,
        columns=[
            "row_number",
            "employee_code",
            "employee_name",
            "punch_date",
            "punch_time",
            "anomaly_type",
            "details",
        ],
    ).to_csv(
        REPORT_DIR / "anomaly_report.csv",
        index=False,
    )

    pd.DataFrame(
        correction_records,
        columns=[
            "row_number",
            "employee_code",
            "employee_name",
            "punch_date",
            "issue",
            "details",
        ],
    ).to_csv(
        REPORT_DIR / "correction_required.csv",
        index=False,
    )

    # Recursion demonstration using a nested hierarchy.
    department_hierarchy = {
        "ROOT": {
            department: {}
            for department in {
                record["department"] for record in valid_records
            }
        }
    }

    hierarchy_rows = traverse_department_hierarchy(
        department_hierarchy
    )

    logging.info("Valid punches processed: %s", len(valid_records))
    logging.info("Late employee-days: %s", len(late_employee_summaries))
    logging.info("Departments traversed: %s", len(hierarchy_rows))
    logging.info("Reports saved to: %s", REPORT_DIR)

    return {
        "total_rows": len(dataframe),
        "valid_records": len(valid_records),
        "late_employee_days": len(late_employee_summaries),
        "anomalies": len(anomaly_records),
        "corrections_required": len(correction_records),
        "reports_directory": str(REPORT_DIR),
        "records": valid_records,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process attendance CSV or Excel files."
    )

    parser.add_argument(
        "file",
        nargs="?",
        default=str(DEFAULT_INPUT),
        help="Path to the input CSV file",
    )

    args = parser.parse_args()

    try:
        result = process_attendance_file(args.file)
        print("\nProcessing completed.")
        print(result)

    except (FileNotFoundError, ValueError, pd.errors.ParserError) as exc:
        logging.error("Attendance processing failed: %s", exc)
        raise SystemExit(1) from exc