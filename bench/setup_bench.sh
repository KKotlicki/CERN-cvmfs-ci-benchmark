#!/bin/bash

set -e

PROJ_ROOT="/root/auto_benchmark"
dnf update -y

# Install necessary packages
dnf install -y htop \
               autofs zlib-devel libcap-devel httpd attr usbutils buildah \
               git cmake gcc gcc-c++ ninja-build golang \
               openssl-devel bzip2 libuuid-devel \
               vim patch fuse fuse-devel \
               python3 valgrind python3-devel unzip meson virtualenv \
               fuse3 fuse3-devel \
               python-unversioned-command time

# Install CERN WLCG repository and HEP_OSlibs
yum install -y https://linuxsoft.cern.ch/wlcg/el9/x86_64/wlcg-repo-1.0.0-1.el9.noarch.rpm
yum install -y HEP_OSlibs

# Set up Python virtual environment and install Python packages
cd "${PROJ_ROOT}"
python -m venv benchmark_venv
"${PROJ_ROOT}/benchmark_venv/bin/python" -m pip install --upgrade pip
"${PROJ_ROOT}/benchmark_venv/bin/python" -m pip install requests pyyaml pandas tqdm argcomplete matplotlib

# Create directory for benchmark results
mkdir -p /root/benchmark_results

# Clone necessary repositories
git clone https://github.com/cvmfs/cvmfs.git cvmfs-devel-current
git clone https://github.com/HereThereBeDragons/cvmfs.git cvmfs-benchmark-release

# Checkout specific commit for benchmarking
cd "${PROJ_ROOT}/cvmfs-benchmark-release"
git checkout e712f3ff4d4020c94d2a40e6d699ed56b040c3fc

# Build cvmfs-devel-current with CMake and Ninja
mkdir -p "${PROJ_ROOT}/cvmfs-devel-current/build"
cd "${PROJ_ROOT}/cvmfs-devel-current/build"
cmake -G Ninja ../
ninja
ninja install

# Setup cvmfs configuration
cvmfs_config setup

chmod +x "${PROJ_ROOT}/run_bench.sh"

### Service start:

CRON_SCHEDULE="0 0 * * 1"
CRON_COMMAND="${PROJ_ROOT}/run_bench.sh"
CRON_IDENTIFIER="# run_bench_cron_job"

( printf "%s\n" "${CRON_SCHEDULE} ${CRON_COMMAND} ${CRON_IDENTIFIER}" ) | crontab -
echo "Cron job added to run run_bench.sh every Monday"

systemctl enable --now crond
echo "Benchmark crond service is enabled and running."
