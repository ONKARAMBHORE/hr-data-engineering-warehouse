
# File: src/verify_cleaned_data.py

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

FILES = [
    "employees",
    "departments",
    "jobs",
    "salaries",
    "attendance",
    "leaves",
    "performance",
]

print("CLEANED DATA VERIFICATION")
print("-" * 65)

data = {}

for name in FILES:
    raw = pd.read_csv(RAW_DIR / f"{name}.csv")
    clean = pd.read_csv(PROCESSED_DIR / f"{name}.csv")

    data[name] = clean

    print(f"\n{name}")
    print(f"Raw rows: {len(raw):,}")
    print(f"Cleaned rows: {len(clean):,}")
    print(f"Rows removed: {len(raw) - len(clean):,}")
    print(f"Exact duplicates: {clean.duplicated().sum()}")
    print(f"Missing values: {clean.isna().sum().sum()}")

    key = {
        "employees": "employee_id",
        "departments": "department_id",
        "jobs": "job_id",
        "salaries": "salary_id",
        "attendance": "attendance_id",
        "leaves": "leave_id",
        "performance": "performance_id",
    }[name]

    print(f"Duplicate {key}: {clean[key].duplicated().sum()}")


# --------------------------------------------------
# Business-rule checks
# --------------------------------------------------

print("\nBUSINESS-RULE CHECKS")
print("-" * 65)

print(
    "Non-positive salaries:",
    (data["salaries"]["salary_amount"] <= 0).sum(),
)

print(
    "Missing employee emails:",
    data["employees"]["email"].isna().sum(),
)

print(
    "Invalid leave date ranges:",
    (
        pd.to_datetime(data["leaves"]["end_date"])
        < pd.to_datetime(data["leaves"]["start_date"])
    ).sum(),
)

print(
    "Attendance status values:",
    sorted(data["attendance"]["status"].dropna().unique()),
)

# Check attendance business-key uniqueness.
print(
    "Duplicate employee/date attendance events:",
    data["attendance"].duplicated(
        subset=["employee_id", "attendance_date"]
    ).sum(),
)


# --------------------------------------------------
# Foreign-key checks
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

print("\nFOREIGN-KEY CHECKS")
print("-" * 65)

all_relationships_valid = True

for child_name, child_col, parent_name, parent_col in relationships:
    child = data[child_name]
    parent = data[parent_name]

    invalid = (
        child[child_col].isna()
        | ~child[child_col].isin(parent[parent_col])
    )

    invalid_count = int(invalid.sum())

    print(f"{child_name}.{child_col}: {invalid_count} invalid references")

    if invalid_count:
        all_relationships_valid = False


# --------------------------------------------------
# Final result
# --------------------------------------------------

if all_relationships_valid:
    print("\nForeign-key relationships are valid.")
else:
    print("\nWARNING: Some foreign-key violations remain.")

print("Verification completed.")
