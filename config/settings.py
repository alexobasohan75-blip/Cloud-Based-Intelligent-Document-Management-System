import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is required")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
RENDER_EXTERNAL_HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

INSTALLED_APPS = [
    "config.apps.MongoAdminConfig",        # instead of "django.contrib.admin"
    "config.apps.MongoAuthConfig",         # instead of "django.contrib.auth"
    "config.apps.MongoContentTypesConfig", # instead of "django.contrib.contenttypes"
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "users",
    "documents",
    "ai_engine",
    "audit",
]

# Set ONCE. Do not redefine this later in the file.
DEFAULT_AUTO_FIELD = "django_mongodb_backend.fields.ObjectIdAutoField"

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ]
    }
}]

WSGI_APPLICATION = 'config.wsgi.application'

# Pull the connection string from the environment instead of hardcoding
# credentials in source. Add MONGO_URI to your .env file, e.g.:
# MONGO_URI=mongodb+srv://asabiaolawumi_db_user:DuxbVXDSOFhZqpsI@dmscluster.w8gstjy.mongodb.net/?appName=DMSCluster
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'sample_mflix')

DATABASES = {
    "default": {
        "ENGINE": "django_mongodb_backend",
        "HOST": MONGO_URI,
        "NAME": MONGO_DB_NAME,
    },
}

# Needed if you use embedded models, so they aren't treated as top-level collections
DATABASE_ROUTERS = ["django_mongodb_backend.routers.MongoRouter"]

MIGRATION_MODULES = {
    "admin": "mongo_migrations.admin",
    "auth": "mongo_migrations.auth",
    "contenttypes": "mongo_migrations.contenttypes",
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

MAX_UPLOAD_SIZE = 10 * 1024 * 1024