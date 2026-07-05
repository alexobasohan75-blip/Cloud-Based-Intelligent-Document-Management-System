from django.conf import settings
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
_client=MongoClient(settings.MONGO_URI)
db=_client[settings.MONGO_DB_NAME]
users=db['users']; documents=db['documents']; categories=db['categories']; embeddings=db['embeddings']; audit_logs=db['audit_logs']
def ensure_indexes():
    users.create_index([('email', ASCENDING)], unique=True)
    documents.create_index([('title', TEXT), ('extracted_text', TEXT)])
    documents.create_index([('category', ASCENDING)])
    documents.create_index([('upload_date', DESCENDING)])
    embeddings.create_index([('document_id', ASCENDING)], unique=True)
    audit_logs.create_index([('timestamp', DESCENDING)])
    categories.create_index([('category_name', ASCENDING)], unique=True)
ensure_indexes()
def seed_categories():
    defaults=[('Report','Findings, analysis and recommendations'),('Invoice','Payment, receipt and billing documents'),('Contract','Agreement and legal terms'),('Policy','Rules, guidelines and procedures'),('Memo','Notices and internal communication'),('Academic Material','Lecture notes, research and projects'),('General Document','Unclassified document')]
    for name,desc in defaults:
        categories.update_one({'category_name':name},{'$setOnInsert':{'category_name':name,'description':desc}},upsert=True)
seed_categories()
