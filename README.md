# Proxy Rewriter

A lightweight proxy server in Docker to fetch, rewrite, and serve remote text files (e.g., `.m3u`) using regex replacements.

## 🚀 Usage

### Run with Docker:

The proxy rewriter can be configured through a `config.yaml` file, which defines the file mappings and regex replacements.

1. **Create a `config.yaml`** file with your desired mappings and regex patterns:

#### Example `config.yaml`:

```yaml
file_mappings:
  file1.m3u:
    backend_url: "https://example.com/playlist.m3u"
    regex_patterns:
      "old-domain.com": "new-domain.com"
  file2.m3u:
    backend_url: "https://example.com/another_playlist.m3u"
    regex_patterns:
      "old-server.com": "new-server.com"
```

2. Run the Docker container with the config.yaml file mounted as a volume:

```bash
docker run -d -p 8000:8000 \
  -v /path/to/config.yaml:/app/config.yaml \
  ghcr.io/chiva/proxy-rewriter:latest
```

This will run the proxy server and load the configuration from the config.yaml file.

Access the proxy via:
```
http://localhost:8000/file1.m3u
http://localhost:8000/file2.m3u
```

## 🐳 Build and Push to GitHub Container Registry

This project uses GitHub Actions to build and push the Docker image to the GitHub Container Registry (GHCR) when a tag is pushed.
