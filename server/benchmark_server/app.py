from flask import Flask, render_template, request, jsonify, make_response, abort
import sqlite3
import pandas as pd
import io
import logging
import os
from dotenv import load_dotenv

load_dotenv()
ALLOWED_IP = os.getenv('ALLOWED_IP')

app = Flask(__name__)

# Set up logging
log_file_path = os.path.join(os.path.dirname(__file__), 'benchmark_server.log')
logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'benchmarks.db')
DB_DEFINITION = os.path.join(BASE_DIR, 'db_definition.sql')

# Create the database if it doesn't exist
if not os.path.exists(DATABASE):
    try:
        if not os.path.exists(DB_DEFINITION):
            logging.error(f"Database definition file not found at {DB_DEFINITION}")
            raise FileNotFoundError(f"Database definition file not found at {DB_DEFINITION}")

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        with open(DB_DEFINITION, 'r') as f:
            sql_script = f.read()

        # Execute the SQL script
        cursor.executescript(sql_script)
        conn.commit()
        conn.close()
        logging.info("Database created successfully using db_definition.")
    except Exception as e:
        logging.error(f"Failed to create database: {e}")
        raise
else:
    logging.info("Database already exists.")

def get_db_connection():
    try:
        conn = sqlite3.connect(DATABASE)
        return conn
    except Exception as e:
        logging.error(f"Failed to connect to database: {e}")
        raise

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/insert_data', methods=['POST'])
def insert_data():
    client_ip = request.remote_addr
    if client_ip != ALLOWED_IP:
        logging.warning(f"Unauthorized access attempt from IP: {client_ip}")
        abort(403)  # Forbidden

    file = request.files['file']
    if not file:
        logging.error("No file part in the request")
        return "No file part in the request", 400

    if file.filename == '':
        logging.error("No selected file")
        return "No selected file", 400

    if file and file.filename.endswith('.csv'):
        logging.info(f"Received file: {file.filename}")
        try:
            # Read the CSV into a pandas DataFrame
            df = pd.read_csv(file)
            df.columns = df.columns.str.strip()  # Strip whitespace from column names

            logging.debug(f"CSV DataFrame shape: {df.shape}")
            logging.debug(f"CSV DataFrame columns: {df.columns.tolist()}")

            conn = get_db_connection()
            cursor = conn.cursor()

            for _, row in df.iterrows():
                logging.debug(f"Processing row: {row.to_dict()}")

                # Insert or select Command, ClientConfig, Metric, and CVMFSBuild
                cursor.execute('INSERT OR IGNORE INTO "Command" ("command_name", "command_content") VALUES (?, ?)', 
                               (row['command'].strip(), row['command'].strip()))
                command_id = cursor.execute('SELECT "id" FROM "Command" WHERE "command_name" = ?', 
                                            (row['command'].strip(),)).fetchone()[0]

                cursor.execute('INSERT OR IGNORE INTO "ClientConfig" ("config_name", "config_content") VALUES (?, ?)', 
                               (row['client_config'].strip(), row['client_config'].strip()))
                client_config_id = cursor.execute('SELECT "id" FROM "ClientConfig" WHERE "config_name" = ? AND "config_content" = ?', 
                                                  (row['client_config'].strip(), row['client_config'].strip())).fetchone()[0]

                cursor.execute('INSERT OR IGNORE INTO "Metric" ("metric_name", "metric_description") VALUES (?, ?)', 
                               (row['metric'].strip(), row['metric'].strip()))
                metric_id = cursor.execute('SELECT "id" FROM "Metric" WHERE "metric_name" = ?', 
                                           (row['metric'].strip(),)).fetchone()[0]

                cursor.execute('''
                    INSERT OR IGNORE INTO "CVMFSBuild" ("commit", "commit_datetime", "version", "tag", "build_type")
                    VALUES (?, ?, ?, ?, ?)
                ''', (row['commit'].strip(), row['datetime'], row['version'].strip(), None, 'automatic'))
                cvmfs_build_id = cursor.execute('SELECT "id" FROM "CVMFSBuild" WHERE "commit" = ?', 
                                                (row['commit'].strip(),)).fetchone()[0]

                # Check if BenchmarkResult exists
                cursor.execute('''
                    SELECT "id" FROM "BenchmarkResult" 
                    WHERE "cvmfs_build_id" = ? AND "command_id" = ? AND "client_config_id" = ? AND "metric_id" = ?
                ''', (cvmfs_build_id, command_id, client_config_id, metric_id))

                result = cursor.fetchone()

                if result:
                    # Update existing entry
                    benchmark_result_id = result[0]
                    logging.info(f"BenchmarkResult already exists, updating for cvmfs_build_id={cvmfs_build_id}, command_id={command_id}")
                    cursor.execute('''
                        UPDATE "BenchmarkResult"
                        SET 
                            "cold_cache_min_val" = ?, "cold_cache_first_quartile" = ?, "cold_cache_median" = ?,
                            "cold_cache_third_quartile" = ?, "cold_cache_max_val" = ?, "warm_cache_min_val" = ?,
                            "warm_cache_first_quartile" = ?, "warm_cache_median" = ?, "warm_cache_third_quartile" = ?,
                            "warm_cache_max_val" = ?, "hot_cache_min_val" = ?, "hot_cache_first_quartile" = ?,
                            "hot_cache_median" = ?, "hot_cache_third_quartile" = ?, "hot_cache_max_val" = ?
                        WHERE "id" = ?
                    ''', (row['cold_cache_min_val'], row['cold_cache_first_quartile'], row['cold_cache_median'],
                          row['cold_cache_third_quartile'], row['cold_cache_max_val'], row['warm_cache_min_val'],
                          row['warm_cache_first_quartile'], row['warm_cache_median'], row['warm_cache_third_quartile'],
                          row['warm_cache_max_val'], row['hot_cache_min_val'], row['hot_cache_first_quartile'],
                          row['hot_cache_median'], row['hot_cache_third_quartile'], row['hot_cache_max_val'],
                          benchmark_result_id))
                else:
                    # Insert new BenchmarkResult entry
                    cursor.execute('''
                        INSERT INTO "BenchmarkResult" (
                            "cvmfs_build_id", "command_id", "client_config_id", "metric_id",
                            "cold_cache_min_val", "cold_cache_first_quartile", "cold_cache_median",
                            "cold_cache_third_quartile", "cold_cache_max_val", "warm_cache_min_val",
                            "warm_cache_first_quartile", "warm_cache_median", "warm_cache_third_quartile",
                            "warm_cache_max_val", "hot_cache_min_val", "hot_cache_first_quartile",
                            "hot_cache_median", "hot_cache_third_quartile", "hot_cache_max_val"
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (cvmfs_build_id, command_id, client_config_id, metric_id,
                          row['cold_cache_min_val'], row['cold_cache_first_quartile'], row['cold_cache_median'],
                          row['cold_cache_third_quartile'], row['cold_cache_max_val'], row['warm_cache_min_val'],
                          row['warm_cache_first_quartile'], row['warm_cache_median'], row['warm_cache_third_quartile'],
                          row['warm_cache_max_val'], row['hot_cache_min_val'], row['hot_cache_first_quartile'],
                          row['hot_cache_median'], row['hot_cache_third_quartile'], row['hot_cache_max_val']))

            conn.commit()
            logging.info("CSV data inserted into the database successfully.")
            return jsonify({"message": "Benchmark data inserted successfully"}), 201
        
        except Exception as e:
            logging.error(f"Failed to insert data: {e}")
            conn.rollback()
            return jsonify({"error": str(e)}), 500

        finally:
            conn.close()

    else:
        logging.error("Invalid file type, only .csv files are allowed")
        return "Invalid file type, only .csv files are allowed", 400

@app.route('/api/configurations', methods=['GET'])
def get_configurations():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch all available commands
        cursor.execute("SELECT id, command_name, command_content FROM Command")
        commands = cursor.fetchall()
        commands_list = [
            {"id": row[0], "command_name": row[1], "command_content": row[2]} for row in commands
        ]

        # Fetch all available client configurations
        cursor.execute("SELECT id, config_name, config_content FROM ClientConfig")
        client_configs = cursor.fetchall()
        client_configs_list = [
            {"id": row[0], "config_name": row[1], "config_content": row[2]} for row in client_configs
        ]

        # Fetch all available metrics
        cursor.execute("SELECT id, metric_name, metric_description FROM Metric")
        metrics = cursor.fetchall()
        metrics_list = [
            {"id": row[0], "metric_name": row[1], "metric_description": row[2]} for row in metrics
        ]

        conn.close()

        return jsonify({
            "commands": commands_list,
            "client_configs": client_configs_list,
            "metrics": metrics_list
        }), 200

    except Exception as e:
        logging.error(f"Failed to retrieve configurations: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/head', methods=['GET'])
def get_head():
    try:
        # Get query parameters for ClientConfig ID, Command ID, and Metric ID
        client_config_id = request.args.get('client_config_id')
        command_id = request.args.get('command_id')
        metric_id = request.args.get('metric_id')

        # Validate that the required parameters are provided
        if not all([client_config_id, command_id, metric_id]):
            return jsonify({"error": "Missing required parameters"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        query = '''
        SELECT
            "CVMFSBuild"."build_type",
            "CVMFSBuild"."commit",
            "CVMFSBuild"."commit_datetime",
            "CVMFSBuild"."tag",
            "CVMFSBuild"."version",
            "BenchmarkResult"."cold_cache_min_val",
            "BenchmarkResult"."cold_cache_first_quartile",
            "BenchmarkResult"."cold_cache_median",
            "BenchmarkResult"."cold_cache_third_quartile",
            "BenchmarkResult"."cold_cache_max_val",
            "BenchmarkResult"."warm_cache_min_val",
            "BenchmarkResult"."warm_cache_first_quartile",
            "BenchmarkResult"."warm_cache_median",
            "BenchmarkResult"."warm_cache_third_quartile",
            "BenchmarkResult"."warm_cache_max_val",
            "BenchmarkResult"."hot_cache_min_val",
            "BenchmarkResult"."hot_cache_first_quartile",
            "BenchmarkResult"."hot_cache_median",
            "BenchmarkResult"."hot_cache_third_quartile",
            "BenchmarkResult"."hot_cache_max_val"
        FROM 
            "BenchmarkResult"
        INNER JOIN 
            "CVMFSBuild" ON "BenchmarkResult"."cvmfs_build_id" = "CVMFSBuild"."id"
        WHERE 
            "BenchmarkResult"."client_config_id" = ?
            AND "BenchmarkResult"."command_id" = ?
            AND "BenchmarkResult"."metric_id" = ?
            AND "CVMFSBuild"."id" IN (
                SELECT "id"
                FROM "CVMFSBuild"
                ORDER BY "commit_datetime" DESC
                LIMIT 12
            )
        ORDER BY 
            "CVMFSBuild"."commit_datetime" DESC;
        '''

        cursor.execute(query, (client_config_id, command_id, metric_id))
        rows = cursor.fetchall()

        # Fetch column names
        columns = [column[0] for column in cursor.description]

        # Convert the rows into a list of dictionaries
        results = [dict(zip(columns, row)) for row in rows]

        conn.close()
        return jsonify(results), 200

    except Exception as e:
        logging.error(f"Failed to retrieve data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/check_commit', methods=['GET'])
def check_commit():
    commit_hash = request.args.get('commit_hash')
    if not commit_hash:
        return jsonify({"error": "Missing commit_hash parameter"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
    SELECT 1 FROM "CVMFSBuild"
    WHERE "commit" = ?
    LIMIT 1
    '''

    cursor.execute(query, (commit_hash,))
    result = cursor.fetchone()

    conn.close()

    if result:
        return "exists", 200
    else:
        return "not found", 200

@app.route('/api/benchmark_combinations', methods=['POST'])
def get_benchmark_combinations():
    try:
        data = request.get_json()
        commit_hash = data.get('commit')
        configurations = data.get('configurations')

        if not commit_hash or not configurations:
            return jsonify({"error": "Missing commit or configurations"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Get benchmarked configurations for the commit from the database
        query = '''
        SELECT
            "ClientConfig"."config_name",
            "Command"."command_name",
            "Metric"."metric_name"
        FROM 
            "BenchmarkResult"
        INNER JOIN 
            "CVMFSBuild" ON "BenchmarkResult"."cvmfs_build_id" = "CVMFSBuild"."id"
        INNER JOIN 
            "ClientConfig" ON "BenchmarkResult"."client_config_id" = "ClientConfig"."id"
        INNER JOIN 
            "Command" ON "BenchmarkResult"."command_id" = "Command"."id"
        INNER JOIN 
            "Metric" ON "BenchmarkResult"."metric_id" = "Metric"."id"
        WHERE 
            "CVMFSBuild"."commit" = ?
        '''

        cursor.execute(query, (commit_hash,))
        benchmarked_combinations = cursor.fetchall()

        # Convert benchmarked results into a set of tuples for easier comparison
        benchmarked_set = set((row[0], row[1], row[2]) for row in benchmarked_combinations)

        # Compare passed configurations with benchmarked configurations
        missing_combinations = [
            config for config in configurations
            if (config['client_config'], config['command'], config['metric']) not in benchmarked_set
        ]

        conn.close()

        # Return the missing combinations (those that haven't been benchmarked yet)
        return jsonify(missing_combinations), 200

    except Exception as e:
        logging.error(f"Failed to retrieve benchmark combinations: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/commits_data', methods=['GET'])
def get_commits_data():
    try:
        # Get query parameters for ClientConfig ID, Command ID, Metric ID, and num_commits
        client_config_id = request.args.get('client_config_id')
        command_id = request.args.get('command_id')
        metric_id = request.args.get('metric_id')
        num_commits = request.args.get('num_commits', 12)  # Default to 12 if not provided

        # Validate that the required parameters are provided
        if not all([client_config_id, command_id, metric_id]):
            return jsonify({"error": "Missing required parameters"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        query = '''
        SELECT
            "CVMFSBuild"."build_type",
            "CVMFSBuild"."commit",
            "CVMFSBuild"."commit_datetime",
            "CVMFSBuild"."tag",
            "CVMFSBuild"."version",
            "BenchmarkResult"."cold_cache_min_val",
            "BenchmarkResult"."cold_cache_first_quartile",
            "BenchmarkResult"."cold_cache_median",
            "BenchmarkResult"."cold_cache_third_quartile",
            "BenchmarkResult"."cold_cache_max_val",
            "BenchmarkResult"."warm_cache_min_val",
            "BenchmarkResult"."warm_cache_first_quartile",
            "BenchmarkResult"."warm_cache_median",
            "BenchmarkResult"."warm_cache_third_quartile",
            "BenchmarkResult"."warm_cache_max_val",
            "BenchmarkResult"."hot_cache_min_val",
            "BenchmarkResult"."hot_cache_first_quartile",
            "BenchmarkResult"."hot_cache_median",
            "BenchmarkResult"."hot_cache_third_quartile",
            "BenchmarkResult"."hot_cache_max_val"
        FROM 
            "BenchmarkResult"
        INNER JOIN 
            "CVMFSBuild" ON "BenchmarkResult"."cvmfs_build_id" = "CVMFSBuild"."id"
        WHERE 
            "BenchmarkResult"."client_config_id" = ?
            AND "BenchmarkResult"."command_id" = ?
            AND "BenchmarkResult"."metric_id" = ?
        ORDER BY 
            "CVMFSBuild"."commit_datetime" DESC
        LIMIT ?
        '''

        cursor.execute(query, (client_config_id, command_id, metric_id, num_commits))
        rows = cursor.fetchall()

        # Fetch column names
        columns = [column[0] for column in cursor.description]

        # Convert the rows into a list of dictionaries
        results = [dict(zip(columns, row)) for row in rows]

        conn.close()
        return jsonify(results), 200

    except Exception as e:
        logging.error(f"Failed to retrieve data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/commits_data_by_names', methods=['GET'])
def get_commits_data_by_names():
    try:
        # Get query parameters for ClientConfig name, Command name, Metric name, and num_commits
        client_config_name = request.args.get('client_config_name')
        command_name = request.args.get('command_name')
        metric_name = request.args.get('metric_name')
        num_commits = request.args.get('num_commits', 12)  # Default to 12 if not provided

        # Validate that the required parameters are provided
        if not all([client_config_name, command_name, metric_name]):
            return jsonify({"error": "Missing required parameters"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        query = '''
        SELECT
            "CVMFSBuild"."build_type",
            "CVMFSBuild"."commit",
            "CVMFSBuild"."commit_datetime",
            "CVMFSBuild"."tag",
            "CVMFSBuild"."version",
            "BenchmarkResult"."cold_cache_min_val",
            "BenchmarkResult"."cold_cache_first_quartile",
            "BenchmarkResult"."cold_cache_median",
            "BenchmarkResult"."cold_cache_third_quartile",
            "BenchmarkResult"."cold_cache_max_val",
            "BenchmarkResult"."warm_cache_min_val",
            "BenchmarkResult"."warm_cache_first_quartile",
            "BenchmarkResult"."warm_cache_median",
            "BenchmarkResult"."warm_cache_third_quartile",
            "BenchmarkResult"."warm_cache_max_val",
            "BenchmarkResult"."hot_cache_min_val",
            "BenchmarkResult"."hot_cache_first_quartile",
            "BenchmarkResult"."hot_cache_median",
            "BenchmarkResult"."hot_cache_third_quartile",
            "BenchmarkResult"."hot_cache_max_val"
        FROM 
            "BenchmarkResult"
        INNER JOIN 
            "CVMFSBuild" ON "BenchmarkResult"."cvmfs_build_id" = "CVMFSBuild"."id"
        INNER JOIN
            "ClientConfig" ON "BenchmarkResult"."client_config_id" = "ClientConfig"."id"
        INNER JOIN
            "Command" ON "BenchmarkResult"."command_id" = "Command"."id"
        INNER JOIN
            "Metric" ON "BenchmarkResult"."metric_id" = "Metric"."id"
        WHERE 
            "ClientConfig"."config_name" = ?
            AND "Command"."command_name" = ?
            AND "Metric"."metric_name" = ?
        ORDER BY 
            "CVMFSBuild"."commit_datetime" DESC
        LIMIT ?
        '''

        cursor.execute(query, (client_config_name, command_name, metric_name, num_commits))
        rows = cursor.fetchall()

        # Fetch column names
        columns = [column[0] for column in cursor.description]

        # Convert the rows into a list of dictionaries
        results = [dict(zip(columns, row)) for row in rows]

        conn.close()
        return jsonify(results), 200

    except Exception as e:
        logging.error(f"Failed to retrieve data by names: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/commits_list', methods=['GET'])
def get_commits_list():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = '''
        SELECT DISTINCT
            "CVMFSBuild"."commit",
            "CVMFSBuild"."commit_datetime",
            "CVMFSBuild"."build_type",
            "CVMFSBuild"."version"
        FROM 
            "CVMFSBuild"
        INNER JOIN
            "BenchmarkResult" ON "BenchmarkResult"."cvmfs_build_id" = "CVMFSBuild"."id"
        ORDER BY
            "CVMFSBuild"."commit_datetime" DESC
        '''

        cursor.execute(query)
        rows = cursor.fetchall()

        # Convert the rows into a list of dictionaries
        commits = [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

        conn.close()
        return jsonify(commits), 200

    except Exception as e:
        logging.error(f"Failed to retrieve commits list: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/results_by_commit', methods=['GET'])
def get_results_by_commit():
    try:
        commit = request.args.get('commit')
        if not commit:
            return jsonify({"error": "Missing required parameter 'commit'"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Get commit info
        cursor.execute('''
            SELECT
                "commit",
                "commit_datetime",
                "build_type",
                "version"
            FROM
                "CVMFSBuild"
            WHERE
                "commit" = ?
        ''', (commit,))
        commit_info = cursor.fetchone()
        if not commit_info:
            return jsonify({"error": "Commit not found"}), 404

        commit_info_dict = dict(zip([column[0] for column in cursor.description], commit_info))

        # Get results
        query = '''
        SELECT
            "Command"."command_name",
            "ClientConfig"."config_name" AS "client_config_name",
            "Metric"."metric_name",
            "BenchmarkResult".*
        FROM 
            "BenchmarkResult"
        INNER JOIN 
            "CVMFSBuild" ON "BenchmarkResult"."cvmfs_build_id" = "CVMFSBuild"."id"
        INNER JOIN 
            "ClientConfig" ON "BenchmarkResult"."client_config_id" = "ClientConfig"."id"
        INNER JOIN 
            "Command" ON "BenchmarkResult"."command_id" = "Command"."id"
        INNER JOIN 
            "Metric" ON "BenchmarkResult"."metric_id" = "Metric"."id"
        WHERE 
            "CVMFSBuild"."commit" = ?
        '''

        df = pd.read_sql_query(query, conn, params=(commit,))

        # Exclude unwanted columns
        df = df.drop(columns=['id', 'cvmfs_build_id', 'client_config_id', 'command_id', 'metric_id'])

        # Convert DataFrame to list of dictionaries
        results = df.to_dict(orient='records')

        conn.close()
        return jsonify({"commit_info": commit_info_dict, "results": results}), 200

    except Exception as e:
        logging.error(f"Failed to retrieve results by commit: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/results_by_commit_csv', methods=['GET'])
def get_results_by_commit_csv():
    try:
        commit = request.args.get('commit')
        if not commit:
            return jsonify({"error": "Missing required parameter 'commit'"}), 400

        conn = get_db_connection()

        query = '''
        SELECT
            "Command"."command_name" AS "command",
            "ClientConfig"."config_name" AS "client_config",
            "Metric"."metric_name" AS "metric",
            "BenchmarkResult".*,
            "CVMFSBuild"."version",
            "CVMFSBuild"."commit",
            "CVMFSBuild"."build_type"
        FROM 
            "BenchmarkResult"
        INNER JOIN 
            "CVMFSBuild" ON "BenchmarkResult"."cvmfs_build_id" = "CVMFSBuild"."id"
        INNER JOIN 
            "ClientConfig" ON "BenchmarkResult"."client_config_id" = "ClientConfig"."id"
        INNER JOIN 
            "Command" ON "BenchmarkResult"."command_id" = "Command"."id"
        INNER JOIN 
            "Metric" ON "BenchmarkResult"."metric_id" = "Metric"."id"
        WHERE 
            "CVMFSBuild"."commit" = ?
        '''

        df = pd.read_sql_query(query, conn, params=(commit,))

        # Exclude unwanted columns
        df = df.drop(columns=['id', 'cvmfs_build_id', 'client_config_id', 'command_id', 'metric_id'])

        # Reorder columns
        columns_order = [
            'command', 'client_config', 'metric',
            'cold_cache_min_val', 'cold_cache_first_quartile', 'cold_cache_median',
            'cold_cache_third_quartile', 'cold_cache_max_val',
            'warm_cache_min_val', 'warm_cache_first_quartile', 'warm_cache_median',
            'warm_cache_third_quartile', 'warm_cache_max_val',
            'hot_cache_min_val', 'hot_cache_first_quartile', 'hot_cache_median',
            'hot_cache_third_quartile', 'hot_cache_max_val',
            'version', 'commit', 'build_type'
        ]
        df = df[columns_order]

        # Convert DataFrame to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)

        conn.close()

        # Prepare the response
        response = make_response(csv_buffer.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename=results-{commit[:6]}.csv'
        response.headers['Content-Type'] = 'text/csv'

        return response

    except Exception as e:
        logging.error(f"Failed to retrieve CSV results by commit: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    logging.info("Starting the Flask server.")
    app.run(debug=True, host='0.0.0.0')
    logging.info("Flask server has stopped.")
