# Deployment Guide: Goodwill Vintage Hunter

This guide explains how to deploy your application securely using Docker and Cloudflare Tunnel.

## Prerequisites
1. A **Cloudflare Account** (Free).
2. A **Domain Name** connected to Cloudflare (e.g., `vintagehunter.com`).
3. **Docker Desktop** installed on your computer (or server).

---

## Phase 1: Run with Docker (Local Test)

1. **Build the Image**
   Open terminal in the `Goodwill-app` folder:
   ```bash
   docker build -t vintage-hunter .
   ```

2. **Run the Container**
   ```bash
   docker run -d -p 5001:5001 --name goodwill-app \
     -v $(pwd)/backend/gw_data.db:/app/backend/gw_data.db \
     -e API_KEY="your_gemini_api_key_here" \
     vintage-hunter
   ```
   *Note: The `-v` flag ensures your database is saved to your computer, so you don't lose data if the container restarts.*

---

## Phase 2: Cloudflare Tunnel (Expose to Internet)

1. **Install `cloudflared`**
   - Mac: `brew install cloudflared`
   - Linux/Server: Follow Cloudflare docs.

2. **Login**
   ```bash
   cloudflared tunnel login
   ```

3. **Create a Tunnel**
   ```bash
   cloudflared tunnel create vintage-app
   ```

4. **Configure the Tunnel**
   Create a file named `config.yml`:
   ```yaml
   tunnel: <Tunnel-UUID>
   credentials-file: /root/.cloudflared/<Tunnel-UUID>.json

   ingress:
     - hostname: vintage.yourdomain.com
       service: http://localhost:5001
     - service: http_status:404
   ```

5. **Run the Tunnel**
   ```bash
   cloudflared tunnel run vintage-app
   ```

---

## Phase 3: Secure Access (Important!)

Since this is on the public internet, you don't want strangers accessing it.

1. Go to **Cloudflare Zero Trust Dashboard** -> **Access** -> **Applications**.
2. Add a **Self-hosted** application.
3. **Application Domain:** `vintage.yourdomain.com`
4. **Policies:**
   - Rule Name: `Allow Family`
   - Action: `Allow`
   - Include: `Emails` -> `your.email@gmail.com`, `wife.email@gmail.com`

**Result:** When you visit `vintage.yourdomain.com`, Cloudflare will ask for your email and send you a login code. No hacking possible.

