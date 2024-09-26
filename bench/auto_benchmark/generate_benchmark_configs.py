import os
import yaml
import logging
import subprocess


class BenchmarkConfigGenerator:
    def __init__(self, commit_hash, result_dir, config_path):
        self.commit_hash = commit_hash
        self.result_dir = result_dir
        self.config_path = config_path
        self.benchmark_config = self.load_benchmark_config()
        self.version = "2.12.0.0"  # Hardcoded for now

        # Set up logging
        log_file_path = "/root/auto_benchmark/generate_benchmark_configs.log"
        logging.basicConfig(
            filename=log_file_path,
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
        )

    def load_benchmark_config(self):
        """Load the benchmark YAML configuration."""
        try:
            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)
                logging.info(f"Loaded benchmark configuration from {self.config_path}")
                return config
        except Exception as e:
            logging.error(f"Error loading benchmark configuration: {e}")
            return None

    def get_commit_datetime(self):
        """Fetch the commit datetime from the git repository."""
        try:
            commit_datetime = subprocess.run(
                ['git', 'show', '-s', '--format=%ci', self.commit_hash],
                stdout=subprocess.PIPE,
                text=True
            ).stdout.strip()
            commit_datetime_formatted = commit_datetime.replace('-', '').replace(' ', '').replace(':', '')[0:-5]
            return commit_datetime_formatted
        except Exception as e:
            logging.error(f"Error fetching commit datetime: {e}")
            return None

    def generate_benchmark_yaml(self):
        """Generate the benchmark YAML based on the template."""
        try:
            template_path = "/root/auto_benchmark/common_configs/config_benchmark_template.yaml"
            output_path = os.path.join(self.result_dir, "config-bench.yaml")

            with open(template_path, 'r') as template_file:
                benchmark_yaml = template_file.read()

            commands = '["' + '", "'.join(self.benchmark_config.get('commands', [])) + '"]'
            client_configs = '\n  - ["' + '", "'.join(self.benchmark_config.get('client_configs', [])) + '"]'

            benchmark_yaml = benchmark_yaml.replace("@COMMIT_HASH@", self.commit_hash)
            benchmark_yaml = benchmark_yaml.replace("@RESULT_DIR@", self.result_dir)
            benchmark_yaml = benchmark_yaml.replace("@COMMANDS@", commands)
            benchmark_yaml = benchmark_yaml.replace(" @CLIENT_CONFIGS@", client_configs)

            with open(output_path, 'w') as file:
                file.write(benchmark_yaml)
            
            logging.info(f"Generated benchmark YAML: {output_path}")
        except Exception as e:
            logging.error(f"Error generating benchmark YAML: {e}")

    def generate_visualization_yaml(self):
        """Generate the visualization YAML based on the template."""
        try:
            template_path = "/root/auto_benchmark/common_configs/config_visualization_template.yaml"
            output_path = os.path.join(self.result_dir, "config-visual.yaml")

            with open(template_path, 'r') as template_file:
                visualization_yaml = template_file.read()

            commit_datetime = self.get_commit_datetime()
            client_configs_visual = '["' + '", "'.join(self.benchmark_config.get('client_configs', [])) + '"]'
            metrics_visual = '["' + '", "'.join(self.benchmark_config.get('metrics', [])) + '"]'
            ia_metrics_visual = '["' + '", "'.join(self.benchmark_config.get('internal_affairs_metrics', [])) + '"]'

            visualization_yaml = visualization_yaml.replace("@COMMIT_HASH@", self.commit_hash)
            visualization_yaml = visualization_yaml.replace("@VERSION@", self.version)
            visualization_yaml = visualization_yaml.replace("@COMMIT_DATETIME@", commit_datetime)
            visualization_yaml = visualization_yaml.replace("@CLIENT_CONFIGS@", client_configs_visual)
            visualization_yaml = visualization_yaml.replace("@METRICS@", metrics_visual)
            visualization_yaml = visualization_yaml.replace("@IA_METRICS@", ia_metrics_visual)

            with open(output_path, 'w') as file:
                file.write(visualization_yaml)

            logging.info(f"Generated visualization YAML: {output_path}")
        except Exception as e:
            logging.error(f"Error generating visualization YAML: {e}")

    def generate_configs(self):
        """Generate both the benchmark and visualization YAML files."""
        if not self.benchmark_config:
            logging.error("Benchmark configuration is not loaded, cannot generate YAML files.")
            return

        self.generate_benchmark_yaml()
        self.generate_visualization_yaml()


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        logging.error("Invalid arguments. Usage: generate_benchmark_configs.py <commit_hash> <result_dir>")
        sys.exit(1)

    commit_hash = sys.argv[1]
    result_dir = sys.argv[2]
    config_path = "/root/auto_benchmark/benchmark.yaml"

    generator = BenchmarkConfigGenerator(commit_hash, result_dir, config_path)
    generator.generate_configs()
