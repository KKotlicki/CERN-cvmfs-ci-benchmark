#!/bin/bash

LOGFILE="/root/auto_benchmark/cron.log"
LOCKFILE="/tmp/run_bench.lock"

echo "Script started at $(date)" >>$LOGFILE

if [ -e "${LOCKFILE}" ]; then
    echo "Script is already running." >>$LOGFILE
    exit 1
fi

touch "${LOCKFILE}"

cleanup() {
    rm -f "${LOCKFILE}"
    echo "Lock file removed" >>$LOGFILE
    echo "Script finished at $(date)" >>$LOGFILE
}
trap cleanup EXIT

timeout_handler() {
    echo "(error) $(date): Script exceeded time limit and was stopped" >>$LOGFILE
    exit 2
}

logfile="/root/benchmark_results/$(date +"%y%m%d%H%M").log"
exec >/dev/null 2>&1

error_handler() {
    echo "(error) $(date): Script encountered an error, stopping execution" >>"${logfile}"
    echo "(error) $(date): Script encountered an error, stopping execution" >>$LOGFILE
    exit 3
}

trap 'error_handler' ERR
trap 'timeout_handler' SIGTERM

log_command() {
    start_time=$(date +%s)
    echo "Running: $*" >>$LOGFILE
    "$@"
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    echo "Completed: $* in ${duration} seconds" >>$LOGFILE
}

echo "Benchmark started at $(date)" >>$LOGFILE

cd /root/auto_benchmark/cvmfs-devel-current/build || exit

git fetch origin devel

# Get the list of commits to benchmark
next_commits=$(/root/auto_benchmark/benchmark_venv/bin/python /root/auto_benchmark/check_benchmarks.py)

if [ "$next_commits" = "NO_BENCHMARK_NEEDED" ]; then
    echo "No benchmark needed. Exiting." >>$LOGFILE
    exit 0
fi

# Convert space-separated commit list into an array
IFS=' ' read -r -a commit_array <<< "$next_commits"

for next_commit in "${commit_array[@]}"; do
    echo "Processing commit: ${next_commit}" >>$LOGFILE

    if [ -d "/root/benchmark_results/${next_commit}" ]; then
        echo "Removing existing result directory: /root/benchmark_results/${next_commit}" >>$LOGFILE
        rm -rf "/root/benchmark_results/${next_commit}"
    fi

    log_command git checkout "${next_commit}"
    log_command ninja

    result_dir="/root/benchmark_results/${next_commit}"
    mkdir -p "${result_dir}"

    log_command /root/auto_benchmark/benchmark_venv/bin/python /root/auto_benchmark/generate_benchmark_configs.py "${next_commit}" "${result_dir}"

    rm -f /root/benchmark_results/results.csv

    cd /root/auto_benchmark/cvmfs-benchmark-release/test/performance-benchmark/client/ || exit
    config_bench_file="${result_dir}/config-bench.yaml"
    log_command /root/auto_benchmark/benchmark_venv/bin/python /root/auto_benchmark/cvmfs-benchmark-release/test/performance-benchmark/client/start_benchmark.py -c "${config_bench_file}"

    config_visual_file="${result_dir}/config-visual.yaml"
    log_command /root/auto_benchmark/benchmark_venv/bin/python /root/auto_benchmark/cvmfs-benchmark-release/test/performance-benchmark/client/start_visualization.py -c "${config_visual_file}"

    log_command /root/auto_benchmark/benchmark_venv/bin/python /root/auto_benchmark/upload_benchmark_data.py
done

echo "Completed all benchmarks." >>$LOGFILE
