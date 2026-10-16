
# File: src/validate_data.py

from pathlib import Path
import sys

import pandas as pd


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_DIR = DATA_DIR / "validation_reports"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_COLUMNS = {
    "employees": [
        "employee_id", "first_name", "last_name", "email",
        "department_id", "job_id", "hire_date",
        "termination_date", "employment_type",
    ],
    "departments": [
        "department_id", "department_name", "location",
    ],
    "jobs": [
        "job_id", "job_title", "department_id", "job_level",
    ],
    "salaries": [
        "salary_id", "employee_id", "salary_amount", "effective_date",
    ],
    "attendance": [
        "attendance_id", "employee_id", "attendance_date", "status",
    ],
    "leaves": [
        "leave_id", "employee_id", "start_date", "end_date",
        "leave_type", "status",
    ],
    "performance": [
        "performance_id", "employee_id", "review_date",
        "rating", "review_category",
    ],
}

PRIMARY_KEYS = {
    "employees": "employee_id",
    "departments": "department_id",
    "jobs": "job_id",
    "salaries": "salary_id",
    "attendance": "attendance_id",
    "leaves": "leave_id",
    "performance": "performance_id",
}

DATE_COLUMNS = {
    "employees": ["hire_date", "termination_date"],
    "salaries": ["effective_date"],
    "attendance": ["attendance_date"],
    "leaves": ["start_date", "end_date"],
    "performance": ["review_date"],
}

VALID_ATTENDANCE = {
    "Present", "Absent", "Work From Home", "Half Day",
}
VALID_LEAVE_TYPES = {"Annual", "Sick", "Casual", "Unpaid"}
VALID_LEAVE_STATUSES = {"Approved", "Pending", "Rejected"}

results = []
data = {}


# --------------------------------------------------
# 2. Validation helper
# --------------------------------------------------

def check(name, passed, details):
    status = "PASS" if passed else "FAIL"

    results.append({
        "check": name,
        "status": status,
        "details": str(details),
    })

    print(f"[{status}] {name}: {details}")


def foreign_key_check(child, child_column, parent, parent_column):
    invalid = (
        child[child_column].isna()
        | ~child[child_column].isin(parent[parent_column])
    )
    return int(invalid.sum())


# --------------------------------------------------
# 3. Load and check file structure
# --------------------------------------------------

print("=" * 70)
print("HR DATA VALIDATION")
print("=" * 70)

for name, required_columns in REQUIRED_COLUMNS.items():
    path = DATA_DIR / f"{name}.csv"

    if not path.exists():
        check(f"{name}: file exists", False, f"Missing file: {path}")
        continue

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        check(f"{name}: file readable", False, exc)
        continue

    data[name] = df

    missing_columns = sorted(
        set(required_columns) - set(df.columns)
    )

    check(
        f"{name}: required columns",
        not missing_columns,
        f"Missing columns: {missing_columns}"
        if missing_columns else "All required columns exist",
    )

    if missing_columns:
        continue

    check(
        f"{name}: file not empty",
        not df.empty,
        f"{len(df):,} rows",
    )

    check(
        f"{name}: no exact duplicate rows",
        int(df.duplicated().sum()) == 0,
        f"{int(df.duplicated().sum())} duplicate rows",
    )

    key = PRIMARY_KEYS[name]
    duplicate_keys = int(df[key].duplicated().sum())

    check(
        f"{name}: unique {key}",
        duplicate_keys == 0,
        f"{duplicate_keys} duplicate keys",
    )

    for column in DATE_COLUMNS.get(name, []):
        parsed = pd.to_datetime(df[column], errors="coerce")
        invalid_dates = int(
            (df[column].notna() & parsed.isna()).sum()
        )

        check(
            f"{name}: valid {column}",
            invalid_dates == 0,
            f"{invalid_dates} invalid date values",
        )


# Stop safely if files are missing or required columns are absent.
required_dataset_names = set(REQUIRED_COLUMNS)
if not required_dataset_names.issubset(data):
    print("\nValidation stopped: some datasets could not be loaded.")
    pd.DataFrame(results).to_csv(
        REPORT_DIR / "validation_report.csv", index=False
    )
    sys.exit(1)

for name, columns in REQUIRED_COLUMNS.items():
    if not set(columns).issubset(data[name].columns):
        print("\nValidation stopped: required columns are missing.")
        pd.DataFrame(results).to_csv(
            REPORT_DIR / "validation_report.csv", index=False
        )
        sys.exit(1)


# --------------------------------------------------
# 4. Required fields
# --------------------------------------------------

required_non_null = {
    "employees": [
        "employee_id", "first_name", "last_name", "email",
        "department_id", "job_id", "hire_date",
    ],
    "departments": ["department_id", "department_name"],
    "jobs": ["job_id", "job_title", "department_id"],
    "salaries": [
        "salary_id", "employee_id", "salary_amount", "effective_date",
    ],
    "attendance": [
        "attendance_id", "employee_id", "attendance_date", "status",
    ],
    "leaves": [
        "leave_id", "employee_id", "start_date", "end_date",
        "leave_type", "status",
    ],
    "performance": [
        "performance_id", "employee_id", "review_date",
    ],
}

for name, columns in required_non_null.items():
    missing_count = int(data[name][columns].isna().sum().sum())

    check(
        f"{name}: required fields not null",
        missing_count == 0,
        f"{missing_count} missing required values",
    )


# --------------------------------------------------
# 5. Business rules
# --------------------------------------------------

employees = data["employees"]
departments = data["departments"]
jobs = data["jobs"]
salaries = data["salaries"]
attendance = data["attendance"]
leaves = data["leaves"]
performance = data["performance"]

# Employee email validity and uniqueness.
email_pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
invalid_emails = int(
    (~employees["email"].astype("string").str.match(
        email_pattern, na=False
    )).sum()
)

check(
    "employees: valid email format",
    invalid_emails == 0,
    f"{invalid_emails} invalid emails",
)

duplicate_emails = int(
    employees["email"].str.lower().duplicated().sum()
)

check(
    "employees: unique emails",
    duplicate_emails == 0,
    f"{duplicate_emails} duplicate emails",
)

hire_dates = pd.to_datetime(employees["hire_date"], errors="coerce")
termination_dates = pd.to_datetime(
    employees["termination_date"], errors="coerce"
)

invalid_employment_dates = int(
    (
        termination_dates.notna()
        & (termination_dates < hire_dates)
    ).sum()
)

check(
    "employees: termination not before hire",
    invalid_employment_dates == 0,
    f"{invalid_employment_dates} invalid date ranges",
)

valid_employment_types = {"Full-Time", "Contract", "Part-Time"}
invalid_employment_types = int(
    (~employees["employment_type"].isin(valid_employment_types)).sum()
)

check(
    "employees: valid employment types",
    invalid_employment_types == 0,
    f"{invalid_employment_types} invalid values",
)

# A job must belong to the employee's assigned department.
employee_job_departments = employees.merge(
    jobs[["job_id", "department_id"]],
    on="job_id",
    how="left",
    suffixes=("_employee", "_job"),
)

mismatched_departments = int(
    (
        employee_job_departments["department_id_employee"]
        != employee_job_departments["department_id_job"]
    ).sum()
)

check(
    "employees: job belongs to assigned department",
    mismatched_departments == 0,
    f"{mismatched_departments} mismatches",
)

# Salaries.
non_positive_salary = int(
    (pd.to_numeric(salaries["salary_amount"], errors="coerce") <= 0).sum()
)

check(
    "salaries: positive amounts",
    non_positive_salary == 0,
    f"{non_positive_salary} non-positive amounts",
)

# Attendance.
invalid_attendance = int(
    (~attendance["status"].isin(VALID_ATTENDANCE)).sum()
)

check(
    "attendance: allowed statuses",
    invalid_attendance == 0,
    f"{invalid_attendance} invalid statuses",
)

duplicate_attendance_events = int(
    attendance.duplicated(
        subset=["employee_id", "attendance_date"]
    ).sum()
)

check(
    "attendance: one record per employee/date",
    duplicate_attendance_events == 0,
    f"{duplicate_attendance_events} duplicate events",
)

# Leaves.
leave_start = pd.to_datetime(leaves["start_date"], errors="coerce")
leave_end = pd.to_datetime(leaves["end_date"], errors="coerce")

invalid_leave_ranges = int((leave_end < leave_start).sum())

check(
    "leaves: end date on/after start date",
    invalid_leave_ranges == 0,
    f"{invalid_leave_ranges} invalid date ranges",
)

invalid_leave_types = int(
    (~leaves["leave_type"].isin(VALID_LEAVE_TYPES)).sum()
)
invalid_leave_statuses = int(
    (~leaves["status"].isin(VALID_LEAVE_STATUSES)).sum()
)

check(
    "leaves: allowed categories",
    invalid_leave_types == 0 and invalid_leave_statuses == 0,
    (
        f"{invalid_leave_types} invalid leave types; "
        f"{invalid_leave_statuses} invalid statuses"
    ),
)

# Performance ratings may be missing but present ratings must be 1-5.
ratings = pd.to_numeric(performance["rating"], errors="coerce")
invalid_rating_format = int(
    (performance["rating"].notna() & ratings.isna()).sum()
)
invalid_ratings = int(
    (ratings.notna() & ~ratings.between(1, 5)).sum()
)

check(
    "performance: ratings within 1-5",
    invalid_rating_format == 0 and invalid_ratings == 0,
    (
        f"{invalid_rating_format} non-numeric ratings; "
        f"{invalid_ratings} out-of-range ratings"
    ),
)


# --------------------------------------------------
# 6. Foreign-key checks
# --------------------------------------------------

relationships = [
    ("employees", "department_id", "departments", "department_id"),
    ("employees", "job_id", "jobs", "job_id"),
    ("jobs", "department_id", "departments", "department_id"),
    ("salaries", "employee_id", "employees", "employee_id"),
    ("attendance", "employee_id", "employees", "employee_id"),
    ("leaves", "employee_id", "employees", "employee_id"),
    ("performance", "employee_id", "employees", "employee_id"),
]

for child_name, child_col, parent_name, parent_col in relationships:
    invalid = foreign_key_check(
        data[child_name],
        child_col,
        data[parent_name],
        parent_col,
    )

    check(
        f"FK: {child_name}.{child_col} -> "
        f"{parent_name}.{parent_col}",
        invalid == 0,
        f"{invalid} invalid references",
    )


# --------------------------------------------------
# 7. Save report and return status
# --------------------------------------------------

report = pd.DataFrame(results)
report_path = REPORT_DIR / "validation_report.csv"
report.to_csv(report_path, index=False)

passed = int((report["status"] == "PASS").sum())
failed = int((report["status"] == "FAIL").sum())

print("\n" + "=" * 70)
print("VALIDATION SUMMARY")
print("=" * 70)
print(f"Total checks: {len(report)}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Report: {report_path}")

if failed:
    print("\nValidation FAILED. Review the FAIL results above.")
    sys.exit(1)

print("\nAll validation checks passed.")
