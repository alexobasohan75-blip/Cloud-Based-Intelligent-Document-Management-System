import math
from collections import Counter
try:
    from sentence_transformers import SentenceTransformer
    MODEL=SentenceTransformer('all-MiniLM-L6-v2')
except Exception:
    MODEL=None

def generate_embedding(text):
    text=(text or '')[:4000]
    if MODEL:
        return {'type':'dense','values':MODEL.encode(text).tolist()}
    words=[w for w in text.lower().split() if len(w)>2]
    return {'type':'sparse','values':dict(Counter(words).most_common(500))}

def cosine_similarity(a,b):
    if not a or not b: return 0
    av=a.get('values',a); bv=b.get('values',b)
    if isinstance(av,list) and isinstance(bv,list):
        dot=sum(x*y for x,y in zip(av,bv)); na=math.sqrt(sum(x*x for x in av)); nb=math.sqrt(sum(y*y for y in bv)); return dot/(na*nb) if na and nb else 0
    if isinstance(av,dict) and isinstance(bv,dict):
        keys=set(av)|set(bv); dot=sum(av.get(k,0)*bv.get(k,0) for k in keys); na=math.sqrt(sum(v*v for v in av.values())); nb=math.sqrt(sum(v*v for v in bv.values())); return dot/(na*nb) if na and nb else 0
    return 0
