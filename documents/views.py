from pathlib import Path

from bson import ObjectId
from django.conf import settings
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import FileResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from ai_engine.classifier import classify_document
from ai_engine.semantic import cosine_similarity, generate_embedding
from ai_engine.text_extractors import extract_text
from audit.utils import log_action
from config.mongo import (
    audit_logs,
    categories,
    documents,
    embeddings,
    users,
)


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


# =========================================================
# Helper functions
# =========================================================

def require_login(request):
    return bool(request.session.get("user_id"))


def require_admin(request):
    return request.session.get("role") == "admin"


def allowed_for_doc(request, doc):
    if require_admin(request):
        return True

    current_user_id = str(request.session.get("user_id", ""))
    document_owner_id = str(doc.get("uploaded_by", ""))

    return current_user_id == document_owner_id


def parse_object_id(value):
    if not value:
        return None

    value = str(value)

    if not ObjectId.is_valid(value):
        return None

    return ObjectId(value)


def active_document_filter():
    return {
        "$or": [
            {"status": "active"},
            {"status": {"$exists": False}},
        ]
    }


def visible_documents_query(request):
    filters = [active_document_filter()]

    if not require_admin(request):
        filters.append({
            "uploaded_by": str(request.session.get("user_id"))
        })

    return {"$and": filters}


def get_document_storage():
    document_directory = Path(settings.MEDIA_ROOT) / "documents"

    document_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return FileSystemStorage(
        location=str(document_directory),
        base_url=f"{settings.MEDIA_URL.rstrip('/')}/documents/",
    )


# =========================================================
# Dashboard
# =========================================================

def dashboard(request):
    if not require_login(request):
        return redirect("login")

    query = visible_documents_query(request)

    recent_documents = list(
        documents.find(query)
        .sort("upload_date", -1)
        .limit(10)
    )

    context = {
        "documents": recent_documents,
        "total_documents": documents.count_documents(query),
        "total_users": users.count_documents({}),
        "total_categories": categories.count_documents({}),
    }

    return render(request, "dashboard.html", context)


# =========================================================
# Document list
# =========================================================

def document_list(request):
    if not require_login(request):
        return redirect("login")

    selected_category = request.GET.get("category", "").strip()

    filters = [visible_documents_query(request)]

    if selected_category:
        filters.append({
            "category": selected_category
        })

    query = {"$and": filters}

    document_results = list(
        documents.find(query)
        .sort("upload_date", -1)
    )

    category_results = list(
        categories.find()
        .sort("category_name", 1)
    )

    context = {
        "documents": document_results,
        "categories": category_results,
        "selected": selected_category,
    }

    return render(
        request,
        "document_list.html",
        context,
    )


# =========================================================
# Upload document
# =========================================================

def upload_document(request):
    if not require_login(request):
        return redirect("login")

    if request.method != "POST":
        return render(request, "upload.html")

    uploaded_file = request.FILES.get("document")
    title = request.POST.get("title", "").strip()

    if not uploaded_file:
        messages.error(
            request,
            "Please select a document.",
        )
        return redirect("upload_document")

    original_filename = Path(uploaded_file.name).name
    suffix = Path(original_filename).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        messages.error(
            request,
            "Only PDF, DOCX and TXT files are supported.",
        )
        return redirect("upload_document")

    maximum_size = getattr(
        settings,
        "MAX_UPLOAD_SIZE",
        10 * 1024 * 1024,
    )

    if uploaded_file.size > maximum_size:
        messages.error(
            request,
            "The file is too large. Maximum size is 10 MB.",
        )
        return redirect("upload_document")

    storage = get_document_storage()
    stored_filename = None

    try:
        stored_filename = storage.save(
            original_filename,
            uploaded_file,
        )

        saved_path = Path(
            storage.path(stored_filename)
        )

        try:
            extracted_text = extract_text(saved_path)
        except Exception as error:
            extracted_text = ""

            messages.warning(
                request,
                f"Text extraction failed: {error}",
            )

        classification_text = (
            extracted_text
            or title
            or original_filename
        )

        try:
            category = classify_document(
                classification_text
            )
        except Exception:
            category = "Uncategorized"

            messages.warning(
                request,
                "The document could not be classified automatically.",
            )

        document_data = {
            "title": title or Path(original_filename).stem,
            "original_filename": original_filename,
            "stored_filename": stored_filename,
            "file_url": storage.url(stored_filename),
            "file_path": str(saved_path),
            "file_type": suffix.lstrip(".").upper(),
            "extracted_text": extracted_text,
            "category": category,
            "uploaded_by": str(
                request.session.get("user_id")
            ),
            "uploaded_by_name": request.session.get(
                "name",
                "Unknown user",
            ),
            "upload_date": timezone.now(),
            "status": "active",
        }

        result = documents.insert_one(
            document_data
        )

        document_id = str(
            result.inserted_id
        )

        try:
            vector_data = generate_embedding(
                classification_text
            )

            embeddings.update_one(
                {
                    "document_id": document_id
                },
                {
                    "$set": {
                        "document_id": document_id,
                        "vector_data": vector_data,
                        "created_at": timezone.now(),
                    }
                },
                upsert=True,
            )

        except Exception as error:
            messages.warning(
                request,
                f"Search embedding could not be created: {error}",
            )

        log_action(
            request.session.get("user_id"),
            "Uploaded and classified document",
            document_id,
            {
                "category": category,
                "filename": original_filename,
            },
        )

        messages.success(
            request,
            f'Document uploaded and classified as "{category}".',
        )

        return redirect(
            "document_detail",
            document_id=document_id,
        )

    except Exception as error:
        if (
            stored_filename
            and storage.exists(stored_filename)
        ):
            storage.delete(stored_filename)

        messages.error(
            request,
            f"The document could not be uploaded: {error}",
        )

        return redirect("upload_document")


# =========================================================
# Search documents
# =========================================================

def search_documents(request):
    if not require_login(request):
        return redirect("login")

    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    results = []

    if search_query:
        try:
            query_embedding = generate_embedding(
                search_query
            )
        except Exception as error:
            messages.error(
                request,
                f"Search could not be completed: {error}",
            )

            return render(
                request,
                "search.html",
                {
                    "query": search_query,
                    "results": [],
                },
            )

        query = visible_documents_query(request)

        for document in documents.find(query):
            embedding_record = embeddings.find_one({
                "document_id": str(document["_id"])
            })

            vector_data = None

            if embedding_record:
                vector_data = embedding_record.get(
                    "vector_data"
                )

            try:
                semantic_score = cosine_similarity(
                    query_embedding,
                    vector_data,
                )
            except Exception:
                semantic_score = 0

            searchable_text = " ".join([
                str(document.get("title", "")),
                str(document.get("category", "")),
                str(document.get("extracted_text", "")),
                str(document.get("original_filename", "")),
            ]).lower()

            lexical_score = 0

            if search_query.lower() in searchable_text:
                lexical_score = 0.05

            total_score = round(
                float(semantic_score or 0)
                + lexical_score,
                4,
            )

            if total_score > 0:
                document["score"] = total_score
                results.append(document)

        results.sort(
            key=lambda item: item.get("score", 0),
            reverse=True,
        )

        results = results[:20]

        log_action(
            request.session.get("user_id"),
            "Semantic search",
            None,
            {
                "query": search_query,
                "results": len(results),
            },
        )

    return render(
        request,
        "search.html",
        {
            "query": search_query,
            "results": results,
        },
    )


# =========================================================
# Document detail
# =========================================================

def document_detail(request, document_id):
    if not require_login(request):
        return redirect("login")

    object_id = parse_object_id(document_id)

    if object_id is None:
        messages.error(
            request,
            "Invalid document ID.",
        )
        return redirect("document_list")

    doc = documents.find_one({
        "$and": [
            {"_id": object_id},
            active_document_filter(),
        ]
    })

    if not doc:
        messages.error(
            request,
            "Document not found.",
        )
        return redirect("document_list")

    if not allowed_for_doc(request, doc):
        messages.error(
            request,
            "You do not have permission to view this document.",
        )
        return redirect("dashboard")

    log_action(
        request.session.get("user_id"),
        "Viewed document",
        document_id,
    )

    return render(
        request,
        "document_detail.html",
        {
            "doc": doc
        },
    )


# =========================================================
# Download document
# =========================================================

def download_document(request, document_id):
    if not require_login(request):
        return redirect("login")

    object_id = parse_object_id(document_id)

    if object_id is None:
        messages.error(
            request,
            "Invalid document ID.",
        )
        return redirect("document_list")

    doc = documents.find_one({
        "$and": [
            {"_id": object_id},
            active_document_filter(),
        ]
    })

    if not doc:
        messages.error(
            request,
            "Document not found.",
        )
        return redirect("document_list")

    if not allowed_for_doc(request, doc):
        messages.error(
            request,
            "You do not have permission to download this document.",
        )
        return redirect("dashboard")

    storage = get_document_storage()
    stored_filename = doc.get("stored_filename")

    if not stored_filename:
        messages.error(
            request,
            "The stored filename is missing.",
        )

        return redirect(
            "document_detail",
            document_id=document_id,
        )

    if not storage.exists(stored_filename):
        messages.error(
            request,
            "The document file is no longer available.",
        )

        return redirect(
            "document_detail",
            document_id=document_id,
        )

    download_name = (
        doc.get("original_filename")
        or doc.get("title")
        or stored_filename
    )

    try:
        file_handle = storage.open(
            stored_filename,
            "rb",
        )

        log_action(
            request.session.get("user_id"),
            "Downloaded document",
            document_id,
            {
                "title": doc.get("title"),
                "filename": download_name,
            },
        )

        return FileResponse(
            file_handle,
            as_attachment=True,
            filename=download_name,
        )

    except Exception as error:
        messages.error(
            request,
            f"The document could not be downloaded: {error}",
        )

        return redirect(
            "document_detail",
            document_id=document_id,
        )


# =========================================================
# Delete document
# =========================================================

def delete_document(request, document_id):
    if not require_login(request):
        return redirect("login")

    object_id = parse_object_id(document_id)

    if object_id is None:
        messages.error(
            request,
            "Invalid document ID.",
        )
        return redirect("document_list")

    doc = documents.find_one({
        "$and": [
            {"_id": object_id},
            active_document_filter(),
        ]
    })

    if not doc:
        messages.error(
            request,
            "Document not found.",
        )
        return redirect("document_list")

    if not allowed_for_doc(request, doc):
        messages.error(
            request,
            "You do not have permission to delete this document.",
        )
        return redirect("dashboard")

    if request.method != "POST":
        return render(
            request,
            "confirm_delete.html",
            {
                "doc": doc
            },
        )

    storage = get_document_storage()
    stored_filename = doc.get("stored_filename")

    try:
        if (
            stored_filename
            and storage.exists(stored_filename)
        ):
            storage.delete(stored_filename)

        elif doc.get("file_path"):
            old_file_path = Path(
                doc["file_path"]
            )

            allowed_directory = (
                Path(settings.MEDIA_ROOT)
                / "documents"
            ).resolve()

            try:
                resolved_file_path = (
                    old_file_path.resolve()
                )

                if (
                    resolved_file_path.is_file()
                    and allowed_directory
                    in resolved_file_path.parents
                ):
                    resolved_file_path.unlink()

            except (OSError, RuntimeError):
                pass

        embeddings.delete_many({
            "document_id": document_id
        })

        document_title = doc.get(
            "title",
            "Document",
        )

        log_action(
            request.session.get("user_id"),
            "Deleted document",
            document_id,
            {
                "title": document_title,
                "filename": doc.get(
                    "original_filename"
                ),
            },
        )

        documents.delete_one({
            "_id": object_id
        })

        messages.success(
            request,
            f'"{document_title}" was deleted successfully.',
        )

        return redirect("document_list")

    except Exception as error:
        messages.error(
            request,
            f"The document could not be deleted: {error}",
        )

        return redirect(
            "document_detail",
            document_id=document_id,
        )


# =========================================================
# Admin panel
# =========================================================

def admin_panel(request):
    if not require_login(request):
        return redirect("login")

    if not require_admin(request):
        messages.error(
            request,
            "Admin access only.",
        )
        return redirect("dashboard")

    context = {
        "users": list(
            users.find()
            .sort("created_at", -1)
            .limit(20)
        ),
        "logs": list(
            audit_logs.find()
            .sort("timestamp", -1)
            .limit(20)
        ),
        "documents": list(
            documents.find(
                active_document_filter()
            )
            .sort("upload_date", -1)
            .limit(20)
        ),
    }

    return render(
        request,
        "admin_panel.html",
        context,
    )


# =========================================================
# Categories
# =========================================================

def manage_categories(request):
    if not require_login(request):
        return redirect("login")

    if not require_admin(request):
        messages.error(
            request,
            "Admin access only.",
        )
        return redirect("dashboard")

    if request.method == "POST":
        name = request.POST.get(
            "category_name",
            "",
        ).strip()

        description = request.POST.get(
            "description",
            "",
        ).strip()

        if not name:
            messages.error(
                request,
                "Category name is required.",
            )

        else:
            categories.update_one(
                {
                    "category_name": name
                },
                {
                    "$set": {
                        "category_name": name,
                        "description": description,
                        "updated_at": timezone.now(),
                    },
                    "$setOnInsert": {
                        "created_at": timezone.now(),
                    },
                },
                upsert=True,
            )

            messages.success(
                request,
                f'Category "{name}" was saved.',
            )

            return redirect(
                "manage_categories"
            )

    category_results = list(
        categories.find()
        .sort("category_name", 1)
    )

    return render(
        request,
        "categories.html",
        {
            "categories": category_results
        },
    )


# =========================================================
# Users
# =========================================================

def manage_users(request):
    if not require_login(request):
        return redirect("login")

    if not require_admin(request):
        messages.error(
            request,
            "Admin access only.",
        )
        return redirect("dashboard")

    user_results = list(
        users.find()
        .sort("created_at", -1)
    )

    return render(
        request,
        "users.html",
        {
            "users": user_results
        },
    )


# =========================================================
# Audit logs
# =========================================================

def audit_log_view(request):
    if not require_login(request):
        return redirect("login")

    if not require_admin(request):
        messages.error(
            request,
            "Admin access only.",
        )
        return redirect("dashboard")

    log_results = list(
        audit_logs.find()
        .sort("timestamp", -1)
        .limit(200)
    )

    return render(
        request,
        "logs.html",
        {
            "logs": log_results
        },
    )


# =========================================================
# Reports
# =========================================================

def reports_view(request):
    if not require_login(request):
        return redirect("login")

    report_data = []

    for category_record in categories.find().sort(
        "category_name",
        1,
    ):
        category_name = category_record.get(
            "category_name",
            "Uncategorized",
        )

        query = {
            "$and": [
                visible_documents_query(request),
                {
                    "category": category_name
                },
            ]
        }

        report_data.append({
            "category": category_name,
            "count": documents.count_documents(
                query
            ),
        })

    return render(
        request,
        "reports.html",
        {
            "data": report_data
        },
    )