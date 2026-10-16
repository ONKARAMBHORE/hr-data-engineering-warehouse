from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from build_warehouse import create_db_engine


PROJECT_ROOT = Path(__file__).resolve().parent.parent

REPORT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "warehouse_quality_reports"
)

REPORT_FILE = REPORT_DIR / "warehouse_quality_report.csv"


# Each SQL query returns the number of records that fail a check.
# Zero means the check passes.

QUALITY_CHECKS = [
    # -------------------------------------------------
    # 1. STAGING PRIMARY / BUSINESS KEY CHECKS
    # -------------------------------------------------
    (
        "stg_employees_unique_id",
        """
        SELECT COUNT(*)
        FROM (
            SELECT employee_id
            FROM stg.employees
            GROUP BY employee_id
            HAVING employee_id IS NULL OR COUNT(*) > 1
        ) AS invalid
        """,
        "Employee IDs must be present and unique.",
    ),
    (
        "stg_departments_unique_id",
        """
        SELECT COUNT(*)
        FROM (
            SELECT department_id
            FROM stg.departments
            GROUP BY department_id
            HAVING department_id IS NULL OR COUNT(*) > 1
        ) AS invalid
        """,
        "Department IDs must be present and unique.",
    ),
    (
        "stg_jobs_unique_id",
        """
        SELECT COUNT(*)
        FROM (
            SELECT job_id
            FROM stg.jobs
            GROUP BY job_id
            HAVING job_id IS NULL OR COUNT(*) > 1
        ) AS invalid
        """,
        "Job IDs must be present and unique.",
    ),
    (
        "stg_salaries_unique_id",
        """
        SELECT COUNT(*)
        FROM (
            SELECT salary_id
            FROM stg.salaries
            GROUP BY salary_id
            HAVING salary_id IS NULL OR COUNT(*) > 1
        ) AS invalid
        """,
        "Salary IDs must be present and unique.",
    ),
    (
        "stg_attendance_unique_id",
        """
        SELECT COUNT(*)
        FROM (
            SELECT attendance_id
            FROM stg.attendance
            GROUP BY attendance_id
            HAVING attendance_id IS NULL OR COUNT(*) > 1
        ) AS invalid
        """,
        "Attendance IDs must be present and unique.",
    ),
    (
        "stg_leaves_unique_id",
        """
        SELECT COUNT(*)
        FROM (
            SELECT leave_id
            FROM stg.leaves
            GROUP BY leave_id
            HAVING leave_id IS NULL OR COUNT(*) > 1
        ) AS invalid
        """,
        "Leave IDs must be present and unique.",
    ),
    (
        "stg_performance_unique_id",
        """
        SELECT COUNT(*)
        FROM (
            SELECT performance_id
            FROM stg.performance
            GROUP BY performance_id
            HAVING performance_id IS NULL OR COUNT(*) > 1
        ) AS invalid
        """,
        "Performance IDs must be present and unique.",
    ),

    # -------------------------------------------------
    # 2. DIMENSION COVERAGE
    # -------------------------------------------------
    (
        "employee_dimension_coverage",
        """
        SELECT COUNT(*)
        FROM stg.employees s
        LEFT JOIN dw.dim_employee d
            ON d.employee_id = s.employee_id
        WHERE d.employee_id IS NULL
        """,
        "Every staging employee must exist in the employee dimension.",
    ),
    (
        "department_dimension_coverage",
        """
        SELECT COUNT(*)
        FROM stg.departments s
        LEFT JOIN dw.dim_department d
            ON d.department_id = s.department_id
        WHERE d.department_id IS NULL
        """,
        "Every staging department must exist in the department dimension.",
    ),
    (
        "job_dimension_coverage",
        """
        SELECT COUNT(*)
        FROM stg.jobs s
        LEFT JOIN dw.dim_job d
            ON d.job_id = s.job_id
        WHERE d.job_id IS NULL
        """,
        "Every staging job must exist in the job dimension.",
    ),

    # -------------------------------------------------
    # 3. STAGING-TO-FACT COUNT CHECKS
    # -------------------------------------------------
    (
        "salary_fact_count",
        """
        SELECT CASE
            WHEN (SELECT COUNT(*) FROM stg.salaries)
               = (SELECT COUNT(*) FROM dw.fact_salary)
            THEN 0 ELSE 1
        END
        """,
        "Salary staging and warehouse row counts must match.",
    ),
    (
        "attendance_fact_count",
        """
        SELECT CASE
            WHEN (SELECT COUNT(*) FROM stg.attendance)
               = (SELECT COUNT(*) FROM dw.fact_attendance)
            THEN 0 ELSE 1
        END
        """,
        "Attendance staging and warehouse row counts must match.",
    ),
    (
        "leave_fact_count",
        """
        SELECT CASE
            WHEN (SELECT COUNT(*) FROM stg.leaves)
               = (SELECT COUNT(*) FROM dw.fact_leave)
            THEN 0 ELSE 1
        END
        """,
        "Leave staging and warehouse row counts must match.",
    ),
    (
        "performance_fact_count",
        """
        SELECT CASE
            WHEN (SELECT COUNT(*) FROM stg.performance)
               = (SELECT COUNT(*) FROM dw.fact_performance)
            THEN 0 ELSE 1
        END
        """,
        "Performance staging and warehouse row counts must match.",
    ),

    # -------------------------------------------------
    # 4. FACT TABLE BUSINESS RULES
    # -------------------------------------------------
    (
        "salary_amount_positive",
        """
        SELECT COUNT(*)
        FROM dw.fact_salary
        WHERE salary_amount IS NULL OR salary_amount <= 0
        """,
        "Every warehouse salary must be greater than zero.",
    ),
    (
        "attendance_status_valid",
        """
        SELECT COUNT(*)
        FROM dw.fact_attendance
        WHERE status IS NULL
           OR status NOT IN (
               'Present',
               'Absent',
               'Late',
               'Half Day',
               'Work From Home'
           )
        """,
        "Attendance status must be one of the approved categories.",
    ),
    (
        "attendance_employee_date_unique",
        """
        SELECT COUNT(*)
        FROM (
            SELECT employee_key, attendance_date_key
            FROM dw.fact_attendance
            GROUP BY employee_key, attendance_date_key
            HAVING COUNT(*) > 1
        ) AS duplicates
        """,
        "An employee must have at most one attendance record per date.",
    ),
    (
        "leave_dates_valid",
        """
        SELECT COUNT(*)
        FROM dw.fact_leave
        WHERE start_date_key IS NULL
           OR end_date_key IS NULL
           OR end_date_key < start_date_key
        """,
        "Leave end date must not be earlier than the start date.",
    ),
    (
        "leave_days_match_dates",
        """
        SELECT COUNT(*)
        FROM dw.fact_leave f
        JOIN dw.dim_date start_d
            ON start_d.date_key = f.start_date_key
        JOIN dw.dim_date end_d
            ON end_d.date_key = f.end_date_key
        WHERE f.leave_days <>
              (end_d.full_date - start_d.full_date + 1)
        """,
        "Leave days must equal the inclusive calendar-day difference.",
    ),
    (
        "performance_rating_valid",
        """
        SELECT COUNT(*)
        FROM dw.fact_performance
        WHERE rating IS NOT NULL
          AND (rating < 1 OR rating > 5)
        """,
        "Non-null performance ratings must be between 1 and 5.",
    ),

    # -------------------------------------------------
    # 5. FACT TABLE FOREIGN-KEY COVERAGE
    # -------------------------------------------------
    (
        "salary_employee_relationship",
        """
        SELECT COUNT(*)
        FROM dw.fact_salary f
        LEFT JOIN dw.dim_employee d
            ON d.employee_key = f.employee_key
        WHERE d.employee_key IS NULL
        """,
        "Every salary fact must reference a valid employee.",
    ),
    (
        "salary_department_relationship",
        """
        SELECT COUNT(*)
        FROM dw.fact_salary f
        LEFT JOIN dw.dim_department d
            ON d.department_key = f.department_key
        WHERE d.department_key IS NULL
        """,
        "Every salary fact must reference a valid department.",
    ),
    (
        "attendance_employee_relationship",
        """
        SELECT COUNT(*)
        FROM dw.fact_attendance f
        LEFT JOIN dw.dim_employee d
            ON d.employee_key = f.employee_key
        WHERE d.employee_key IS NULL
        """,
        "Every attendance fact must reference a valid employee.",
    ),
    (
        "leave_employee_relationship",
        """
        SELECT COUNT(*)
        FROM dw.fact_leave f
        LEFT JOIN dw.dim_employee d
            ON d.employee_key = f.employee_key
        WHERE d.employee_key IS NULL
        """,
        "Every leave fact must reference a valid employee.",
    ),
    (
        "performance_employee_relationship",
        """
        SELECT COUNT(*)
        FROM dw.fact_performance f
        LEFT JOIN dw.dim_employee d
            ON d.employee_key = f.employee_key
        WHERE d.employee_key IS NULL
        """,
        "Every performance fact must reference a valid employee.",
    ),
]


def run_quality_checks():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    engine = create_db_engine()
    results = []

    print("\nHR DATA WAREHOUSE — DATA QUALITY REPORT")
    print("=" * 75)

    try:
        with engine.connect() as connection:
            for check_name, query, description in QUALITY_CHECKS:
                try:
                    failed_rows = connection.execute(
                        text(query)
                    ).scalar_one()

                    passed = failed_rows == 0

                    results.append({
                        "check_name": check_name,
                        "status": "PASS" if passed else "FAIL",
                        "failed_rows": int(failed_rows),
                        "description": description,
                        "checked_at": datetime.now().isoformat(
                            timespec="seconds"
                        ),
                    })

                    status = "PASS" if passed else "FAIL"

                    print(
                        f"{status:<6} | "
                        f"{check_name:<38} | "
                        f"Failed rows: {failed_rows}"
                    )

                except Exception as exc:
                    results.append({
                        "check_name": check_name,
                        "status": "ERROR",
                        "failed_rows": None,
                        "description": f"{description} Error: {exc}",
                        "checked_at": datetime.now().isoformat(
                            timespec="seconds"
                        ),
                    })

                    print(f"ERROR  | {check_name} | {exc}")

    finally:
        engine.dispose()

    report = pd.DataFrame(results)
    report.to_csv(REPORT_FILE, index=False)

    total = len(report)
    passed = int((report["status"] == "PASS").sum())
    failed = int((report["status"] == "FAIL").sum())
    errors = int((report["status"] == "ERROR").sum())

    print("\n" + "=" * 75)
    print(f"Total checks : {total}")
    print(f"Passed       : {passed}")
    print(f"Failed       : {failed}")
    print(f"Errors       : {errors}")
    print(f"\nReport saved: {REPORT_FILE}")

    if failed > 0 or errors > 0:
        raise SystemExit(1)

    print("\nAll data quality checks passed.")


if __name__ == "__main__":
    run_quality_checks()