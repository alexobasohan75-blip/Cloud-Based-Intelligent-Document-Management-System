import re
from pathlib import Path
from collections import Counter
import joblib
MODEL_PATH=Path(__file__).resolve().parent/'trained_classifier.joblib'
CATEGORY_KEYWORDS={
 'Invoice':['invoice','receipt','payment','amount','vat','total','bill','balance','paid'],
 'Contract':['agreement','contract','party','terms','clause','signature','obligation','legal'],
 'Policy':['policy','procedure','compliance','regulation','guideline','standard','rule'],
 'Memo':['memo','memorandum','notice','internal','attention','staff','announcement'],
 'Academic Material':['lecture','student','chapter','research','project','course','assignment','thesis'],
 'Report':['report','summary','findings','recommendation','analysis','evaluation','result'],
}
def preprocess_text(text):
    text=(text or '').lower(); text=re.sub(r'[^a-z0-9\s]',' ',text); return re.sub(r'\s+',' ',text).strip()
def classify_document(text):
    clean=preprocess_text(text)
    if MODEL_PATH.exists():
        try:
            bundle=joblib.load(MODEL_PATH); return bundle['model'].predict(bundle['vectorizer'].transform([clean]))[0]
        except Exception: pass
    counts=Counter({cat:sum(clean.count(k) for k in kws) for cat,kws in CATEGORY_KEYWORDS.items()})
    if not counts or counts.most_common(1)[0][1]==0: return 'General Document'
    return counts.most_common(1)[0][0]
