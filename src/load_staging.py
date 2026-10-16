# File: src/load_staging.py

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

load_dotenv(PROJECT_ROOT / ".env")

DATE_COLUMNS = {
    "employees": ["hire_date", "termination_date"],
    "salaries": ["effective_date"],
    "attendance": ["attendance_date"],
    "leaves": ["start_date", "end_date"],
    "performance": ["review_date"],
}

DATASET_NAMES = [
    "employees",
    "departments",
    "jobs",
    "salaries",
    "attendance",
    "leaves",
    "performance",
]


# --------------------------------------------------
# 2. Create PostgreSQL connection
# --------------------------------------------------

def create_db_engine():
    required_vars = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    ]

    missing = [
        var for var in required_vars
        if not os.getenv(var)
    ]

    if missing:
        raise ValueError(
            f"Missing environment variables in .env: {missing}"
        )

    database_url = URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        database=os.getenv("DB_NAME"),
    )

    return create_engine(
        database_url,
        pool_pre_ping=True,
    )


# --------------------------------------------------
# 3. Load a cleaned CSV
# --------------------------------------------------

def load_csv(dataset_name):
    csv_path = PROCESSED_DIR / f"{dataset_name}.csv"

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Cleaned CSV not found: {csv_path}\n"
            "Run python src/clean_data.py first."
        )

    df = pd.read_csv(
        csv_path,
        parse_dates=DATE_COLUMNS.get(dataset_name, []),
    )

    if df.empty:
        raise ValueError(
            f"{dataset_name}.csv is empty. "
            "Check the cleaned dataset before loading."
        )

    return df


# --------------------------------------------------
# 4. Load datasets into staging
# --------------------------------------------------

def load_dataset(engine, dataset_name):
    df = load_csv(dataset_name)

    # Reload behavior: replace this staging table each run.
    # This is appropriate for this initial full-load phase.
    df.to_sql(
        name=dataset_name,
        con=engine,
        schema="stg",
        if_exists="replace",
        index=False,
        chunksize=5000,
        method="multi",
    )

    return len(df), len(df.columns)


# --------------------------------------------------
# 5. Verify loaded row counts
# --------------------------------------------------

def verify_staging(engine):
    print("\nSTAGING ROW COUNT VERIFICATION")
    print("=" * 65)

    for dataset_name in DATASET_NAMES:
        query = text(
            f'SELECT COUNT(*) FROM stg."{dataset_name}"'
        )

        with engine.connect() as connection:
            database_count = connection.execute(
                query
            ).scalar_one()

        csv_df = load_csv(dataset_name)
        csv_count = len(csv_df)

        status = (
            "PASS"
            if database_count == csv_count
            else "FAIL"
        )

        print(
            f"{dataset_name:<15} "
            f"CSV: {csv_count:>7,} | "
            f"DB: {database_count:>7,} | "
            f"{status}"
        )

        if status == "FAIL":
            raise RuntimeError(
                f"Row count mismatch for {dataset_name}"
            )


# --------------------------------------------------
# 6. Main execution
# --------------------------------------------------

def main():
    schema_sql = (
        PROJECT_ROOT
        / "sql"
        / "staging"
        / "01_create_staging_schema.sql"
    )

    if not schema_sql.exists():
        raise FileNotFoundError(
            f"Schema SQL file not found: {schema_sql}"
        )

    engine = create_db_engine()

    try:
        # Create the staging schema.
        with engine.begin() as connection:
            connection.execute(
                text("CREATE SCHEMA IF NOT EXISTS stg")
            )

        print("HR POSTGRESQL STAGING LOAD")
        print("=" * 65)

        for dataset_name in DATASET_NAMES:
            rows, columns = load_dataset(
                engine,
                dataset_name,
            )

            print(
                f"Loaded {dataset_name:<15} "
                f"Rows: {rows:>7,} | "
                f"Columns: {columns}"
            )

        verify_staging(engine)

        print("\nPhase 7 staging load completed successfully.")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()