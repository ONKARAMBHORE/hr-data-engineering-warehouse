# Phase 6 — HR Data Warehouse Modeling

## 1. Modeling Approach

The project uses a dimensional model with four dimensions
and four fact tables.

## 2. Dimension Tables

### dim_employee
Grain: One row per employee.
Primary key: employee_key
Business key: employee_id

### dim_department
Grain: One row per department.
Primary key: department_key
Business key: department_id

### dim_job
Grain: One row per job.
Primary key: job_key
Business key: job_id

### dim_date
Grain: One row per calendar date.
Primary key: date_key
Format: YYYYMMDD

## 3. Fact Tables

### fact_salary
Grain: One row per salary record.
Measure: salary_amount

### fact_attendance
Grain: One row per employee per attendance date.
Measure: attendance_count

### fact_leave
Grain: One row per leave request.
Measures: leave_days

### fact_performance
Grain: One row per performance review.
Measure: rating

## 4. Relationships

- Each fact references the relevant dimension keys.
- Each source business ID is retained for traceability.
- Dimension surrogate keys are used as warehouse primary keys.
- Foreign keys maintain referential integrity.
- Department and job assignments represent current assignments.
- Leave duration is calculated using inclusive calendar days.

## 5. Business Analytics Supported

- Employee headcount
- Department-wise salary analysis
- Salary trends over time
- Daily and monthly attendance
- Leave utilization and leave status
- Employee performance ratings

## 6. Limitations

- Department and job assignment history is not available.
- Leave duration does not yet exclude weekends or holidays.
- Missing performance ratings remain missing; they are not replaced
  with invented scores.

## 7. Next Step

Create the PostgreSQL staging layer, then implement the warehouse
tables and load data through ETL.