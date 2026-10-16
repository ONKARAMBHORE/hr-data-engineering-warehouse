
# File: src/explore_data.py

from pathlib import Path

import pandas as pd


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

REPORT_DIR = PROJECT_ROOT / "data" / "processed" / "exploration_reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 2. Load all datasets
# --------------------------------------------------

datasets = {
    "employees": pd.read_csv(
        RAW_DIR / "employees.csv",
        parse_dates=["hire_date", "termination_date"],
    ),
    "departments": pd.read_csv(
        RAW_DIR / "departments.csv",
    ),
    "jobs": pd.read_csv(
        RAW_DIR / "jobs.csv",
    ),
    "salaries": pd.read_csv(
        RAW_DIR / "salaries.csv",
        parse_dates=["effective_date"],
    ),
    "attendance": pd.read_csv(
        RAW_DIR / "attendance.csv",
        parse_dates=["attendance_date"],
    ),
    "leaves": pd.read_csv(
        RAW_DIR / "leaves.csv",
        parse_dates=["start_date", "end_date"],
    ),
    "performance": pd.read_csv(
        RAW_DIR / "performance.csv",
        parse_dates=["review_date"],
    ),
}


# --------------------------------------------------
# 3. Dataset overview
# --------------------------------------------------

print("\n" + "=" * 70)
print("1. DATASET OVERVIEW")
print("=" * 70)

overview_rows = []

for name, df in datasets.items():
    overview_rows.append(
        {
            "dataset": name,
            "rows": len(df),
            "columns": len(df.columns),
            "memory_mb": round(
                df.memory_usage(deep=True).sum() / (1024 ** 2),
                2,
            ),
        }
    )

    print(
        f"{name:<15} "
        f"Rows={len(df):>7,} "
        f"Columns={len(df.columns):>2}"
    )

overview = pd.DataFrame(overview_rows)
overview.to_csv(REPORT_DIR / "dataset_overview.csv", index=False)


# --------------------------------------------------
# 4. Column names and data types
# --------------------------------------------------

print("\n" + "=" * 70)
print("2. COLUMN NAMES AND DATA TYPES")
print("=" * 70)

schema_rows = []

for name, df in datasets.items():
    print(f"\nDataset: {name}")
    print(df.dtypes)

    for column in df.columns:
        schema_rows.append(
            {
                "dataset": name,
                "column": column,
                "dtype": str(df[column].dtype),
            }
        )

schema_report = pd.DataFrame(schema_rows)
schema_report.to_csv(REPORT_DIR / "schema_report.csv", index=False)


# --------------------------------------------------
# 5. Missing values
# --------------------------------------------------

print("\n" + "=" * 70)
print("3. MISSING VALUES")
print("=" * 70)

missing_rows = []

for name, df in datasets.items():
    missing_counts = df.isna().sum()

    for column, count in missing_counts.items():
        missing_rows.append(
            {
                "dataset": name,
                "column": column,
                "missing_count": int(count),
                "missing_percentage": round(
                    count / len(df) * 100, 2
                ) if len(df) else 0,
            }
        )

    columns_with_missing = missing_counts[missing_counts > 0]

    print(f"\n{name}:")

    if columns_with_missing.empty:
        print("No missing values")
    else:
        print(columns_with_missing)

missing_report = pd.DataFrame(missing_rows)
missing_report.to_csv(REPORT_DIR / "missing_values_report.csv", index=False)


# --------------------------------------------------
# 6. Duplicate records and duplicate IDs
# --------------------------------------------------

print("\n" + "=" * 70)
print("4. DUPLICATE ANALYSIS")
print("=" * 70)

primary_keys = {
    "employees": "employee_id",
    "departments": "department_id",
    "jobs": "job_id",
    "salaries": "salary_id",
    "attendance": "attendance_id",
    "leaves": "leave_id",
    "performance": "performance_id",
}

duplicate_rows = []

for name, df in datasets.items():
    exact_duplicates = int(df.duplicated().sum())
    primary_key = primary_keys[name]
    duplicate_ids = int(
        df[primary_key].duplicated(keep=False).sum()
    )

    duplicate_rows.append(
        {
            "dataset": name,
            "exact_duplicate_rows": exact_duplicates,
            "rows_with_duplicate_primary_key": duplicate_ids,
        }
    )

    print(f"\n{name}:")
    print(f"Exact duplicate rows: {exact_duplicates}")
    print(f"Rows with repeated {primary_key}: {duplicate_ids}")

duplicate_report = pd.DataFrame(duplicate_rows)
duplicate_report.to_csv(REPORT_DIR / "duplicate_report.csv", index=False)


# --------------------------------------------------
# 7. Numeric statistics
# --------------------------------------------------

print("\n" + "=" * 70)
print("5. NUMERIC STATISTICS")
print("=" * 70)

numeric_datasets = ["employees", "salaries", "performance"]

numeric_rows = []

for name in numeric_datasets:
    df = datasets[name]
    numeric_columns = df.select_dtypes(include="number").columns

    print(f"\nDataset: {name}")
    print(df[numeric_columns].describe().round(2))

    for column in numeric_columns:
        values = df[column]

        numeric_rows.append(
            {
                "dataset": name,
                "column": column,
                "count": int(values.count()),
                "min": values.min(),
                "max": values.max(),
                "mean": values.mean(),
                "median": values.median(),
            }
        )

numeric_report = pd.DataFrame(numeric_rows)
numeric_report.to_csv(REPORT_DIR / "numeric_statistics.csv", index=False)


# --------------------------------------------------
# 8. Categorical value distributions
# --------------------------------------------------

print("\n" + "=" * 70)
print("6. CATEGORICAL VALUE DISTRIBUTIONS")
print("=" * 70)

categorical_columns = {
    "employees": ["employment_type"],
    "departments": ["department_name", "location"],
    "jobs": ["job_title", "job_level"],
    "attendance": ["status"],
    "leaves": ["leave_type", "status"],
    "performance": ["rating", "review_category"],
}

category_rows = []

for name, columns in categorical_columns.items():
    df = datasets[name]

    for column in columns:
        print(f"\n{name}.{column}")
        counts = df[column].value_counts(dropna=False)

        print(counts)

        for value, count in counts.items():
            category_rows.append(
                {
                    "dataset": name,
                    "column": column,
                    "value": str(value),
                    "count": int(count),
                }
            )

category_report = pd.DataFrame(category_rows)
category_report.to_csv(REPORT_DIR / "category_distributions.csv", index=False)


# --------------------------------------------------
# 9. Date ranges
# --------------------------------------------------

print("\n" + "=" * 70)
print("7. DATE RANGES")
print("=" * 70)

date_columns = {
    "employees": ["hire_date", "termination_date"],
    "salaries": ["effective_date"],
    "attendance": ["attendance_date"],
    "leaves": ["start_date", "end_date"],
    "performance": ["review_date"],
}

date_rows = []

for name, columns in date_columns.items():
    df = datasets[name]

    for column in columns:
        dates = df[column].dropna()

        minimum = dates.min() if not dates.empty else pd.NaT
        maximum = dates.max() if not dates.empty else pd.NaT

        print(f"{name}.{column}: {minimum} to {maximum}")

        date_rows.append(
            {
                "dataset": name,
                "column": column,
                "minimum_date": minimum,
                "maximum_date": maximum,
                "missing_dates": int(df[column].isna().sum()),
            }
        )

date_report = pd.DataFrame(date_rows)
date_report.to_csv(REPORT_DIR / "date_ranges.csv", index=False)


# --------------------------------------------------
# 10. Foreign-key relationship checks
# --------------------------------------------------

print("\n" + "=" * 70)
print("8. FOREIGN-KEY RELATIONSHIPS")
print("=" * 70)

employees = datasets["employees"]
departments = datasets["departments"]
jobs = datasets["jobs"]

relationships = [
    (
        "employees.department_id -> departments.department_id",
        employees["department_id"],
        departments["department_id"],
    ),
    (
        "employees.job_id -> jobs.job_id",
        employees["job_id"],
        jobs["job_id"],
    ),
]

for table_name in ["salaries", "attendance", "leaves", "performance"]:
    relationships.append(
        (
            f"{table_name}.employee_id -> employees.employee_id",
            datasets[table_name]["employee_id"],
            employees["employee_id"],
        )
    )

relationship_rows = []

for description, child_values, parent_values in relationships:
    invalid_count = int(
        (~child_values.isin(parent_values)).sum()
    )

    print(f"{description}: {invalid_count} invalid references")

    relationship_rows.append(
        {
            "relationship": description,
            "invalid_reference_count": invalid_count,
        }
    )

relationship_report = pd.DataFrame(relationship_rows)
relationship_report.to_csv(
    REPORT_DIR / "relationship_report.csv",
    index=False,
)


# --------------------------------------------------
# 11. Additional business-rule exploration
# --------------------------------------------------

print("\n" + "=" * 70)
print("9. BUSINESS-RULE EXPLORATION")
print("=" * 70)

employees = datasets["employees"]
salaries = datasets["salaries"]
attendance = datasets["attendance"]
leaves = datasets["leaves"]
performance = datasets["performance"]

checks = {
    "Negative salary amounts": int(
        (salaries["salary_amount"] < 0).sum()
    ),
    "Non-positive salary amounts": int(
        (salaries["salary_amount"] <= 0).sum()
    ),
    "Termination before hire": int(
        (
            employees["termination_date"].notna()
            & (
                employees["termination_date"]
                < employees["hire_date"]
            )
        ).sum()
    ),
    "Leave end before leave start": int(
        (leaves["end_date"] < leaves["start_date"]).sum()
    ),
    "Performance ratings outside 1-5": int(
        (
            performance["rating"].notna()
            & ~performance["rating"].between(1, 5)
        ).sum()
    ),
    "Attendance statuses with surrounding spaces": int(
        attendance["status"].ne(
            attendance["status"].str.strip()
        ).sum()
    ),
}

for check_name, count in checks.items():
    print(f"{check_name}: {count}")

business_report = pd.DataFrame(
    [
        {"check": name, "count": count}
        for name, count in checks.items()
    ]
)
business_report.to_csv(
    REPORT_DIR / "business_rule_report.csv",
    index=False,
)


# --------------------------------------------------
# 12. Final summary
# --------------------------------------------------

print("\n" + "=" * 70)
print("EXPLORATION COMPLETED")
print("=" * 70)

print(f"Reports saved to: {REPORT_DIR}")
print("Raw CSV files have not been modified.")
