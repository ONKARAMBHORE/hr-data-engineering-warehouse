-- HR Data Engineering Project
-- Phase 7: PostgreSQL staging schema

CREATE SCHEMA IF NOT EXISTS stg;

-- The Python loader creates/reloads the seven staging tables
-- from the cleaned CSV files in data/processed/.