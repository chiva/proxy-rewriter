# Proxy Rewriter

A lightweight proxy server in Docker to fetch, rewrite, and serve remote text files (e.g., `.m3u`) using regex replacements.

## 🚀 Usage

### Run with Docker:

```bash
docker run -d -p 8000:8000 \
  -e FILE_MAPPINGS='{
    "file1.m3u": {
      "backend_url": "https://example.com/playlist.m3u",
      "regex_patterns": {
        "old-domain.com": "new-domain.com"
      }
    }
  }' \
  ghcr.io/YOUR_USERNAME/proxy-rewriter:latest
```

Access via:
```
http://localhost:8000/file1.m3u
```

## 🐳 Build and Push to GitHub Container Registry

```bash
docker build -t ghcr.io/YOUR_USERNAME/proxy-rewriter:latest .
docker push ghcr.io/YOUR_USERNAME/proxy-rewriter:latest
```
