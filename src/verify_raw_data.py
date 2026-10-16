
# File: src/verify_raw_data.py

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

expected_files = [
    "employees.csv",
    "departments.csv",
    "jobs.csv",
    "salaries.csv",
    "attendance.csv",
    "leaves.csv",
    "performance.csv",
]

print("RAW DATA VERIFICATION")
print("-" * 60)

for filename in expected_files:
    path = RAW_DIR / filename

    if not path.exists():
        print(f"FAIL: Missing {filename}")
        continue

    df = pd.read_csv(path)

    print(f"\nFile: {filename}")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")
    print(f"Column names: {list(df.columns)}")
    print(df.head(3).to_string(index=False))





# Load the relevant datasets

employees = pd.read_csv(RAW_DIR / "employees.csv")
departments = pd.read_csv(RAW_DIR / "departments.csv")
jobs = pd.read_csv(RAW_DIR / "jobs.csv")
salaries = pd.read_csv(RAW_DIR / "salaries.csv")
attendance = pd.read_csv(RAW_DIR / "attendance.csv")
leaves = pd.read_csv(RAW_DIR / "leaves.csv")
performance = pd.read_csv(RAW_DIR / "performance.csv")

print("\nRELATIONSHIP CHECKS")
print("-" * 60)

print(
    "Employees with unknown departments:",
    (~employees["department_id"].isin(
        departments["department_id"]
    )).sum(),
)

print(
    "Employees with unknown jobs:",
    (~employees["job_id"].isin(jobs["job_id"])).sum(),
)

employee_ids = set(employees["employee_id"])

for name, df in {
    "salaries": salaries,
    "attendance": attendance,
    "leaves": leaves,
    "performance": performance,
}.items():
    invalid = (~df["employee_id"].isin(employee_ids)).sum()
    print(f"{name} with unknown employees: {invalid}")

print("\nVerification finished.")
