# 🌐 Nginx Configuration

DrugX uses **nginx** (say: “engine-x”) **as a reverse proxy** to serve both the Streamlit application and static documentation through a single port.

## 🏗️ Architecture

```
User Request (port 8100)
    ↓
nginx (port 80 internal)
    ├─→ /docs/*     → Static files (Docsify documentation)
    └─→ /*          → Proxy to Streamlit (port 7860)
```

## 🛠️ What We Implemented

1. **Reverse Proxy Setup**
   - nginx listens on port 80 internally (mapped to 8100 externally)
   - Routes `/docs/` requests to static files at `/app/src/frontend/static/docs/`
   - Proxies all other requests to Streamlit running on port 7860

2. **Static File Serving**
   - Docsify documentation served directly by nginx
   - Each doc page has its own clean URL (e.g., `/docs/architecture`)
   - No iframe limitations - proper navigation and URL routing

3. **Startup Process**
   - Streamlit starts first in background (port 7860)
   - Wait 8 seconds for Streamlit to be ready
   - nginx starts in foreground and proxies requests

4. **Benefits**
   - Single entry point (one port for everything)
   - Better performance (nginx handles static files efficiently)
   - Clean URLs for documentation pages
   - Production-ready setup for GCP deployment
   - WebSocket support for Streamlit's real-time features

## 📁 Key Files

- `nginx.conf` - nginx configuration with location blocks
- `start-nginx.sh` - Startup script that runs both services
- `Dockerfile` - Installs nginx and sets up the container

## ⚙️ Development vs Production

Both use the same nginx setup, but development mode mounts volumes for hot reloading:
- **Production**: `make run`
- **Development**: `make run-dev` (with volume mounting)
```
