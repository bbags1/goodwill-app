# Cloud Deployment Instructions (Railway / Render)

Since Cloudflare Workers cannot host Python/SQLite apps, we will use a dedicated cloud host.

## Option 1: Railway (Recommended - Easiest)

1. **Push Code to GitHub**
   - Create a GitHub repository.
   - Push this entire `Goodwill-app` folder to it.

2. **Deploy on Railway**
   - Go to [railway.app](https://railway.app/).
   - Login with GitHub.
   - Click **"New Project"** -> **"Deploy from GitHub repo"**.
   - Select your repository.

3. **Add Environment Variables**
   - In Railway Dashboard -> Variables:
   - Add `API_KEY` = `your_gemini_api_key`
   - Add `PORT` = `5001` (Railway requires this or defaults to another port. Our code listens on `os.getenv("PORT")`, so this is safe).

4. **IMPORTANT: Service Configuration**
   - Go to Settings -> Service.
   - **Root Directory:** `/Goodwill-app` (or wherever your `Procfile` is).
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `cd backend && python app.py`

5. **Persistence (Important)**
   - Since Railway restarts apps, your `gw_data.db` might reset.
   - **Solution:** Add a "Volume" in Railway settings and mount it to `/app/backend`.

## Option 2: DigitalOcean Droplet ($6/mo) + Cloudflare

This gives you a full computer in the cloud.

1. **Create a Droplet** on DigitalOcean (Ubuntu 22.04).
2. **SSH into it:** `ssh root@your-ip`
3. **Clone your Code:**
   ```bash
   git clone https://github.com/yourname/vintage-hunter.git
   cd vintage-hunter
   ```
4. **Install Docker:**
   ```bash
   snap install docker
   ```
5. **Run your App:**
   ```bash
   docker build -t app .
   docker run -d -p 5001:5001 --restart always -v $(pwd)/backend/gw_data.db:/app/backend/gw_data.db -e API_KEY="xyz" app
   ```
6. **Connect Cloudflare Tunnel:**
   - Follow the `DEPLOY_CLOUDFLARE.md` guide I wrote earlier, but run the commands *on the Droplet*, not your Mac.

**End Result:** The app runs 24/7 on the cloud server, and you access it via `vintage.yourdomain.com`.
