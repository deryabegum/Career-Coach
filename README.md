# Career-Coach
This is an AI Career Coach app.

## Deployment

This project is set up to deploy as:

- frontend on `Vercel`
- backend on `Render`

### 1. Deploy the backend to Render

The repo includes a root [render.yaml](/Users/deryabegum/Career-Coach/render.yaml) for a Render web service.

In Render:

1. Create a new Blueprint or Web Service from this GitHub repo.
2. Use the generated service from `render.yaml`.
3. Set `CORS_ORIGINS` to your Vercel frontend URL after you have it.

Important backend notes:

- The backend uses SQLite and uploaded files.
- `render.yaml` mounts a persistent disk and stores both at:
  - database: `/opt/render/project/src/backend/render-data/app.db`
  - uploads: `/opt/render/project/src/backend/render-data/uploads`
- The backend health check is available at `/health`.

### 2. Deploy the frontend to Vercel

In Vercel:

1. Import this repo.
2. Set the project root directory to `frontend`.
3. Framework preset: `Create React App`.
4. Add environment variable:
   - `REACT_APP_API_URL=https://your-render-service.onrender.com`

The frontend also includes:

- [frontend/vercel.json](/Users/deryabegum/Career-Coach/frontend/vercel.json) for SPA routing
- [frontend/.env.example](/Users/deryabegum/Career-Coach/frontend/.env.example) showing the required API URL variable

### 3. Connect frontend and backend

After both are deployed:

1. Copy the Vercel production URL.
2. Put that URL into the Render backend `CORS_ORIGINS` env var.
3. Redeploy the Render service if needed.

### Production caveat

This setup works for a student/demo deployment, but long term you should move:

- SQLite to Postgres
- local uploads to cloud object storage like S3 or Cloudinary
