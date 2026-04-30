# Career-Coach
This is an AI Career Coach app.

## No-card deployment option

If you do not want to add a credit card, the simplest path for this project is:

- frontend on `Vercel`
- backend on `PythonAnywhere`

This repo is prepared for that setup on `deryasBranch`.

### Frontend deploy on Vercel

1. Go to [Vercel](https://vercel.com) and import this GitHub repo.
2. Choose branch `deryasBranch`.
3. Set the project root directory to `frontend`.
4. Framework preset: `Create React App`.
5. Add this environment variable:

   `REACT_APP_API_URL=https://yourusername.pythonanywhere.com`

6. Deploy.

Files included for Vercel:

- [frontend/vercel.json](/Users/deryabegum/Career-Coach/frontend/vercel.json)
- [frontend/.env.example](/Users/deryabegum/Career-Coach/frontend/.env.example)

### Backend deploy on PythonAnywhere

PythonAnywhere recommends manual Flask configuration with a virtualenv:
[PythonAnywhere Flask setup guide](https://help.pythonanywhere.com/pages/Flask)

High-level steps:

1. Create a free PythonAnywhere account.
2. Open a Bash console.
3. Clone your repo:

   `git clone https://github.com/deryabegum/Career-Coach.git`

4. Check out the branch:

   `git checkout deryasBranch`

5. Create a virtualenv and install backend dependencies:

   `mkvirtualenv --python=/usr/bin/python3.13 career-coach-env`

   `pip install -r /home/YOUR_PYTHONANYWHERE_USERNAME/Career-Coach/backend/requirements.txt`

6. In the PythonAnywhere Web tab, create a new web app using `Manual configuration`.
7. Point the web app virtualenv to your new virtualenv.
8. Open the PythonAnywhere WSGI file and replace its Flask section with the contents of:

   [backend/pythonanywhere_wsgi.py](/Users/deryabegum/Career-Coach/backend/pythonanywhere_wsgi.py)

9. Replace these placeholders inside that file:

   - `YOUR_PYTHONANYWHERE_USERNAME`
   - `replace-me`
   - `replace-me-too`
   - `https://your-vercel-project.vercel.app`

10. Reload the PythonAnywhere web app.

### Important limits

This is a good no-card student/demo setup, but there are tradeoffs:

- PythonAnywhere free accounts have outbound internet restrictions:
  [PythonAnywhere allowlist policy](https://help.pythonanywhere.com/pages/RequestingAllowlistAdditions/)
- Features that call external AI or live job sources may be limited unless those domains are allowed
- SQLite and local uploads stay on the PythonAnywhere filesystem, which is okay for a lightweight demo but not ideal long term
