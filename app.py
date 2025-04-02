import os
import yaml
import re
import logging
import gzip
from io import BytesIO
from flask import Flask, Response, abort
import requests

app = Flask(__name__)

# Set up logging configuration
if app.debug:
    log_level = logging.DEBUG
else:
    log_level = logging.INFO

# Create a custom logger
logger = logging.getLogger()
logger.setLevel(log_level)

# Create a console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(log_level)

# Create a formatter and set it for the handler
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(ch)

# Load the configuration from the YAML file
def load_config():
    with open('config.yaml', 'r') as file:
        return yaml.safe_load(file)

config = load_config()
file_mappings = config.get('file_mappings', {})
recompress_content = config.get('recompress_content', False)  # Read recompress_content setting

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
    # Log the request to proxy a specific file
    app.logger.debug(f"Received request to proxy: {filename}")

    if filename not in file_mappings:
        app.logger.warning(f"No mapping found for {filename}")
        abort(404, description=f"No mapping found for {filename}")

    mapping = file_mappings[filename]
    backend_url = mapping.get('backend_url')
    regex_patterns = mapping.get('regex_patterns', {})

    if not backend_url:
        app.logger.error(f"Backend URL not defined for {filename}")
        abort(500, description=f"Backend URL not defined for {filename}")

    # Log the backend request
    app.logger.debug(f"Fetching content from backend: {backend_url}")

    # Fetch the file content from the backend URL
    try:
        response = requests.get(backend_url)
        response.raise_for_status()  # Raise an exception for HTTP errors
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching file from {backend_url}: {e}")
        abort(500, description=f"Error fetching file from {backend_url}")

    # Log response status
    app.logger.debug(f"Received {response.status_code} response from backend")

    # Apply regex substitutions to the content
    modified_content = apply_regex_substitutions(response.text, regex_patterns)

    # If recompression is enabled, compress the content and adjust headers
    if recompress_content:
        app.logger.debug("Recompression enabled, compressing content.")
        compressed_content = gzip_compress(modified_content)
        content_encoding = 'gzip'
        # Log the compression action
        app.logger.debug(f"Content compressed to {content_encoding}.")
    else:
        compressed_content = modified_content
        content_encoding = 'identity'  # No compression
        app.logger.debug("Recompression disabled, returning uncompressed content.")

    # Ensure the correct Content-Type is forwarded
    content_type = response.headers.get('Content-Type', 'text/plain')

    # Log the content-type being used
    app.logger.debug(f"Using Content-Type: {content_type}")

    # Return the modified content with the appropriate headers
    app.logger.debug(f"Returning modified content to client with status code {response.status_code}")

    return Response(
        compressed_content,
        status=response.status_code,
        headers={'Content-Encoding': content_encoding},  # Set Content-Encoding to 'gzip' or 'identity'
        content_type=content_type  # Forward Content-Type header or default to 'text/plain'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
