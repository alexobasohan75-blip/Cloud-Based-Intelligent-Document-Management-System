import os
import shutil
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from config.mongo import (
    audit_logs,
    categories,
    documents,
    embeddings,
    users,
)


BASE_DIR = Path(__file__).resolve().parent
DOCUMENTS_DIRECTORY = BASE_DIR / "media" / "documents"


def reset_database():
    collections = {
        "users": users,
        "documents": documents,
        "categories": categories,
        "embeddings": embeddings,
        "audit_logs": audit_logs,
    }

    print("WARNING: This will permanently delete all application data.")
    print("It will also delete all uploaded files in media/documents.")

    confirmation = input('Type RESET and press Enter to continue: ').strip()

    if confirmation != "RESET":
        print("Reset cancelled.")
        return

    for name, collection in collections.items():
        result = collection.delete_many({})
        print(f"{name}: deleted {result.deleted_count} records")

    if DOCUMENTS_DIRECTORY.exists():
        shutil.rmtree(DOCUMENTS_DIRECTORY)
        print("Uploaded document files deleted.")

    DOCUMENTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    print("Empty media/documents directory created.")

    print("Database and uploaded files reset successfully.")


if __name__ == "__main__":
    reset_database()