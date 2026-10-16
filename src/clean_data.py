
# File: src/clean_data.py

from pathlib import Path

import pandas as pd


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_DIR = PROCESSED_DIR / "cleaning_reports"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

DATE_COLUMNS = {
    "employees": ["hire_date", "termination_date"],
    "salaries": ["effective_date"],
    "attendance": ["attendance_date"],
    "leaves": ["start_date", "end_date"],
    "performance": ["review_date"],
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

CATEGORICAL_COLUMNS = {
    "employees": ["employment_type"],
    "departments": ["department_name", "location"],
    "jobs": ["job_title", "job_level"],
    "attendance": ["status"],
    "leaves": ["leave_type", "status"],
    "performance": ["review_category"],
}


# --------------------------------------------------
# 2. Load raw datasets
# --------------------------------------------------

def load_datasets():
    datasets = {}

    for name in PRIMARY_KEYS:
        path = RAW_DIR / f"{name}.csv"

        if not path.exists():
            raise FileNotFoundError(
                f"Missing raw dataset: {path}"
            )

        df = pd.read_csv(path)

        for column in DATE_COLUMNS.get(name, []):
            df[column] = pd.to_datetime(
                df[column],
                errors="coerce",
            )

        datasets[name] = df

    return datasets


# --------------------------------------------------
# 3. Cleaning report helper
# --------------------------------------------------

cleaning_summary = []


def record_summary(
    dataset,
    step,
    rows_before,
    rows_after,
    details,
):
    cleaning_summary.append(
        {
            "dataset": dataset,
            "step": step,
            "rows_before": rows_before,
            "rows_after": rows_after,
            "rows_removed": rows_before - rows_after,
            "details": details,
        }
    )


# --------------------------------------------------
# 4. Standardize text
# --------------------------------------------------

def standardize_text(datasets):
    for name, df in datasets.items():
        for column in df.select_dtypes(
            include=["object", "string"]
        ).columns:
            df[column] = df[column].map(
                lambda value: (
                    value.strip()
                    if isinstance(value, str)
                    else value
                )
            )

        for column in CATEGORICAL_COLUMNS.get(name, []):
            df[column] = df[column].str.title()

        # Standardize email casing and surrounding spaces.
        if name == "employees":
            df["email"] = df["email"].str.lower()

    # Map attendance statuses to an explicit allowed vocabulary.
    attendance = datasets["attendance"]

    attendance_status_map = {
        "Present": "Present",
        "Absent": "Absent",
        "Work From Home": "Work From Home",
        "Half Day": "Half Day",
    }

    attendance["status"] = attendance["status"].map(
        attendance_status_map
    )

    return datasets


# --------------------------------------------------
# 5. Clean employees
# --------------------------------------------------

def clean_employees(df):
    before = len(df)

    # The synthetic generator uses this email convention.
    missing_email = (
        df["email"].isna()
        | df["email"].eq("")
    )

    df.loc[missing_email, "email"] = (
        "employee"
        + df.loc[missing_email, "employee_id"].astype("Int64").astype(str)
        + "@company.com"
    )

    # Invalid termination dates cannot precede hire dates.
    invalid_termination = (
        df["termination_date"].notna()
        & (
            df["termination_date"]
            < df["hire_date"]
        )
    )

    invalid_count = int(invalid_termination.sum())

    # Do not invent a termination date.
    df.loc[invalid_termination, "termination_date"] = pd.NaT

    # Employee identity fields must be present.
    df = df.dropna(
        subset=[
            "employee_id",
            "first_name",
            "last_name",
            "department_id",
            "job_id",
            "hire_date",
        ]
    )

    df = df.drop_duplicates(
        subset=["employee_id"],
        keep="first",
    )

    record_summary(
        "employees",
        "missing emails and invalid termination dates",
        before,
        len(df),
        (
            f"Generated {int(missing_email.sum())} emails; "
            f"replaced {invalid_count} invalid termination dates "
            "with missing values"
        ),
    )

    return df


# --------------------------------------------------
# 6. Clean departments and jobs
# --------------------------------------------------

def clean_dimension(df, name, key, required_columns):
    before = len(df)

    df = df.dropna(subset=required_columns)

    df = df.drop_duplicates(
        subset=[key],
        keep="first",
    )

    record_summary(
        name,
        "required fields and duplicate keys",
        before,
        len(df),
        f"Checked required columns and unique {key}",
    )

    return df


# --------------------------------------------------
# 7. Clean salaries
# --------------------------------------------------

def clean_salaries(df):
    before = len(df)

    invalid_salary = (
        df["salary_amount"].isna()
        | (df["salary_amount"] <= 0)
    )

    rejected = df.loc[invalid_salary].copy()

    rejected.to_csv(
        REPORT_DIR / "rejected_salaries.csv",
        index=False,
        date_format="%Y-%m-%d",
    )

    df = df.loc[~invalid_salary].copy()

    df = df.dropna(
        subset=[
            "salary_id",
            "employee_id",
            "effective_date",
        ]
    )

    df = df.drop_duplicates(
        subset=["salary_id"],
        keep="first",
    )

    record_summary(
        "salaries",
        "invalid amounts and duplicate keys",
        before,
        len(df),
        (
            f"Quarantined {len(rejected)} records with "
            "missing, zero, or negative salary amounts; "
            "saved them to rejected_salaries.csv"
        ),
    )

    return df


# --------------------------------------------------
# 8. Clean attendance
# --------------------------------------------------

def clean_attendance(df):
    before = len(df)

    valid_statuses = {
        "Present",
        "Absent",
        "Work From Home",
        "Half Day",
    }

    df = df.dropna(
        subset=[
            "attendance_id",
            "employee_id",
            "attendance_date",
        ]
    )

    # Remove unknown statuses instead of silently changing them.
    df = df[df["status"].isin(valid_statuses)].copy()

    # One attendance record per employee per date.
    # This also removes the generator's duplicate business events.
    df = df.drop_duplicates(
        subset=["employee_id", "attendance_date"],
        keep="first",
    )

    # Ensure each retained record has a unique primary key.
    df = df.drop_duplicates(
        subset=["attendance_id"],
        keep="first",
    )

    record_summary(
        "attendance",
        "status normalization and duplicate events",
        before,
        len(df),
        (
            "Normalized status vocabulary; kept one record "
            "per employee per attendance date"
        ),
    )

    return df


# --------------------------------------------------
# 9. Clean leaves
# --------------------------------------------------

def clean_leaves(df):
    before = len(df)

    df = df.dropna(
        subset=[
            "leave_id",
            "employee_id",
            "start_date",
            "end_date",
            "leave_type",
            "status",
        ]
    )

    # Invalid date ranges cannot represent valid leave periods.
    df = df[df["end_date"] >= df["start_date"]].copy()

    valid_leave_types = {
        "Annual", "Sick", "Casual", "Unpaid"
    }
    valid_leave_statuses = {
        "Approved", "Pending", "Rejected"
    }

    df = df[
        df["leave_type"].isin(valid_leave_types)
        & df["status"].isin(valid_leave_statuses)
    ].copy()

    df = df.drop_duplicates(
        subset=["leave_id"],
        keep="first",
    )

    record_summary(
        "leaves",
        "required fields, dates, categories and duplicate keys",
        before,
        len(df),
        "Validated leave date ranges and category values",
    )

    return df


# --------------------------------------------------
# 10. Clean performance
# --------------------------------------------------

def clean_performance(df):
    before = len(df)

    df = df.dropna(
        subset=[
            "performance_id",
            "employee_id",
            "review_date",
        ]
    )

    # Valid ratings are integers from 1 through 5.
    # Missing ratings remain missing; no score is invented.
    invalid_rating = (
        df["rating"].notna()
        & ~df["rating"].between(1, 5)
    )

    df.loc[invalid_rating, "rating"] = pd.NA

    df = df.drop_duplicates(
        subset=["performance_id"],
        keep="first",
    )

    record_summary(
        "performance",
        "required fields, ratings and duplicate keys",
        before,
        len(df),
        (
            "Preserved missing ratings; invalid non-null "
            "ratings were set to missing"
        ),
    )

    return df


# --------------------------------------------------
# 11. Validate foreign-key relationships
# --------------------------------------------------

def remove_orphan_records(datasets):
    relationships = [
        ("employees", "department_id", "departments", "department_id"),
        ("employees", "job_id", "jobs", "job_id"),
        ("salaries", "employee_id", "employees", "employee_id"),
        ("attendance", "employee_id", "employees", "employee_id"),
        ("leaves", "employee_id", "employees", "employee_id"),
        ("performance", "employee_id", "employees", "employee_id"),
    ]

    for child_name, child_key, parent_name, parent_key in relationships:
        child = datasets[child_name]
        parent = datasets[parent_name]

        before = len(child)

        valid_parent_ids = set(
            parent[parent_key].dropna()
        )

        child = child[
            child[child_key].notna()
            & child[child_key].isin(valid_parent_ids)
        ].copy()

        datasets[child_name] = child

        record_summary(
            child_name,
            f"foreign-key check: {child_key}",
            before,
            len(child),
            f"Checked references against {parent_name}.{parent_key}",
        )

    return datasets


# --------------------------------------------------
# 12. Save cleaned datasets
# --------------------------------------------------

def save_datasets(datasets):
    for name, df in datasets.items():
        output_path = PROCESSED_DIR / f"{name}.csv"

        df.to_csv(
            output_path,
            index=False,
            date_format="%Y-%m-%d",
        )

        print(
            f"{name:<15} "
            f"Rows: {len(df):>7,} "
            f"Columns: {len(df.columns):>2}"
        )


# --------------------------------------------------
# 13. Main execution
# --------------------------------------------------

def main():
    datasets = load_datasets()

    print("HR DATA CLEANING")
    print("-" * 60)

    datasets = standardize_text(datasets)

    datasets["departments"] = clean_dimension(
        datasets["departments"],
        "departments",
        "department_id",
        ["department_id", "department_name"],
    )

    datasets["jobs"] = clean_dimension(
        datasets["jobs"],
        "jobs",
        "job_id",
        ["job_id", "job_title", "department_id"],
    )

    datasets["employees"] = clean_employees(
        datasets["employees"]
    )

    datasets["salaries"] = clean_salaries(
        datasets["salaries"]
    )

    datasets["attendance"] = clean_attendance(
        datasets["attendance"]
    )

    datasets["leaves"] = clean_leaves(
        datasets["leaves"]
    )

    datasets["performance"] = clean_performance(
        datasets["performance"]
    )

    datasets = remove_orphan_records(datasets)

    print("\nCLEANED DATASET COUNTS")
    print("-" * 60)
    save_datasets(datasets)

    summary = pd.DataFrame(cleaning_summary)

    summary.to_csv(
        REPORT_DIR / "cleaning_summary.csv",
        index=False,
    )

    print("\nCLEANING SUMMARY")
    print(summary.to_string(index=False))

    print("\nData cleaning completed.")
    print(f"Cleaned files: {PROCESSED_DIR}")
    print(f"Cleaning reports: {REPORT_DIR}")
    print("Original raw files were not modified.")


if __name__ == "__main__":
    main()
