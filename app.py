import os
import yaml
import re
import logging
import gzip
from io import BytesIO
from flask import Flask, Response, abort, request
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

app = Flask(__name__)

config = {}
config_file_path = 'config.yaml'
config_last_modified = 0

def load_config():
    global config, config_last_modified
    try:
        with open(config_file_path, 'r') as file:
            config = yaml.safe_load(file)
        config_last_modified = os.path.getmtime(config_file_path)
        
        configure_logging()
        
        app.logger.info(f"Configuration loaded successfully from {config_file_path}")
        return config
    except Exception as e:
        app.logger.error(f"Error loading configuration: {e}")
        # If we're loading for the first time and fail, use empty config
        if not config:
            return {}
        return config

def configure_logging():
    log_level_name = config.get('log_level', 'INFO').upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    
    logger = logging.getLogger()
    logger.handlers = []
    logger.setLevel(log_level)
    
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    
    logger.addHandler(ch)
    
    app.logger.info(f"Logging level set to {log_level_name}")

def check_config_updated():
    global config_last_modified
    try:
        current_mtime = os.path.getmtime(config_file_path)
        if current_mtime > config_last_modified:
            app.logger.info("Config file change detected, reloading...")
            load_config()
            return True
        return False
    except Exception as e:
        app.logger.error(f"Error checking config file: {e}")
        return False

class ConfigFileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(config_file_path):
            app.logger.info(f"Config file {event.src_path} has been modified")
            load_config()

def start_config_watcher():
    event_handler = ConfigFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path=os.path.dirname(os.path.abspath(config_file_path)) or '.', recursive=False)
    observer.start()
    app.logger.info(f"Started watching config file: {config_file_path}")
    return observer

def apply_regex_substitutions(content, substitutions):
    for pattern, replacement in substitutions.items():
        content = re.sub(pattern, replacement, content)
    return content

def gzip_compress(content):
    buf = BytesIO()
    with gzip.GzipFile(mode='wb', fileobj=buf) as f:
        f.write(content.encode('utf-8'))
    return buf.getvalue()

@app.route('/<path:filename>')
def proxy(filename):
    # Check if config needs to be updated
    check_config_updated()
    
    client_ip = request.remote_addr
    app.logger.debug(f"Received request from {client_ip} to proxy: {filename}")

    file_mappings = config.get('file_mappings', {})

    if filename not in file_mappings:
        app.logger.warning(f"No mapping found for {filename}, requested by {client_ip}")
        abort(404, description=f"No mapping found for {filename}")

    mapping = file_mappings[filename]
    backend_url = mapping.get('backend_url')
    regex_patterns = mapping.get('regex_patterns', {})

    if not backend_url:
        app.logger.error(f"Backend URL not defined for {filename}")
        abort(500, description=f"Backend URL not defined for {filename}")

    app.logger.debug(f"Fetching content from backend: {backend_url} for client {client_ip}")

    try:
        response = requests.get(backend_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching file from {backend_url}: {e}")
        abort(500, description=f"Error fetching file from {backend_url}")

    app.logger.debug(f"Received {response.status_code} response from backend for request from {client_ip}")
    modified_content = apply_regex_substitutions(response.text, regex_patterns)
    recompress_content = config.get('recompress_content', False)

    if recompress_content:
        app.logger.debug(f"Recompression enabled, compressing content for {client_ip}.")
        compressed_content = gzip_compress(modified_content)
        content_encoding = 'gzip'
        app.logger.debug(f"Content compressed to {content_encoding}.")
    else:
        compressed_content = modified_content.encode('utf-8') if isinstance(modified_content, str) else modified_content
        content_encoding = 'identity'  # No compression
        app.logger.debug(f"Recompression disabled, returning uncompressed content to {client_ip}.")

    content_type = response.headers.get('Content-Type', 'text/plain')
    app.logger.debug(f"Using Content-Type: {content_type} for response to {client_ip}")
    app.logger.debug(f"Returning modified content to client {client_ip} with status code {response.status_code}")

    return Response(
        compressed_content,
        status=response.status_code,
        headers={'Content-Encoding': content_encoding},
        content_type=content_type
    )

if __name__ == '__main__':
    load_config()
    observer = start_config_watcher()

    try:
        app.run(host='0.0.0.0', port=8000, debug=config.get('debug', True))
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
