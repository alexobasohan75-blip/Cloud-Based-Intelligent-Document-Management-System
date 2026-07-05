# Installation Guide
1. Create MongoDB Atlas free cluster and copy connection string.
2. Upload project to PythonAnywhere.
3. Open Bash console:
   ```bash
   cd ai_document_manager_full
   python3.10 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   nano .env
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```
4. In PythonAnywhere Web tab, set WSGI file to import `config.wsgi`.
5. Add static mapping `/static/` to `staticfiles` and media mapping `/media/` to `media`.
6. Reload the web app.
