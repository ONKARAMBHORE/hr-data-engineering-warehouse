
# HR Data Engineering & Data Warehouse

## 1. Business Objective
Build a centralized HR data warehouse for employee,
salary, attendance, leave, and performance analytics.

## 2. Source Datasets
- employees
- departments
- jobs
- salaries
- attendance
- leaves
- performance

## 3. Business KPIs
- Active employee headcount
- Employee turnover rate
- Department salary expenses
- Monthly attendance rate
- Average employee performance rating
- Salary growth
- Department headcount trends
- Leave utilization

## 4. Data Architecture
Raw CSV Files
-> Python and Pandas
-> PostgreSQL Staging
-> SQL Transformations
-> Data Warehouse
-> Analytics

## 5. Warehouse Tables

### Dimensions
- dim_employee
- dim_department
- dim_job
- dim_date

### Facts
- fact_salary
- fact_attendance
- fact_leave
- fact_performance

## 6. Technical Stack
Python, Pandas, PostgreSQL, SQL, ETL,
Docker, Docker Compose, Git, GitHub.

## 7. Data Quality Requirements
- Identify duplicate records.
- Validate mandatory fields.
- Validate data types and business rules.
- Check foreign-key relationships.
- Track rejected or invalid records.

## 8. Loading Requirements
- Support an initial full load.
- Support incremental loading of new and changed records.
- Avoid duplicate records during reruns.
- Validate loaded data.

## 9. Expected Deliverables
- Reproducible ETL pipeline
- PostgreSQL staging layer
- Star-schema data warehouse
- Incremental loading
- Data quality checks
- SQL analytics queries
- Dockerized environment
- GitHub documentation
