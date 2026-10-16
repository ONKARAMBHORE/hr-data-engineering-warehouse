-- Unique source IDs enable safe incremental upserts.
-- Run after confirming existing IDs are unique.

CREATE UNIQUE INDEX IF NOT EXISTS uq_stg_employees_id
    ON stg.employees(employee_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_stg_departments_id
    ON stg.departments(department_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_stg_jobs_id
    ON stg.jobs(job_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_stg_salaries_id
    ON stg.salaries(salary_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_stg_attendance_id
    ON stg.attendance(attendance_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_stg_leaves_id
    ON stg.leaves(leave_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_stg_performance_id
    ON stg.performance(performance_id);