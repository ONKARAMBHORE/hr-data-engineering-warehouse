
# HR Data Engineering & Data Warehouse

An end-to-end HR data engineering project that demonstrates data generation, data exploration, data cleaning, data validation, PostgreSQL staging, data warehouse development, incremental loading, data quality checks, Dockerization, and SQL analytics.

## Project Overview

Organizations need reliable HR data to understand employee turnover, salary distribution, attendance, performance, and workforce growth.

This project builds a data pipeline that processes HR datasets and loads them into a PostgreSQL data warehouse designed for analytical queries and business reporting.

## Project Objectives

- Generate and explore HR datasets.
- Clean and standardize raw data using Python and Pandas.
- Validate data quality before loading.
- Load cleaned datasets into PostgreSQL staging tables.
- Design a dimensional data warehouse using a star-schema approach.
- Load employee, salary, attendance, leave, and performance data.
- Implement incremental loading for new and changed records.
- Build reusable data quality checks.
- Run the environment using Docker Compose.
- Write SQL queries for HR business analytics.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Data processing and ETL |
| Pandas | Data cleaning and transformation |
| NumPy | Synthetic data generation |
| PostgreSQL | Staging database and data warehouse |
| SQL | Transformations, validation, analytics |
| SQLAlchemy | Python database connectivity |
| Docker | Containerization |
| Docker Compose | Multi-container management |
| Git and GitHub | Version control and project documentation |
| pgAdmin | Database exploration and SQL execution |

## Architecture

```text
Raw HR Datasets
      |
      v
Python / Pandas
      |
      v
Data Exploration and Cleaning
      |
      v
Data Validation
      |
      v
PostgreSQL Staging Schema (stg)
      |
      v
ETL and Warehouse Loading
      |
      v
PostgreSQL Data Warehouse (dw)
      |
      v
Data Quality Framework
      |
      v
SQL Analytics and Business Insights
```

Docker Compose provides the containerized PostgreSQL and Python application environment.

## Dataset Description

The project generates synthetic HR datasets.

| Dataset | Description |
|---|---|
| Employees | Employee details and employment dates |
| Departments | Department names and locations |
| Jobs | Job titles, levels, and department references |
| Salaries | Employee salary history |
| Attendance | Daily employee attendance |
| Leaves | Employee leave requests and statuses |
| Performance | Employee performance reviews |

The generated datasets initially include selected data quality issues so the cleaning and validation stages can be demonstrated.

## Data Warehouse Design

The warehouse uses dimension and fact tables.

### Dimension tables

- `dw.dim_employee`
- `dw.dim_department`
- `dw.dim_job`
- `dw.dim_date`

### Fact tables

- `dw.fact_salary`
- `dw.fact_attendance`
- `dw.fact_leave`
- `dw.fact_performance`

The dimensions provide descriptive context, while fact tables store salary, attendance, leave, and performance events.

The current model uses the employee's current department and job assignment when associating records with dimensions; it does not implement historical slowly changing dimensions.

## SQL Analytics

The combined SQL script is located at:

`sql/analytics/01_hr_analytics.sql`

It includes:

1. **Employee Turnover Analysis** — annual employee exits and turnover rates.
2. **Department Salary Analysis** — latest salary statistics by department.
3. **Monthly Attendance Analysis** — attendance counts and attendance rates.
4. **Employee Performance Analysis** — ratings by department and review category, plus top-rated employees.
5. **Employee Salary Growth** — earliest versus latest recorded salary.
6. **Department Headcount** — employee distribution by department.

These reports are intended for HR analysis and can be extended with additional business rules and reporting requirements.

## Prerequisites

- Python 3.12
- PostgreSQL 16, or Docker Desktop with Docker Compose
- Git
- pgAdmin (optional)

## Local Setup

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd hr-data-engineering
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hr_data_warehouse
DB_USER=postgres
DB_PASSWORD=your_local_password
```

Replace the example password with your own local database password. Never commit real credentials.

### 5. Run the ETL pipeline

After configuring PostgreSQL and creating the required schemas:

```powershell
python src/run_pipeline.py
```

The pipeline should execute the stages configured in `src/run_pipeline.py`. Review the script before running it to confirm whether it performs a full refresh or incremental loading.

## Docker Setup

Start the containers:

```powershell
docker compose up -d --build
```

Check container health:

```powershell
docker compose ps
```

Run the configured pipeline:

```powershell
docker compose exec app python src/run_pipeline.py
```

View database logs:

```powershell
docker compose logs postgres
```

Stop the containers without deleting the database volume:

```powershell
docker compose down
```

Follow the repository's SQL initialization instructions before the first load. Database initialization scripts mounted under `/docker-entrypoint-initdb.d/` execute only when PostgreSQL initializes an empty data directory.

## Data Quality

The project includes validation at multiple stages:

- Missing and duplicate values
- Invalid salary values
- Invalid attendance statuses
- Foreign-key and reference validation
- Fact and dimension coverage
- Leave date and duration checks
- Performance rating validation
- Staging-to-warehouse row-count checks

The warehouse quality framework generates a CSV report at:

`data/processed/warehouse_quality_reports/warehouse_quality_report.csv`

Check the actual output before claiming that all quality checks pass.

## Project Pipeline Stages

1. Business requirements and KPIs
2. Raw HR dataset generation
3. Data exploration
4. Data cleaning
5. Data validation
6. Dimensional data modeling
7. PostgreSQL staging
8. Data warehouse construction
9. ETL pipeline orchestration
10. Incremental loading
11. Data quality framework
12. Dockerization
13. SQL analytics
14. GitHub documentation

## Future Improvements

- Add automated tests for the complete ETL pipeline.
- Add CI checks using GitHub Actions.
- Implement slowly changing dimensions for employee history.
- Add a BI dashboard for HR reporting.
- Add scheduling and monitoring for production ETL workflows.

## Author

Onkar Ambhore

GitHub: https://github.com/ONKARAMBHORE

LinkedIn: https://linkedin.com/in/onkar-ambhore-77134b289
