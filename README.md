# Cloud-Based Intelligent Document Management System — Full Submission Project

A submission-ready Django + MongoDB implementation of **Cloud-Based Intelligent Document Management System with AI-Powered Classification and Retrieval**.

# Features
- User registration/login
- Admin and user roles
- Document upload for PDF, DOCX and TXT
- Local media storage for PythonAnywhere deployment
- Text extraction from uploaded documents
- Automated classification using trained TF-IDF + LinearSVC when trained, with keyword fallback
- Semantic retrieval using Sentence Transformers `all-MiniLM-L6-v2`, with sparse fallback for limited hosting
- MongoDB collections: users, documents, categories, embeddings, audit_logs
- Dashboard, document listing, search, reports, admin panel
- Audit trail for login, upload, view, search and delete actions
- Sample training dataset and classifier training command

# Stack
Python, Django, MongoDB, PyMongo, Scikit-Learn, Sentence Transformers, PyMuPDF, python-docx, Bootstrap, PythonAnywhere.

# Local Setup
```bash
python -m venv venv
venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py train_classifier
python manage.py runserver
```

# PythonAnywhere Setup
See `docs/INSTALLATION_GUIDE.md`.

# First Use
Register your first account and select `Admin`. Then upload documents and test semantic search.

# Important Submission Note
This is a complete academic prototype, not a hardened enterprise SaaS. For production, add stronger file scanning, HTTPS-only settings, external object storage, backups and extensive load testing.
