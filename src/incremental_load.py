from pathlib import Path

import pandas as pd
from sqlalchemy import text

from build_warehouse import (
    create_db_engine,
    LOAD_DEPARTMENTS,
    LOAD_JOBS,
    LOAD_EMPLOYEES,
    LOAD_DATES,
    LOAD_SALARY_FACT,
    LOAD_ATTENDANCE_FACT,
    LOAD_LEAVE_FACT,
    LOAD_PERFORMANCE_FACT,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

DATASETS = {
    "employees": {
        "key": "employee_id",
        "dates": ["hire_date", "termination_date"],
    },
    "departments": {
        "key": "department_id",
        "dates": [],
    },
    "jobs": {
        "key": "job_id",
        "dates": [],
    },
    "salaries": {
        "key": "salary_id",
        "dates": ["effective_date"],
    },
    "attendance": {
        "key": "attendance_id",
        "dates": ["attendance_date"],
    },
    "leaves": {
        "key": "leave_id",
        "dates": ["start_date", "end_date"],
    },
    "performance": {
        "key": "performance_id",
        "dates": ["review_date"],
    },
}

# Source ID -> fact table, mutable warehouse columns.
FACT_CONFIG = {
    "fact_salary": (
        "salary_id",
        [
            "employee_key", "department_key", "job_key",
            "effective_date_key", "salary_amount",
        ],
        LOAD_SALARY_FACT,
    ),
    "fact_attendance": (
        "attendance_id",
        [
            "employee_key", "department_key", "job_key",
            "attendance_date_key", "status", "attendance_count",
        ],
        LOAD_ATTENDANCE_FACT,
    ),
    "fact_leave": (
        "leave_id",
        [
            "employee_key", "department_key", "job_key",
            "start_date_key", "end_date_key",
            "leave_type", "status", "leave_days",
        ],
        LOAD_LEAVE_FACT,
    ),
    "fact_performance": (
        "performance_id",
        [
            "employee_key", "department_key", "job_key",
            "review_date_key", "rating", "review_category",
        ],
        LOAD_PERFORMANCE_FACT,
    ),
}


def load_incoming_csvs(connection):
    """Load cleaned CSVs into incoming tables, then upsert into staging."""

    for table_name, config in DATASETS.items():
        path = PROCESSED_DIR / f"{table_name}.csv"

        if not path.exists():
            raise FileNotFoundError(
                f"Missing cleaned CSV: {path}"
            )

        df = pd.read_csv(
            path,
            parse_dates=config["dates"],
        )

        if df.empty:
            raise ValueError(
                f"{table_name}.csv is empty; refusing to load."
            )

        key = config["key"]

        if key not in df.columns:
            raise ValueError(
                f"Missing key column {key} in {path}"
            )

        if df[key].isna().any() or df[key].duplicated().any():
            raise ValueError(
                f"Null or duplicate {key} values in {path}"
            )

        incoming = f"_incoming_{table_name}"

        # Incoming tables are disposable; production staging tables
        # retain their unique indexes.
        df.to_sql(
            name=incoming,
            con=connection,
            schema="stg",
            if_exists="replace",
            index=False,
            chunksize=5000,
            method="multi",
        )

        columns = list(df.columns)
        quoted_columns = ", ".join(f'"{col}"' for col in columns)
        update_columns = [col for col in columns if col != key]

        if update_columns:
            assignments = ", ".join(
                f'"{col}" = EXCLUDED."{col}"'
                for col in update_columns
            )
            old_row = ", ".join(
                f'target."{col}"' for col in update_columns
            )
            new_row = ", ".join(
                f'EXCLUDED."{col}"' for col in update_columns
            )

            conflict_action = f"""
                DO UPDATE SET {assignments}
                WHERE ROW({old_row})
                      IS DISTINCT FROM ROW({new_row})
            """
        else:
            conflict_action = "DO NOTHING"

        merge_sql = text(f"""
            INSERT INTO stg."{table_name}" AS target
                ({quoted_columns})
            SELECT {quoted_columns}
            FROM stg."{incoming}"
            ON CONFLICT ("{key}")
            {conflict_action}
        """)

        connection.execute(merge_sql)
        connection.execute(
            text(f'DROP TABLE stg."{incoming}"')
        )

        print(
            f"Staging processed: {table_name} "
            f"({len(df):,} incoming rows)"
        )


def make_fact_upsert(source_id, columns, base_sql):
    """Convert the existing fact INSERT into a changed-row upsert."""

    insert_sql = base_sql.strip().rstrip(";")
    insert_sql = insert_sql.replace(
        "INSERT INTO dw.",
        "INSERT INTO dw.",
        1,
    )

    # Add target alias to the INSERT statement.
    table_name = next(
        name for name, cfg in FACT_CONFIG.items()
        if cfg[0] == source_id
    )
    insert_sql = insert_sql.replace(
        f"INSERT INTO dw.{table_name} (",
        f"INSERT INTO dw.{table_name} AS target (",
        1,
    )

    assignments = ", ".join(
        f"{col} = EXCLUDED.{col}" for col in columns
    )
    old_row = ", ".join(f"target.{col}" for col in columns)
    new_row = ", ".join(f"EXCLUDED.{col}" for col in columns)

    return text(f"""
        {insert_sql}
        ON CONFLICT ({source_id})
        DO UPDATE SET {assignments}
        WHERE ROW({old_row})
              IS DISTINCT FROM ROW({new_row})
    """)


def main():
    engine = create_db_engine()

    try:
        with engine.begin() as connection:
            # 1. Merge incoming records into staging.
            load_incoming_csvs(connection)

            # 2. Update dimensions before loading facts.
            connection.execute(text(LOAD_DEPARTMENTS))
            connection.execute(text(LOAD_JOBS))
            connection.execute(text(LOAD_EMPLOYEES))
            connection.execute(text(LOAD_DATES))

            # 3. Insert new facts or update changed facts.
            for table_name, (
                source_id,
                columns,
                base_sql,
            ) in FACT_CONFIG.items():
                upsert_sql = make_fact_upsert(
                    source_id,
                    columns,
                    base_sql,
                )
                connection.execute(upsert_sql)
                print(f"Warehouse processed: {table_name}")

            # 4. Verify source-aligned row counts.
            print("\nINCREMENTAL LOAD ROW COUNT CHECK")
            print("=" * 55)

            for table_name in DATASETS:
                count = connection.execute(
                    text(f'SELECT COUNT(*) FROM stg."{table_name}"')
                ).scalar_one()
                print(f"stg.{table_name:<20} {count:>10,}")

            for table_name, (source_id, _, _) in FACT_CONFIG.items():
                count = connection.execute(
                    text(f"SELECT COUNT(*) FROM dw.{table_name}")
                ).scalar_one()
                print(f"dw.{table_name:<21} {count:>10,}")

        print("\nIncremental ETL completed successfully.")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()