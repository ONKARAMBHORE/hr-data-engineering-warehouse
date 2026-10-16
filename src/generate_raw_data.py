
# File: src/generate_raw_data.py

from pathlib import Path

import numpy as np
import pandas as pd


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

RNG = np.random.default_rng(42)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

RAW_DIR.mkdir(parents=True, exist_ok=True)

START_DATE = pd.Timestamp("2025-01-01")
END_DATE = pd.Timestamp("2025-12-31")

NUMBER_OF_EMPLOYEES = 1000


def random_dates(start, end, size):
    """Generate random dates between start and end."""
    days = (end - start).days
    offsets = RNG.integers(0, days + 1, size=size)

    return start + pd.to_timedelta(offsets, unit="D")


# --------------------------------------------------
# 2. Departments
# --------------------------------------------------

departments = pd.DataFrame(
    [
        (1, "Engineering", "Pune"),
        (2, "Human Resources", "Pune"),
        (3, "Finance", "Mumbai"),
        (4, "Sales", "Pune"),
        (5, "Marketing", "Mumbai"),
        (6, "Operations", "Hyderabad"),
        (7, "Data Analytics", "Hyderabad"),
        (8, "Customer Success", "Pune"),
    ],
    columns=[
        "department_id",
        "department_name",
        "location",
    ],
)


# --------------------------------------------------
# 3. Jobs
# --------------------------------------------------

job_records = [
    (101, "Software Engineer", 1, "L2"),
    (102, "Senior Software Engineer", 1, "L3"),
    (103, "Engineering Manager", 1, "L4"),
    (201, "HR Executive", 2, "L1"),
    (202, "HR Manager", 2, "L3"),
    (301, "Accountant", 3, "L2"),
    (302, "Finance Manager", 3, "L3"),
    (401, "Sales Executive", 4, "L1"),
    (402, "Sales Manager", 4, "L3"),
    (501, "Marketing Executive", 5, "L1"),
    (601, "Operations Analyst", 6, "L2"),
    (701, "Data Analyst", 7, "L2"),
    (702, "Data Engineer", 7, "L2"),
    (703, "Data Science Manager", 7, "L4"),
    (801, "Customer Success Executive", 8, "L1"),
]

jobs = pd.DataFrame(
    job_records,
    columns=[
        "job_id",
        "job_title",
        "department_id",
        "job_level",
    ],
)


# --------------------------------------------------
# 4. Employees
# --------------------------------------------------

first_names = [
    "Aarav", "Vivaan", "Aditya", "Arjun", "Ishaan",
    "Riya", "Ananya", "Diya", "Priya", "Sneha",
    "Rahul", "Rohan", "Neha", "Pooja", "Amit",
    "Karan", "Meera", "Sahil", "Kavya", "Nikhil",
]

last_names = [
    "Patil", "Sharma", "Verma", "Shah", "Joshi",
    "Kulkarni", "Deshmukh", "Pawar", "Singh", "Gupta",
    "More", "Jadhav", "Kadam", "Khan", "Chavan",
]

employee_ids = np.arange(1001, 1001 + NUMBER_OF_EMPLOYEES)

employee_departments = RNG.choice(
    departments["department_id"].to_numpy(),
    size=NUMBER_OF_EMPLOYEES,
)

employee_job_ids = []

for department_id in employee_departments:
    eligible_jobs = jobs.loc[
        jobs["department_id"] == department_id,
        "job_id",
    ].to_numpy()

    employee_job_ids.append(RNG.choice(eligible_jobs))

hire_dates = random_dates(
    pd.Timestamp("2018-01-01"),
    END_DATE,
    NUMBER_OF_EMPLOYEES,
)

termination_dates = []

for hire_date in hire_dates:
    if RNG.random() < 0.08:
        termination_date = random_dates(
            hire_date,
            END_DATE,
            1,
        )[0]
    else:
        termination_date = pd.NaT

    termination_dates.append(termination_date)

employees = pd.DataFrame(
    {
        "employee_id": employee_ids,
        "first_name": RNG.choice(first_names, NUMBER_OF_EMPLOYEES),
        "last_name": RNG.choice(last_names, NUMBER_OF_EMPLOYEES),
        "email": [
            f"employee{i}@company.com"
            for i in employee_ids
        ],
        "department_id": employee_departments,
        "job_id": employee_job_ids,
        "hire_date": hire_dates,
        "termination_date": termination_dates,
        "employment_type": RNG.choice(
            ["Full-Time", "Contract", "Part-Time"],
            NUMBER_OF_EMPLOYEES,
            p=[0.80, 0.15, 0.05],
        ),
    }
)

# Employees cannot terminate before they join.
employees.loc[
    employees["termination_date"].notna()
    & (
        employees["termination_date"]
        < employees["hire_date"]
    ),
    "termination_date",
] = employees["hire_date"]


# --------------------------------------------------
# 5. Salary history
# --------------------------------------------------

salary_records = []
salary_id = 1

for employee in employees.itertuples(index=False):
    number_of_revisions = RNG.choice([1, 2, 3], p=[0.50, 0.35, 0.15])

    dates = pd.to_datetime(
        random_dates(
            employee.hire_date,
            END_DATE,
            number_of_revisions,
        )
    )

    dates = sorted(set(dates))

    # Ensure every employee has at least one salary record.
    if not dates:
        dates = [employee.hire_date]

    salary_amount = int(RNG.integers(25000, 120001))

    for index, effective_date in enumerate(dates):
        if index > 0:
            salary_amount = int(
                salary_amount * RNG.uniform(1.03, 1.15)
            )

        salary_records.append(
            (
                salary_id,
                employee.employee_id,
                salary_amount,
                effective_date,
            )
        )

        salary_id += 1

salaries = pd.DataFrame(
    salary_records,
    columns=[
        "salary_id",
        "employee_id",
        "salary_amount",
        "effective_date",
    ],
)


# --------------------------------------------------
# 6. Attendance
# --------------------------------------------------

working_dates = pd.bdate_range(
    start="2025-01-01",
    end="2025-03-31",
)

attendance_records = []
attendance_id = 1

for employee in employees.itertuples(index=False):
    for attendance_date in working_dates:
        if attendance_date < employee.hire_date:
            continue

        if pd.notna(employee.termination_date):
            if attendance_date > employee.termination_date:
                continue

        status = RNG.choice(
            ["Present", "Absent", "Work From Home", "Half Day"],
            p=[0.78, 0.06, 0.12, 0.04],
        )

        attendance_records.append(
            (
                attendance_id,
                employee.employee_id,
                attendance_date,
                status,
            )
        )

        attendance_id += 1

attendance = pd.DataFrame(
    attendance_records,
    columns=[
        "attendance_id",
        "employee_id",
        "attendance_date",
        "status",
    ],
)


# --------------------------------------------------
# 7. Leaves
# --------------------------------------------------

leave_records = []
leave_id = 1

leave_types = ["Annual", "Sick", "Casual", "Unpaid"]
leave_statuses = ["Approved", "Pending", "Rejected"]

for employee in employees.itertuples(index=False):
    number_of_leaves = int(RNG.integers(0, 4))

    for _ in range(number_of_leaves):
        start_date = random_dates(
            START_DATE,
            END_DATE - pd.Timedelta(days=5),
            1,
        )[0]

        duration = int(RNG.integers(1, 6))
        end_date = start_date + pd.Timedelta(days=duration - 1)

        if start_date < employee.hire_date:
            continue

        if (
            pd.notna(employee.termination_date)
            and start_date > employee.termination_date
        ):
            continue

        leave_records.append(
            (
                leave_id,
                employee.employee_id,
                start_date,
                end_date,
                RNG.choice(leave_types),
                RNG.choice(
                    leave_statuses,
                    p=[0.70, 0.20, 0.10],
                ),
            )
        )

        leave_id += 1

leaves = pd.DataFrame(
    leave_records,
    columns=[
        "leave_id",
        "employee_id",
        "start_date",
        "end_date",
        "leave_type",
        "status",
    ],
)


# --------------------------------------------------
# 8. Performance reviews
# --------------------------------------------------

performance_records = []
performance_id = 1

review_dates = pd.to_datetime(
    ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"]
)

for employee in employees.itertuples(index=False):
    for review_date in review_dates:
        if review_date < employee.hire_date:
            continue

        if (
            pd.notna(employee.termination_date)
            and review_date > employee.termination_date
        ):
            continue

        if RNG.random() < 0.65:
            performance_records.append(
                (
                    performance_id,
                    employee.employee_id,
                    review_date,
                    int(RNG.integers(1, 6)),
                    RNG.choice(
                        ["Needs Improvement", "Meets Expectations",
                         "Exceeds Expectations"]
                    ),
                )
            )

            performance_id += 1

performance = pd.DataFrame(
    performance_records,
    columns=[
        "performance_id",
        "employee_id",
        "review_date",
        "rating",
        "review_category",
    ],
)


# --------------------------------------------------
# 9. Introduce controlled raw-data quality issues
# --------------------------------------------------
# These are intentional training examples for later
# exploration, cleaning, and validation phases.

# Missing employee emails
employees.loc[employees.index[:5], "email"] = np.nan

# Inconsistent attendance status values
if len(attendance) >= 10:
    attendance.loc[attendance.index[:10], "status"] = "present "

# Duplicate attendance rows
if len(attendance) >= 20:
    duplicates = attendance.iloc[:10].copy()
    attendance = pd.concat(
        [attendance, duplicates],
        ignore_index=True,
    )

# Invalid salary amounts
if len(salaries) >= 3:
    salaries.loc[salaries.index[:3], "salary_amount"] = -1000

# Missing performance ratings
if len(performance) >= 5:
    performance.loc[performance.index[:5], "rating"] = np.nan


# --------------------------------------------------
# 10. Save raw datasets
# --------------------------------------------------

datasets = {
    "employees": employees,
    "departments": departments,
    "jobs": jobs,
    "salaries": salaries,
    "attendance": attendance,
    "leaves": leaves,
    "performance": performance,
}

for name, dataframe in datasets.items():
    file_path = RAW_DIR / f"{name}.csv"

    dataframe.to_csv(
        file_path,
        index=False,
        date_format="%Y-%m-%d",
    )

    print(
        f"Created: {file_path.name:<18}"
        f" Rows: {len(dataframe):>6,}"
        f" Columns: {len(dataframe.columns):>2}"
    )

print("\nAll raw HR datasets generated successfully.")
print(f"Output directory: {RAW_DIR}")
