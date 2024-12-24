import psycopg2
import time
import csv
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# You can optionally use pandas for EDA:
import pandas as pd

# ============== DB CONFIGURATIONS ==============
LOCAL_DB = {
    "host": "localhost",
    "port": 5432,
    "dbname": "postgres",
    "user": "postgres",
    "password": "postgres"
}

AWS_DB = {
    "host": "",
    "port": 5432,
    "dbname": "postgres",
    "user": "postgres",
    "password": ""
}

TABLE_NAME = "bank_transactions"
CSV_FILE = "bankdataset.csv"

# ============== LOGGING CONFIGURATION ==============
# Create a logs directory if it doesn't exist
if not os.path.exists("logs"):
    os.makedirs("logs")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Log to console
        logging.FileHandler("logs/data_pipeline.log", mode='a', encoding='utf-8')  # Log to file
    ]
)

logger = logging.getLogger(__name__)


def get_connection(db_config):
    """Establishes a psycopg2 connection with given config and returns it."""
    try:
        conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            dbname=db_config["dbname"],
            user=db_config["user"],
            password=db_config["password"]
        )
        return conn
    except Exception as e:
        logger.error(f"Error establishing DB connection: {e}")
        raise  # Re-raise to stop execution if DB connection fails


def create_table_if_not_exists(db_config):
    """Creates a table if it doesn't already exist."""
    create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id SERIAL PRIMARY KEY,
            date DATE,
            domain VARCHAR(255),
            location VARCHAR(255),
            value NUMERIC,
            transaction_count INT
        );
    """
    conn = None
    try:
        conn = get_connection(db_config)
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute(create_table_query)
        logger.info(f"Table '{TABLE_NAME}' checked/created in DB {db_config['host']}.")
        cursor.close()
    except Exception as e:
        logger.error(f"Error creating table '{TABLE_NAME}' in DB {db_config['host']}: {e}")
        raise
    finally:
        if conn:
            conn.close()


def exploratory_data_analysis(csv_path):
    """
    Simple EDA function using pandas. 
    Checks for missing data, duplicates, and basic stats.
    """
    try:
        df = pd.read_csv(csv_path)
        logger.info("=== EDA START ===")
        
        # Basic shape
        logger.info(f"DataFrame shape: {df.shape}")

        # Columns and dtypes
        logger.info("Columns and dtypes:\n" + str(df.dtypes))

        # Check for missing values
        missing = df.isnull().sum()
        logger.info("Missing values per column:\n" + str(missing))

        # Check for duplicates based on all columns
        duplicates_count = df.duplicated().sum()
        logger.info(f"Number of duplicate rows: {duplicates_count}")

        # Basic statistics (numeric columns)
        numeric_cols = df.select_dtypes(include=['int64', 'float64'])
        logger.info("Numeric columns describe:\n" + str(numeric_cols.describe()))

        logger.info("=== EDA END ===")

    except Exception as e:
        logger.error(f"Error during EDA on {csv_path}: {e}")
        raise


def load_csv_to_db(db_config, csv_path):
    """
    Loads data from CSV into the specified DB table.
    Returns the number of rows inserted.
    """
    conn = None
    row_count = 0
    try:
        conn = get_connection(db_config)
        cursor = conn.cursor()
        
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=',')
        
            
            cursor.execute(f"TRUNCATE TABLE {TABLE_NAME};")
            
            insert_query = f"""
                INSERT INTO {TABLE_NAME} (date, domain, location, value, transaction_count)
                VALUES (%s, %s, %s, %s, %s);
            """
            
            for row in reader:

                if row_count >= 10000:
                    break

                date_ = row['Date']         # e.g. '1/1/2022'
                domain = row['Domain']      # e.g. 'RESTRAUNT'
                location = row['Location']  # e.g. 'Bhuj'
                value = row['Value']        # e.g. '365554'
                txn_count = row['Transaction_count']  # e.g. '1932'
                
                # Convert date if needed (Postgres usually handles MM/DD/YYYY fine)
                cursor.execute(insert_query, (date_, domain, location, value, txn_count))
                row_count += 1
                if row_count % 1000 == 0:
                    logger.info(f"Inserted {row_count} rows...")

        conn.commit()
        logger.info(f"Inserted {row_count} rows into table '{TABLE_NAME}' in DB {db_config['host']}.")
        cursor.close()
    except Exception as e:
        logger.error(f"Error loading CSV into DB {db_config['host']}: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

    return row_count


def query_test(db_config):
    """
    Runs a sample query (e.g., total row count).
    Returns the time taken and the result.
    """
    conn = None
    try:
        conn = get_connection(db_config)
        cursor = conn.cursor()
        start_time = time.time()
        
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME};")
        result = cursor.fetchone()[0]
        
        end_time = time.time()
        elapsed = end_time - start_time
        cursor.close()
        return elapsed, result
    except Exception as e:
        logger.error(f"Error running query in DB {db_config['host']}: {e}")
        raise
    finally:
        if conn:
            conn.close()


def concurrent_query_test(db_config, n_threads=5):
    """
    Runs multiple queries in parallel to test concurrency.
    Returns a list of (query_time, row_count_result) for each thread.
    """
    results = []
    
    def worker():
        return query_test(db_config)
    
    with ThreadPoolExecutor(max_workers=n_threads) as executor:
        futures = [executor.submit(worker) for _ in range(n_threads)]
        for future in as_completed(futures):
            try:
                results.append(future.result())  # Each result is (elapsed_time, row_count)
            except Exception as e:
                logger.error(f"Concurrent query failed: {e}")
                results.append((None, None))
    
    return results


def main():
    #============== STEP 1: EDA ==============
    logger.info(f"Starting EDA for file: {CSV_FILE}")
    exploratory_data_analysis(CSV_FILE)
    
    # ============== CREATE TABLES ==============
    logger.info("Creating table in Local DB if not exists...")
    create_table_if_not_exists(LOCAL_DB)

    logger.info("Creating table in AWS DB if not exists...")
    create_table_if_not_exists(AWS_DB)

    # ============== LOAD CSV TO DB ==============
    logger.info("\n--- LOADING CSV DATA ---")
    
    # Local
    start_local_load = time.time()
    local_rows = load_csv_to_db(LOCAL_DB, CSV_FILE)
    end_local_load = time.time()
    logger.info(f"Loaded {local_rows} rows into LOCAL DB in {end_local_load - start_local_load:.4f} seconds.")
    
    # AWS
    start_aws_load = time.time()
    aws_rows = load_csv_to_db(AWS_DB, CSV_FILE)
    end_aws_load = time.time()
    logger.info(f"Loaded {aws_rows} rows into AWS DB in {end_aws_load - start_aws_load:.4f} seconds.")

    #============== SINGLE QUERY TEST ==============
    logger.info("\n--- SINGLE QUERY TEST ---")
    
    local_time, local_count = query_test(LOCAL_DB)
    logger.info(f"Local DB - Single Query Time: {local_time:.4f}s, Row Count: {local_count}")
    
    aws_time, aws_count = query_test(AWS_DB)
    logger.info(f"AWS DB - Single Query Time: {aws_time:.4f}s, Row Count: {aws_count}")

    # ============== CONCURRENT QUERY TESTS ==============
    logger.info("\n--- CONCURRENT QUERY TESTS ---")

    # Test concurrency with these different thread counts
    thread_counts = [1, 2, 3, 5, 8, 10, 15, 20, 30, 50]

    for t in thread_counts:
        logger.info(f"\nRunning concurrent queries with {t} threads...")

        # Local concurrency test
        local_concurrent_results = concurrent_query_test(LOCAL_DB, n_threads=t)
        local_times = [res[0] for res in local_concurrent_results if res[0] is not None]
        if local_times:
            local_avg = sum(local_times) / len(local_times)
            logger.info(f"Local DB - {t} Threads - Average Query Time: {local_avg:.4f}s")
        else:
            logger.warning(f"No valid local concurrency results for {t} threads.")

        # AWS concurrency test
        aws_concurrent_results = concurrent_query_test(AWS_DB, n_threads=t)
        aws_times = [res[0] for res in aws_concurrent_results if res[0] is not None]
        if aws_times:
            aws_avg = sum(aws_times) / len(aws_times)
            logger.info(f"AWS DB - {t} Threads - Average Query Time: {aws_avg:.4f}s")
        else:
            logger.warning(f"No valid AWS concurrency results for {t} threads.")


if __name__ == "__main__":
    main()
