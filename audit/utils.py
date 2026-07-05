from datetime import datetime
from config.mongo import audit_logs

def log_action(user_id, action, document_id=None, extra=None):
    try:
        audit_logs.insert_one({'user_id':user_id,'document_id':document_id,'action':action,'extra':extra or {},'timestamp':datetime.utcnow()})
    except Exception:
        pass
