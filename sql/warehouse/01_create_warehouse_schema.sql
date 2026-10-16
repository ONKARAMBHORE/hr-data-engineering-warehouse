-- HR Data Warehouse
-- Phase 6: Dimensional Model
-- Execute during the warehouse implementation phase.

CREATE SCHEMA IF NOT EXISTS dw;

-- ==================================================
-- 1. DIMENSION TABLES
-- ==================================================

CREATE TABLE dw.dim_department (
    department_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    department_id INTEGER NOT NULL UNIQUE,
    department_name VARCHAR(100) NOT NULL,
    location VARCHAR(100)
);

CREATE TABLE dw.dim_job (
    job_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_id INTEGER NOT NULL UNIQUE,
    job_title VARCHAR(100) NOT NULL,
    job_level VARCHAR(50)
);

CREATE TABLE dw.dim_employee (
    employee_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id INTEGER NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    hire_date DATE NOT NULL,
    termination_date DATE,
    employment_type VARCHAR(50) NOT NULL,

    CONSTRAINT chk_employee_dates
        CHECK (
            termination_date IS NULL
            OR termination_date >= hire_date
        ),

    CONSTRAINT chk_employment_type
        CHECK (
            employment_type IN (
                'Full-Time',
                'Part-Time',
                'Contract'
            )
        )
);

CREATE TABLE dw.dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    day_of_month SMALLINT NOT NULL,
    month_number SMALLINT NOT NULL,
    month_name VARCHAR(15) NOT NULL,
    quarter_number SMALLINT NOT NULL,
    year_number SMALLINT NOT NULL,
    day_of_week SMALLINT NOT NULL,
    day_name VARCHAR(15) NOT NULL,
    is_weekend BOOLEAN NOT NULL,

    CONSTRAINT chk_date_key
        CHECK (
            date_key =
            (
                EXTRACT(YEAR FROM full_date)::INTEGER * 10000
                + EXTRACT(MONTH FROM full_date)::INTEGER * 100
                + EXTRACT(DAY FROM full_date)::INTEGER
            )
        )
);

-- ==================================================
-- 2. FACT TABLES
-- ==================================================

CREATE TABLE dw.fact_salary (
    salary_fact_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    salary_id INTEGER NOT NULL UNIQUE,

    employee_key BIGINT NOT NULL
        REFERENCES dw.dim_employee(employee_key),

    department_key BIGINT NOT NULL
        REFERENCES dw.dim_department(department_key),

    job_key BIGINT NOT NULL
        REFERENCES dw.dim_job(job_key),

    effective_date_key INTEGER NOT NULL
        REFERENCES dw.dim_date(date_key),

    salary_amount NUMERIC(12, 2) NOT NULL,

    CONSTRAINT chk_salary_positive
        CHECK (salary_amount > 0)
);

CREATE TABLE dw.fact_attendance (
    attendance_fact_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    attendance_id INTEGER NOT NULL UNIQUE,

    employee_key BIGINT NOT NULL
        REFERENCES dw.dim_employee(employee_key),

    department_key BIGINT NOT NULL
        REFERENCES dw.dim_department(department_key),

    job_key BIGINT NOT NULL
        REFERENCES dw.dim_job(job_key),

    attendance_date_key INTEGER NOT NULL
        REFERENCES dw.dim_date(date_key),

    status VARCHAR(30) NOT NULL,
    attendance_count SMALLINT NOT NULL DEFAULT 1,

    CONSTRAINT uq_attendance_employee_date
        UNIQUE (employee_key, attendance_date_key),

    CONSTRAINT chk_attendance_status
        CHECK (
            status IN (
                'Present',
                'Absent',
                'Work From Home',
                'Half Day'
            )
        ),

    CONSTRAINT chk_attendance_count
        CHECK (attendance_count = 1)
);

CREATE TABLE dw.fact_leave (
    leave_fact_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    leave_id INTEGER NOT NULL UNIQUE,

    employee_key BIGINT NOT NULL
        REFERENCES dw.dim_employee(employee_key),

    department_key BIGINT NOT NULL
        REFERENCES dw.dim_department(department_key),

    job_key BIGINT NOT NULL
        REFERENCES dw.dim_job(job_key),

    start_date_key INTEGER NOT NULL
        REFERENCES dw.dim_date(date_key),

    end_date_key INTEGER NOT NULL
        REFERENCES dw.dim_date(date_key),

    leave_type VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL,
    leave_days INTEGER NOT NULL,

    CONSTRAINT chk_leave_dates
        CHECK (end_date_key >= start_date_key),

    CONSTRAINT chk_leave_days
        CHECK (leave_days >= 1),

    CONSTRAINT chk_leave_type
        CHECK (
            leave_type IN (
                'Annual', 'Sick', 'Casual', 'Unpaid'
            )
        ),

    CONSTRAINT chk_leave_status
        CHECK (
            status IN (
                'Approved', 'Pending', 'Rejected'
            )
        )
);

CREATE TABLE dw.fact_performance (
    performance_fact_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    performance_id INTEGER NOT NULL UNIQUE,

    employee_key BIGINT NOT NULL
        REFERENCES dw.dim_employee(employee_key),

    department_key BIGINT NOT NULL
        REFERENCES dw.dim_department(department_key),

    job_key BIGINT NOT NULL
        REFERENCES dw.dim_job(job_key),

    review_date_key INTEGER NOT NULL
        REFERENCES dw.dim_date(date_key),

    rating NUMERIC(3, 1),
    review_category VARCHAR(50),

    CONSTRAINT chk_performance_rating
        CHECK (
            rating IS NULL
            OR rating BETWEEN 1 AND 5
        )
);

-- ==================================================
-- 3. INDEXES FOR COMMON ANALYTICS JOINS
-- ==================================================

CREATE INDEX idx_salary_employee
    ON dw.fact_salary(employee_key);

CREATE INDEX idx_salary_date
    ON dw.fact_salary(effective_date_key);

CREATE INDEX idx_salary_department
    ON dw.fact_salary(department_key);

CREATE INDEX idx_attendance_date
    ON dw.fact_attendance(attendance_date_key);

CREATE INDEX idx_attendance_department
    ON dw.fact_attendance(department_key);

CREATE INDEX idx_leave_start_date
    ON dw.fact_leave(start_date_key);

CREATE INDEX idx_leave_department
    ON dw.fact_leave(department_key);

CREATE INDEX idx_performance_review_date
    ON dw.fact_performance(review_date_key);

CREATE INDEX idx_performance_department
    ON dw.fact_performance(department_key);