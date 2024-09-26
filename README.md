# CVMFS client Continuous Benchmark CI

Author: **Konrad Kotlicki**

## Table of Contents

1. [Project Overview](#project-overview)
2. [Prerequisites](#prerequisites)
3. [Server Node](#server-node)
    - [Server Installation](#server-installation)
    - [Manage the Server Service](#manage-the-server-service)
    - [Run the Server Manually without service](#run-the-server-manually-without-service)
    - [Server Requirements](#server-requirements)
    - [Server Project Structure](#server-project-structure)
4. [Benchmark Node](#benchmark-node)
    - [Benchmark Installation](#benchmark-installation)
    - [Manage the Benchmark Service](#manage-the-benchmark-service)
    - [Run the Benchmark Workflow on Demand](#run-the-benchmark-workflow-on-demand)
    - [Benchmark Requirements](#benchmark-requirements)
    - [Benchmark Project Structure](#benchmark-project-structure)
5. [Server Development](#server-development)

## Project Overview

This project sets up a Continuous Integration (CI) benchmarking system split across two AlmaLinux 9 (Alma9) x86-64 nodes:

- **Server node:** Hosts the benchmark server application. The website is hosted available under the node's local network ip with port that is by default `5000`.
    - Example path for the root (website visualization) `192.168.1.1:5000`
- **Benchmark node:** Runs benchmarking tasks and sends results to the server.

## Prerequisites

Before proceeding with the installation, ensure you have the following:

- **Operating System:** AlmaLinux 9 (x86-64 architecture) sourced from the CERN repository.
- **User Privileges:** Access to a `root`-named user with superuser privileges on both nodes.
- **Network Configuration:** Both nodes should be connected within the same local network, allowing communication between them.

## Server Node

### Server Installation

Follow these steps to set up the server node:

1. **Copy the Server Project Source:**

2. **Configure the Server:**

    - Modify the `.env` file to set the `ALLOWED_IP` environment variable to the IP address of the benchmark node:
      ```env
      ALLOWED_IP=192.168.1.1
      ```
      *(Replace `192.168.1.1` with the actual IP of your benchmark node.)*

3. **Install and Start the Server Project:**

    - Copy the `setup_server.sh` script to the `/root/` directory and execute it.
    - (Optional) To install the project without starting the service, comment out the lines below `### Service start:` in the `setup_server.sh` script.

### Manage the Server Service

- **Stop the Service:**
    ```bash
    sudo systemctl stop benchmark_server
    ```
- **Restart the Service:**
    ```bash
    sudo systemctl restart benchmark_server
    ```

### Run the Server Manually without service

```bash
/root/benchmark_server/benchmark_venv/bin/python /root/benchmark_server/app.py
```

### Server Requirements

All requirements are installed by `setup` scripts. There is no need to install any manually.

**System Packages:**
```bash
dnf install -y python3 virtualenv
```

**Python Packages:** 
```bash
python3 -m pip install pandas flask gunicorn python-dotenv
```

### Server Project Structure

```bash
/root/benchmark_server/
├── app.py
├── benchmark_server.service
├── db_definition.sql
├── static
│   ├── favicon.svg
│   ├── index.js
│   └── js
│       └── plotly-2.34.0.min.js
├── templates
│   └── index.html
└── benchmark_venv/
    └── ... (virtual environment files)
```

**File Explanations:**

- **app.py** - Main application script that runs the Flask server.
- **benchmark_server.service** - Systemd service file to manage the benchmark server as a background service.
- **db_definition.sql** - SQL script for setting up the database schema.
- **static/** - Directory containing static assets like images and JavaScript files.
- **index.js** - Main JavaScript file for frontend interactions.
- **index.html** - Main HTML page served by the Flask app.
- **benchmark_venv/** - Python virtual environment containing all installed dependencies.


## Benchmark Node

### Benchmark Installation

Follow these steps to set up the benchmark node.

1. **Copy the Benchmark Project Source:**

    - **Action:** Copy the `auto_benchmark` folder to the `/root/` directory.
    - **Command:**
      ```bash
      cp -r auto_benchmark /root/
      ```

2. **Configure the Benchmark node:**

    - **Action:** Modify the `benchmark.yaml` file to set the `server_url` key to the IP address of the server node.
    - **Default Configuration:**
      ```yaml
      server_url: http://192.168.1.1:5000
      ```
      *(Replace `http://192.168.1.1:5000` with the actual IP and port of your server node.)*

3. **Install and Start the Benchmark Project:**

    - **Optional:** To install the project without starting the service, comment out the lines below `### Service start:` in the `setup_bench.sh` script.
    - **Action:** Copy the `setup_bench.sh` script to the `/root/` directory and execute it.
    - **Commands:**
      ```bash
      cp setup_bench.sh /root/
      cd /root/
      chmod +x setup_bench.sh
      ./setup_bench.sh
      ```

---

### Manage the Benchmark Service

- **Stop the Service:**
    ```bash
    sudo systemctl stop crond
    ```
- **Restart the Service:**
    ```bash
    sudo systemctl restart crond
    ```
    *(Use with caution, as this affects all cron jobs on the system.)*

### Run the Benchmark Workflow on Demand

```bash
/root/auto_benchmark/run_bench.sh
```

---

### Benchmark Requirements

System Packages:

```bash
dnf install -y htop \
               autofs zlib-devel libcap-devel httpd attr usbutils buildah \
               git cmake gcc gcc-c++ ninja-build golang \
               openssl-devel bzip2 libuuid-devel \
               vim patch fuse fuse-devel \
               python3 valgrind python3-devel unzip meson virtualenv \
               fuse3 fuse3-devel \
               python-unversioned-command time
```

CERN `HEP_OS` Repository Setup:

```bash
yum install -y https://linuxsoft.cern.ch/wlcg/el9/x86_64/wlcg-repo-1.0.0-1.el9.noarch.rpm
yum install -y HEP_OSlibs
```

Python Packages:

```bash
python3 -m pip install requests pyyaml pandas tqdm argcomplete matplotlib
```

---

### Benchmark Project Structure

```bash
/root/auto_benchmark/
├── benchmark.yaml
├── check_benchmarks.py
├── common_configs
│   ├── config_benchmark_template.yaml
│   └── config_visualization_template.yaml
├── generate_benchmark_configs.py
├── run_bench.sh
├── upload_benchmark_data.py
└── benchmark_venv/
    └── ... (virtual environment files)
```

**File Explanations:**

- **run_bench.sh** - Shell script to execute the benchmarking workflow.
- **benchmark.yaml:** - Configuration file containing settings like `server_url` and benchmark parameters.
- **check_benchmarks.py** - Script to verify the integrity and performance of benchmark results.
- **common_configs/** - Directory containing template configuration files.
- **generate_benchmark_configs.py** - Script to generate specific benchmark configuration files based on templates.
- **upload_benchmark_data.py** - Script to upload benchmark results to the server.
- **benchmark_venv/** - Python virtual environment containing all installed dependencies.

## Server Development

- To modify website structure, change `<body/>` section in `index.html`
- To modify the graphs, change in `index.js` either `createLinePlotCustom()` or `createBoxPlotCustom()`. For changes inside these functions not involving graph's input data modifications the easiest approach for customization is to change options in two sections according to `plotly.js` documentation:
    - `const layout = {}` - [Layout Refference](https://plotly.com/javascript/reference/layout/), [Configuration Refference](https://plotly.com/javascript/configuration-options/)
    - `Plotly.newPlot()` - [Functions Refference](https://plotly.com/javascript/plotlyjs-function-reference/#plotlynewplot)
