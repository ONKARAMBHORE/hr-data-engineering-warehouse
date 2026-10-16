# File: src/build_warehouse.py

from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text
import os


# --------------------------------------------------
# 1. PROJECT CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def create_db_engine():
    required = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    ]

    missing = [key for key in required if not os.getenv(key)]

    if missing:
        raise ValueError(
            f"Missing .env variables: {missing}"
        )

    url = URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        database=os.getenv("DB_NAME"),
    )

    return create_engine(url, pool_pre_ping=True)


# --------------------------------------------------
# 2. LOAD DIMENSION TABLES
# --------------------------------------------------

LOAD_DEPARTMENTS = """
INSERT INTO dw.dim_department AS target (
    department_id,
    department_name,
    location
)
SELECT
    department_id,
    department_name,
    location
FROM stg.departments
ON CONFLICT (department_id)
DO UPDATE SET
    department_name = EXCLUDED.department_name,
    location = EXCLUDED.location
WHERE ROW(target.department_name, target.location)
      IS DISTINCT FROM
      ROW(EXCLUDED.department_name, EXCLUDED.location);
"""


LOAD_JOBS = """
INSERT INTO dw.dim_job AS target (
    job_id,
    job_title,
    job_level
)
SELECT
    job_id,
    job_title,
    job_level
FROM stg.jobs
ON CONFLICT (job_id)
DO UPDATE SET
    job_title = EXCLUDED.job_title,
    job_level = EXCLUDED.job_level
WHERE ROW(target.job_title, target.job_level)
      IS DISTINCT FROM
      ROW(EXCLUDED.job_title, EXCLUDED.job_level);
"""

LOAD_EMPLOYEES = """
INSERT INTO dw.dim_employee AS target (
    employee_id,
    first_name,
    last_name,
    email,
    hire_date,
    termination_date,
    employment_type
)
SELECT
    employee_id,
    first_name,
    last_name,
    email,
    hire_date,
    termination_date,
    employment_type
FROM stg.employees
ON CONFLICT (employee_id)
DO UPDATE SET
    first_name = EXCLUDED.first_name,
    last_name = EXCLUDED.last_name,
    email = EXCLUDED.email,
    hire_date = EXCLUDED.hire_date,
    termination_date = EXCLUDED.termination_date,
    employment_type = EXCLUDED.employment_type
WHERE ROW(
    target.first_name,
    target.last_name,
    target.email,
    target.hire_date,
    target.termination_date,
    target.employment_type
)
IS DISTINCT FROM ROW(
    EXCLUDED.first_name,
    EXCLUDED.last_name,
    EXCLUDED.email,
    EXCLUDED.hire_date,
    EXCLUDED.termination_date,
    EXCLUDED.employment_type
);
"""

# --------------------------------------------------
# 3. BUILD DATE DIMENSION
# --------------------------------------------------

LOAD_DATES = """
WITH source_dates AS (
    SELECT hire_date AS dt
    FROM stg.employees

    UNION ALL
    SELECT termination_date
    FROM stg.employees

    UNION ALL
    SELECT effective_date
    FROM stg.salaries

    UNION ALL
    SELECT attendance_date
    FROM stg.attendance

    UNION ALL
    SELECT start_date
    FROM stg.leaves

    UNION ALL
    SELECT end_date
    FROM stg.leaves

    UNION ALL
    SELECT review_date
    FROM stg.performance
),
date_bounds AS (
    SELECT
        MIN(dt)::date AS min_date,
        MAX(dt)::date AS max_date
    FROM source_dates
    WHERE dt IS NOT NULL
),
calendar AS (
    SELECT
        generate_series(
            min_date,
            max_date,
            INTERVAL '1 day'
        )::date AS full_date
    FROM date_bounds
    WHERE min_date IS NOT NULL
      AND max_date IS NOT NULL
)
INSERT INTO dw.dim_date (
    date_key,
    full_date,
    day_of_month,
    month_number,
    month_name,
    quarter_number,
    year_number,
    day_of_week,
    day_name,
    is_weekend
)
SELECT
    TO_CHAR(full_date, 'YYYYMMDD')::integer,
    full_date,
    EXTRACT(DAY FROM full_date)::smallint,
    EXTRACT(MONTH FROM full_date)::smallint,
    TO_CHAR(full_date, 'FMMonth'),
    EXTRACT(QUARTER FROM full_date)::smallint,
    EXTRACT(YEAR FROM full_date)::smallint,
    EXTRACT(ISODOW FROM full_date)::smallint,
    TO_CHAR(full_date, 'FMDay'),
    EXTRACT(ISODOW FROM full_date) IN (6, 7)
FROM calendar
ON CONFLICT (date_key)
DO UPDATE SET
    full_date = EXCLUDED.full_date,
    day_of_month = EXCLUDED.day_of_month,
    month_number = EXCLUDED.month_number,
    month_name = EXCLUDED.month_name,
    quarter_number = EXCLUDED.quarter_number,
    year_number = EXCLUDED.year_number,
    day_of_week = EXCLUDED.day_of_week,
    day_name = EXCLUDED.day_name,
    is_weekend = EXCLUDED.is_weekend;
"""


# --------------------------------------------------
# 4. LOAD FACT TABLES
# --------------------------------------------------

LOAD_SALARY_FACT = """
INSERT INTO dw.fact_salary (
    salary_id,
    employee_key,
    department_key,
    job_key,
    effective_date_key,
    salary_amount
)
SELECT
    s.salary_id,
    de.employee_key,
    dd.department_key,
    dj.job_key,
    dt.date_key,
    s.salary_amount
FROM stg.salaries s
JOIN stg.employees e
    ON e.employee_id = s.employee_id
JOIN dw.dim_employee de
    ON de.employee_id = e.employee_id
JOIN dw.dim_department dd
    ON dd.department_id = e.department_id
JOIN dw.dim_job dj
    ON dj.job_id = e.job_id
JOIN dw.dim_date dt
    ON dt.full_date = s.effective_date;
"""


LOAD_ATTENDANCE_FACT = """
INSERT INTO dw.fact_attendance (
    attendance_id,
    employee_key,
    department_key,
    job_key,
    attendance_date_key,
    status,
    attendance_count
)
SELECT
    a.attendance_id,
    de.employee_key,
    dd.department_key,
    dj.job_key,
    dt.date_key,
    a.status,
    1
FROM stg.attendance a
JOIN stg.employees e
    ON e.employee_id = a.employee_id
JOIN dw.dim_employee de
    ON de.employee_id = e.employee_id
JOIN dw.dim_department dd
    ON dd.department_id = e.department_id
JOIN dw.dim_job dj
    ON dj.job_id = e.job_id
JOIN dw.dim_date dt
    ON dt.full_date = a.attendance_date;
"""


LOAD_LEAVE_FACT = """
INSERT INTO dw.fact_leave (
    leave_id,
    employee_key,
    department_key,
    job_key,
    start_date_key,
    end_date_key,
    leave_type,
    status,
    leave_days
)
SELECT
    l.leave_id,
    de.employee_key,
    dd.department_key,
    dj.job_key,
    start_dt.date_key,
    end_dt.date_key,
    l.leave_type,
    l.status,
    ((l.end_date::date - l.start_date::date) + 1)
FROM stg.leaves l
JOIN stg.employees e
    ON e.employee_id = l.employee_id
JOIN dw.dim_employee de
    ON de.employee_id = e.employee_id
JOIN dw.dim_department dd
    ON dd.department_id = e.department_id
JOIN dw.dim_job dj
    ON dj.job_id = e.job_id
JOIN dw.dim_date start_dt
    ON start_dt.full_date = l.start_date
JOIN dw.dim_date end_dt
    ON end_dt.full_date = l.end_date;
"""


LOAD_PERFORMANCE_FACT = """
INSERT INTO dw.fact_performance (
    performance_id,
    employee_key,
    department_key,
    job_key,
    review_date_key,
    rating,
    review_category
)
SELECT
    p.performance_id,
    de.employee_key,
    dd.department_key,
    dj.job_key,
    dt.date_key,
    p.rating,
    p.review_category
FROM stg.performance p
JOIN stg.employees e
    ON e.employee_id = p.employee_id
JOIN dw.dim_employee de
    ON de.employee_id = e.employee_id
JOIN dw.dim_department dd
    ON dd.department_id = e.department_id
JOIN dw.dim_job dj
    ON dj.job_id = e.job_id
JOIN dw.dim_date dt
    ON dt.full_date = p.review_date;
"""


# --------------------------------------------------
# 5. VERIFY WAREHOUSE COUNTS
# --------------------------------------------------

TABLES = [
    "dim_employee",
    "dim_department",
    "dim_job",
    "dim_date",
    "fact_salary",
    "fact_attendance",
    "fact_leave",
    "fact_performance",
]


def verify_warehouse(connection):
    print("\nWAREHOUSE ROW COUNT SUMMARY")
    print("=" * 55)

    for table_name in TABLES:
        count = connection.execute(
            text(f"SELECT COUNT(*) FROM dw.{table_name}")
        ).scalar_one()

        print(f"{table_name:<25} {count:>10,}")


# --------------------------------------------------
# 6. MAIN PIPELINE
# --------------------------------------------------

def main():
    engine = create_db_engine()

    try:
        with engine.begin() as connection:
            # Confirm required schemas exist.
            schemas = connection.execute(
                text("""
                    SELECT schema_name
                    FROM information_schema.schemata
                    WHERE schema_name IN ('stg', 'dw')
                """)
            ).scalars().all()

            if not {"stg", "dw"}.issubset(set(schemas)):
                raise RuntimeError(
                    "Required schemas missing. "
                    "Complete Phase 7 and execute the "
                    "Phase 6 warehouse DDL first."
                )

            # Refresh dimensions using source business IDs.
            connection.execute(text(LOAD_DEPARTMENTS))
            connection.execute(text(LOAD_JOBS))
            connection.execute(text(LOAD_EMPLOYEES))
            connection.execute(text(LOAD_DATES))

            # Full reload: remove old facts before inserting new ones.
            connection.execute(text("""
                TRUNCATE TABLE
                    dw.fact_salary,
                    dw.fact_attendance,
                    dw.fact_leave,
                    dw.fact_performance
                RESTART IDENTITY;
            """))

            connection.execute(text(LOAD_SALARY_FACT))
            connection.execute(text(LOAD_ATTENDANCE_FACT))
            connection.execute(text(LOAD_LEAVE_FACT))
            connection.execute(text(LOAD_PERFORMANCE_FACT))

            # Verify counts before the transaction commits.
            verify_warehouse(connection)

        print("\nPhase 8 warehouse build completed successfully.")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()