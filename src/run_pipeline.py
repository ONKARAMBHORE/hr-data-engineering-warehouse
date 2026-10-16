# File: src/run_pipeline.py

import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path


# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "etl_pipeline.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


# --------------------------------------------------
# 2. PIPELINE STAGES
# --------------------------------------------------

PIPELINE_STAGES = [
    ("Clean HR datasets", "src/clean_data.py"),
    ("Verify cleaned datasets", "src/verify_cleaned_data.py"),
    ("Validate cleaned datasets", "src/validate_data.py"),
    (
        "Incremental staging and warehouse load",
        "src/incremental_load.py",
    ),
    (
        "Warehouse data quality checks",
        "src/warehouse_data_quality.py",
    ),
]

# --------------------------------------------------
# 3. EXECUTE ONE STAGE
# --------------------------------------------------

def run_stage(stage_name, script_relative_path):
    script_path = PROJECT_ROOT / script_relative_path

    if not script_path.exists():
        raise FileNotFoundError(
            f"Required pipeline script not found: {script_path}"
        )

    logger.info("=" * 65)
    logger.info("STARTING STAGE: %s", stage_name)
    logger.info("SCRIPT: %s", script_relative_path)

    subprocess.run(
        [sys.executable, str(script_path)],
        cwd=PROJECT_ROOT,
        check=True,
    )

    logger.info("STAGE COMPLETED: %s", stage_name)


# --------------------------------------------------
# 4. RUN FULL ETL PIPELINE
# --------------------------------------------------

def main():
    start_time = datetime.now()

    logger.info("=" * 65)
    logger.info("HR DATA ENGINEERING ETL PIPELINE STARTED")
    logger.info("Start time: %s", start_time.isoformat(timespec="seconds"))
    logger.info("Project root: %s", PROJECT_ROOT)

    try:
        for stage_name, script_path in PIPELINE_STAGES:
            run_stage(stage_name, script_path)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info("=" * 65)
        logger.info("ETL PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("End time: %s", end_time.isoformat(timespec="seconds"))
        logger.info("Duration: %.2f seconds", duration)
        logger.info("Log file: %s", LOG_FILE)

    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        logger.exception("ETL PIPELINE FAILED")
        logger.error("Failure details: %s", exc)
        logger.error(
            "Pipeline stopped. Fix the failed stage before rerunning."
        )
        sys.exit(1)

    except Exception:
        logger.exception("Unexpected ETL pipeline error")
        sys.exit(1)


if __name__ == "__main__":
    main()