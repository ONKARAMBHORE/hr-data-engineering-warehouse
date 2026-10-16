-- ============================================================
-- 1. EMPLOYEE TURNOVER ANALYSIS
-- ============================================================

WITH years AS (
    SELECT DISTINCT year_number AS year
    FROM dw.dim_date
),
yearly_metrics AS (
    SELECT
        y.year,

        COUNT(*) FILTER (
            WHERE e.termination_date >= MAKE_DATE(y.year, 1, 1)
              AND e.termination_date < MAKE_DATE(y.year + 1, 1, 1)
        ) AS employees_left,

        COUNT(*) FILTER (
            WHERE e.hire_date <= MAKE_DATE(y.year, 1, 1)
              AND (
                  e.termination_date IS NULL
                  OR e.termination_date >= MAKE_DATE(y.year, 1, 1)
              )
        ) AS opening_headcount,

        COUNT(*) FILTER (
            WHERE e.hire_date < MAKE_DATE(y.year + 1, 1, 1)
              AND (
                  e.termination_date IS NULL
                  OR e.termination_date >= MAKE_DATE(y.year + 1, 1, 1)
              )
        ) AS closing_headcount

    FROM years y
    CROSS JOIN dw.dim_employee e
    GROUP BY y.year
)
SELECT
    year,
    employees_left,
    opening_headcount,
    closing_headcount,

    ROUND(
        100.0 * employees_left
        / NULLIF(
            (opening_headcount + closing_headcount)::NUMERIC / 2,
            0
        ),
        2
    ) AS turnover_rate_percent

FROM yearly_metrics
ORDER BY year;

-- ============================================================
-- 2. DEPARTMENT SALARY ANALYSIS
-- Business question:
-- Which departments have the highest average salary?
-- Uses each employee's latest salary record.
-- ============================================================

WITH ranked_salaries AS (
    SELECT
        fs.employee_key,
        fs.department_key,
        fs.salary_amount,
        d.full_date AS effective_date,

        ROW_NUMBER() OVER (
            PARTITION BY fs.employee_key
            ORDER BY d.full_date DESC, fs.salary_fact_key DESC
        ) AS rn

    FROM dw.fact_salary fs
    JOIN dw.dim_date d
        ON d.date_key = fs.effective_date_key
)
SELECT
    dept.department_name,
    COUNT(*) AS employee_count,
    ROUND(AVG(rs.salary_amount), 2) AS average_salary,
    MIN(rs.salary_amount) AS minimum_salary,
    MAX(rs.salary_amount) AS maximum_salary,
    SUM(rs.salary_amount) AS total_latest_salary
FROM ranked_salaries rs
JOIN dw.dim_department dept
    ON dept.department_key = rs.department_key
WHERE rs.rn = 1
GROUP BY dept.department_key, dept.department_name
ORDER BY average_salary DESC;


-- ============================================================
-- 3. MONTHLY ATTENDANCE ANALYSIS
-- Business question:
-- How does attendance change month by month?
-- ============================================================

SELECT
    DATE_TRUNC('month', d.full_date)::DATE AS attendance_month,

    COUNT(*) AS total_attendance_records,

    COUNT(*) FILTER (
        WHERE LOWER(TRIM(f.status)) = 'present'
    ) AS present_count,

    COUNT(*) FILTER (
        WHERE LOWER(TRIM(f.status)) = 'absent'
    ) AS absent_count,

    COUNT(*) FILTER (
        WHERE LOWER(TRIM(f.status)) = 'late'
    ) AS late_count,

    COUNT(*) FILTER (
        WHERE LOWER(TRIM(f.status)) = 'half day'
    ) AS half_day_count,

    COUNT(*) FILTER (
        WHERE LOWER(TRIM(f.status)) = 'work from home'
    ) AS work_from_home_count,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE LOWER(TRIM(f.status)) IN (
                'present', 'late', 'half day', 'work from home'
            )
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS attendance_rate_percent

FROM dw.fact_attendance f
JOIN dw.dim_date d
    ON d.date_key = f.attendance_date_key
GROUP BY DATE_TRUNC('month', d.full_date)::DATE
ORDER BY attendance_month;


-- ============================================================
-- 4. EMPLOYEE PERFORMANCE ANALYSIS
-- Business question:
-- What are the average performance ratings by department
-- and review category?
-- ============================================================

SELECT
    dept.department_name,
    f.review_category,
    COUNT(*) AS total_reviews,
    COUNT(f.rating) AS rated_reviews,
    ROUND(AVG(f.rating), 2) AS average_rating,
    MIN(f.rating) AS minimum_rating,
    MAX(f.rating) AS maximum_rating
FROM dw.fact_performance f
JOIN dw.dim_department dept
    ON dept.department_key = f.department_key
GROUP BY
    dept.department_key,
    dept.department_name,
    f.review_category
ORDER BY
    dept.department_name,
    average_rating DESC NULLS LAST;


-- Additional performance report:
-- Top 10 employees by average performance rating.

SELECT
    e.employee_id,
    e.first_name,
    e.last_name,
    COUNT(f.rating) AS rated_reviews,
    ROUND(AVG(f.rating), 2) AS average_rating
FROM dw.fact_performance f
JOIN dw.dim_employee e
    ON e.employee_key = f.employee_key
GROUP BY
    e.employee_key,
    e.employee_id,
    e.first_name,
    e.last_name
HAVING COUNT(f.rating) > 0
ORDER BY average_rating DESC, rated_reviews DESC
LIMIT 10;


-- ============================================================
-- 5. EMPLOYEE SALARY GROWTH
-- Business question:
-- How much has each employee's salary changed between
-- their earliest and latest salary records?
-- ============================================================

WITH salary_history AS (
    SELECT
        fs.employee_key,
        fs.salary_amount,
        d.full_date AS effective_date,

        ROW_NUMBER() OVER (
            PARTITION BY fs.employee_key
            ORDER BY d.full_date ASC, fs.salary_fact_key ASC
        ) AS first_record,

        ROW_NUMBER() OVER (
            PARTITION BY fs.employee_key
            ORDER BY d.full_date DESC, fs.salary_fact_key DESC
        ) AS last_record

    FROM dw.fact_salary fs
    JOIN dw.dim_date d
        ON d.date_key = fs.effective_date_key
),
first_salary AS (
    SELECT employee_key, salary_amount, effective_date
    FROM salary_history
    WHERE first_record = 1
),
latest_salary AS (
    SELECT employee_key, salary_amount, effective_date
    FROM salary_history
    WHERE last_record = 1
)
SELECT
    e.employee_id,
    e.first_name,
    e.last_name,

    first_s.effective_date AS first_salary_date,
    first_s.salary_amount AS initial_salary,

    latest_s.effective_date AS latest_salary_date,
    latest_s.salary_amount AS latest_salary,

    latest_s.salary_amount - first_s.salary_amount
        AS salary_increase,

    ROUND(
        100.0 * (
            latest_s.salary_amount - first_s.salary_amount
        ) / NULLIF(first_s.salary_amount, 0),
        2
    ) AS salary_growth_percent

FROM first_salary first_s
JOIN latest_salary latest_s
    ON latest_s.employee_key = first_s.employee_key
JOIN dw.dim_employee e
    ON e.employee_key = first_s.employee_key
ORDER BY salary_growth_percent DESC NULLS LAST;


-- ============================================================
-- 6. DEPARTMENT HEADCOUNT
-- Business question:
-- How many employees currently belong to each department?
--
-- Uses staging employee assignments because the current
-- dim_employee schema does not store department_id.
-- ============================================================

SELECT
    dept.department_name,
    COUNT(e.employee_id) AS total_employees,

    COUNT(*) FILTER (
        WHERE e.termination_date IS NULL
    ) AS employees_without_termination_date,

    COUNT(*) FILTER (
        WHERE e.termination_date IS NOT NULL
    ) AS employees_with_termination_date

FROM stg.employees e
JOIN dw.dim_department dept
    ON dept.department_id = e.department_id
GROUP BY dept.department_id, dept.department_name
ORDER BY total_employees DESC;


