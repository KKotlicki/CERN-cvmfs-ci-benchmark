import subprocess
import requests
import logging
import yaml
import os
import sys
from datetime import datetime, timedelta
from requests.exceptions import RequestException

log_file_path = "/root/auto_benchmark/check_benchmarks.log"
logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

API_ENDPOINT = "api/benchmark_combinations"
MAX_COMMITS = 10

def get_commits_from_repo():
    """Fetch all commits from the local Git repository."""
    try:
        logging.info("Fetching commits from the local git repository...")
        result = subprocess.run(['git', 'log', 'origin/devel', '-n', '100', '--pretty=format:%H %ci'], 
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            commits = [line.split()[0] for line in result.stdout.strip().split('\n')]
            commit_dates = [line.split()[1] for line in result.stdout.strip().split('\n')]
            logging.info(f"Fetched {len(commits)} commits from the repository.")
            return commits, commit_dates
        else:
            logging.error(f"Error fetching commits: {result.stderr}")
            return None, None
    except Exception as e:
        logging.error(f"Error running git command: {e}")
        return None, None

def load_benchmark_config(config_path=None):
    """Load benchmark configurations from the benchmark.yaml file."""
    if config_path is None:
        config_path = os.path.expanduser("~/auto_benchmark/benchmark.yaml")
    
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            logging.info(f"Loaded benchmark configuration from {config_path}")
            return config
    except Exception as e:
        logging.error(f"Error loading benchmark configuration: {e}")
        return None

def send_benchmark_request(commit_hash, config):
    """Send a POST request to check if the commit has all configurations benchmarked."""
    try:
        configurations = [
            {"client_config": client_config, "command": command, "metric": metric}
            for client_config in config['client_configs']
            for command in config['commands']
            for metric in config['metrics'] + config['internal_affairs_metrics']
        ]
        payload = {
            "commit": commit_hash,
            "configurations": configurations
        }
        logging.info(f"Sending request to {config.get('server_url')}/{API_ENDPOINT} with payload: {payload}")
        
        response = requests.post(f"{config.get('server_url')}/{API_ENDPOINT}", json=payload)
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        logging.error(f"Error checking benchmark combinations: {e}")
        return []

def find_commits_to_benchmark(commits, commit_dates, config):
    """Find commits that need benchmarking, considering the time period and configuration combinations."""
    logging.info("Searching for the next commits that need benchmarking...")
    
    today = datetime.now()
    last_monday = today - timedelta(days=today.weekday() + 7)

    commits_to_benchmark = []
    new_commits = []
    historical_commit_to_benchmark = None

    commits_and_dates = sorted(zip(commits, commit_dates), key=lambda x: x[1], reverse=True)

    for commit, commit_date in commits_and_dates:
        commit_datetime = datetime.strptime(commit_date, '%Y-%m-%d')
        
        if commit_datetime >= last_monday:
            new_commits.append(commit)
            missing_combinations = send_benchmark_request(commit, config)
            if missing_combinations:
                logging.info(f"Found a recent commit {commit} that needs benchmarking: {missing_combinations}")
                commits_to_benchmark.append(commit)
                if len(commits_to_benchmark) >= MAX_COMMITS:
                    break

    if not commits_to_benchmark:
        for commit, commit_date in commits_and_dates:
            if commit not in new_commits:
                missing_combinations = send_benchmark_request(commit, config)
                if missing_combinations:
                    logging.info(f"Found historical commit {commit} that needs benchmarking.")
                    historical_commit_to_benchmark = commit
                    break

    if commits_to_benchmark:
        logging.info(f"Found {len(commits_to_benchmark)} recent commits that need benchmarks.")
        return list(set(commits_to_benchmark))[:MAX_COMMITS]
    elif historical_commit_to_benchmark:
        logging.info(f"Returning one most recent historical commit for benchmarking: {historical_commit_to_benchmark}")
        return [historical_commit_to_benchmark]
    else:
        logging.info("No commits need benchmarking.")
        return []

if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else None

    logging.info("Starting check_benchmarks.py script.")
    
    config = load_benchmark_config(config_path)
    if config is None:
        logging.error("Error loading benchmark configuration. Exiting script.")
        print("ERROR_LOADING_CONFIG")
        exit(1)

    commits, commit_dates = get_commits_from_repo()
    if not commits:
        logging.error("Error fetching commits. Exiting script.")
        print("ERROR_FETCHING_COMMITS")
        exit(1)

    next_commits = find_commits_to_benchmark(commits, commit_dates, config)

    if next_commits:
        logging.info(f"Next commits to benchmark: {next_commits}")
        print(' '.join(next_commits))
    else:
        logging.info("No benchmark needed. Exiting.")
        print("NO_BENCHMARK_NEEDED")

    logging.info("Finished check_benchmarks.py script.")
