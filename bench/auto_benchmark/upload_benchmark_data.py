import requests
import os
import logging
import pandas as pd
import yaml

# Set up logging
log_file_path = "/root/auto_benchmark/upload_benchmark_data.log"
logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

csv_file_path = "/root/benchmark_results/results.csv"
processed_csv_path = "/root/benchmark_results/processed_results.csv"
upload_endpoint = "api/insert_data"
benchmark_config_path = "/root/auto_benchmark/benchmark.yaml"

def load_benchmark_config(config_path):
    """Load the benchmark configuration from YAML."""
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        logging.info(f"Loaded benchmark configuration from {config_path}")
        return config
    except Exception as e:
        logging.error(f"Failed to load benchmark configuration: {e}")
        return None

def process_csv(file_path, processed_file_path):
    """Process the CSV file to clean and prepare for upload."""
    try:
        df = pd.read_csv(file_path)

        # Strip any leading or trailing whitespace from the column names and values
        df.columns = df.columns.str.strip()
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

        # Remove 'sft.cern.ch_' prefix from 'metric' column
        df['metric'] = df['metric'].str.replace('^sft\.cern\.ch_', '', regex=True)

        # Ensure the expected columns are present
        required_columns = ['tag', 'command_label', 'build_name', 'client_config', 'metric']
        for col in required_columns:
            if col not in df.columns:
                logging.error(f"Missing required column: {col}")
                return None

        # Rename columns for consistency
        df.rename(columns={'tag': 'datetime', 'command_label': 'command'}, inplace=True)

        # Remove unnecessary columns if they exist
        columns_to_drop = ['threads', 'run_id', 'repetitions']
        existing_columns_to_drop = [col for col in columns_to_drop if col in df.columns]
        df.drop(columns=existing_columns_to_drop, inplace=True)

        # Split 'build_name' into 'version' and 'commit'
        df[['version', 'commit']] = df['build_name'].str.rsplit('-', n=1, expand=True)
        df.drop(columns=['build_name'], inplace=True)

        # Add 'build_type' column with value 'automatic'
        df['build_type'] = 'automatic'

        # Round all cache-related data to 2 decimal places
        cache_columns = [
            'cold_cache_min_val', 'cold_cache_first_quartile', 'cold_cache_median',
            'cold_cache_third_quartile', 'cold_cache_max_val', 'warm_cache_min_val',
            'warm_cache_first_quartile', 'warm_cache_median', 'warm_cache_third_quartile',
            'warm_cache_max_val', 'hot_cache_min_val', 'hot_cache_first_quartile',
            'hot_cache_median', 'hot_cache_third_quartile', 'hot_cache_max_val'
        ]
        df[cache_columns] = df[cache_columns].applymap(lambda x: round(x, 2) if pd.notnull(x) else x)

        # Save the processed DataFrame to a new CSV file
        df.to_csv(processed_file_path, index=False)
        logging.info(f"Processed CSV saved to {processed_file_path}")
        return df

    except Exception as e:
        logging.error(f"Error processing CSV file {file_path}: {e}")
        return None

def upload_csv(file_path, upload_url):
    """Upload the entire processed CSV."""
    if not os.path.isfile(file_path):
        logging.error(f"Error: File {file_path} does not exist.")
        return
    
    df = process_csv(file_path, processed_csv_path)
    if df is None:
        logging.error(f"CSV processing failed for {file_path}.")
        return

    # Upload the entire processed CSV file
    try:
        with open(processed_csv_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(upload_url, files=files)
            if response.status_code == 201:
                logging.info("Processed CSV uploaded successfully.")
            else:
                logging.error(f"Failed to upload CSV: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Failed to upload CSV: {e}")

if __name__ == "__main__":
    logging.info("Starting the benchmark data upload script.")
    config = load_benchmark_config(benchmark_config_path)
    if config:
        upload_csv(csv_file_path, f"{config.get('server_url')}/{upload_endpoint}")
    logging.info("Finished running the benchmark data upload script.")
