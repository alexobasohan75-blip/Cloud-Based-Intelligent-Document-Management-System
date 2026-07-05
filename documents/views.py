from datetime import datetime
from pathlib import Path
from bson import ObjectId
from django.conf import settings
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render, redirect
from config.mongo import users, documents, categories, embeddings, audit_logs
from audit.utils import log_action
from ai_engine.text_extractors import extract_text
from ai_engine.classifier import classify_document
from ai_engine.semantic import generate_embedding, cosine_similarity

def require_login(request): return bool(request.session.get('user_id'))
def require_admin(request): return request.session.get('role')=='admin'
def allowed_for_doc(request, doc): return require_admin(request) or str(doc.get('uploaded_by'))==request.session.get('user_id')

def dashboard(request):
    if not require_login(request): return redirect('login')
    query={} if require_admin(request) else {'uploaded_by':request.session.get('user_id')}
    recent=list(documents.find(query).sort('upload_date',-1).limit(10))
    stats={'total_documents':documents.count_documents(query),'total_users':users.count_documents({}),'total_categories':categories.count_documents({})}
    return render(request,'dashboard.html',{'documents':recent,**stats})

def document_list(request):
    if not require_login(request): return redirect('login')
    cat=request.GET.get('category','')
    query={} if require_admin(request) else {'uploaded_by':request.session.get('user_id')}
    if cat: query['category']=cat
    docs=list(documents.find(query).sort('upload_date',-1))
    return render(request,'document_list.html',{'documents':docs,'categories':list(categories.find()),'selected':cat})

def upload_document(request):
    if not require_login(request): return redirect('login')
    if request.method=='POST':
        f=request.FILES.get('document'); title=request.POST.get('title','').strip()
        if not f: messages.error(request,'Select a document.'); return redirect('upload_document')
        suffix=Path(f.name).suffix.lower()
        if suffix not in ['.pdf','.docx','.txt']:
            messages.error(request,'Only PDF, DOCX and TXT are supported.'); return redirect('upload_document')
        if f.size>settings.MAX_UPLOAD_SIZE:
            messages.error(request,'File too large. Maximum size is 10MB.'); return redirect('upload_document')
        fs=FileSystemStorage(location=settings.MEDIA_ROOT/'documents', base_url=settings.MEDIA_URL+'documents/')
        filename=fs.save(f.name, f); saved_path=Path(settings.MEDIA_ROOT)/'documents'/filename
        try: extracted=extract_text(saved_path)
        except Exception as e: extracted=''; messages.warning(request,f'Text extraction warning: {e}')
        category=classify_document(extracted or title or f.name)
        doc={'title':title or Path(f.name).stem,'original_filename':f.name,'file_url':fs.url(filename),'file_path':str(saved_path),'file_type':suffix.replace('.','').upper(),'extracted_text':extracted,'category':category,'uploaded_by':request.session.get('user_id'),'uploaded_by_name':request.session.get('name'),'upload_date':datetime.utcnow(),'status':'active'}
        result=documents.insert_one(doc)
        emb=generate_embedding(extracted or title or f.name)
        embeddings.update_one({'document_id':str(result.inserted_id)},{'$set':{'document_id':str(result.inserted_id),'vector_data':emb,'created_at':datetime.utcnow()}},upsert=True)
        log_action(request.session.get('user_id'),'Uploaded and classified document',str(result.inserted_id),{'category':category})
        messages.success(request,f'Document uploaded and classified as {category}.')
        return redirect('document_detail', document_id=str(result.inserted_id))
    return render(request,'upload.html')

def search_documents(request):
    if not require_login(request): return redirect('login')
    q=request.GET.get('q','').strip(); results=[]
    if q:
        q_emb=generate_embedding(q)
        query={} if require_admin(request) else {'uploaded_by':request.session.get('user_id')}
        for doc in documents.find(query):
            emb=embeddings.find_one({'document_id':str(doc['_id'])})
            score=cosine_similarity(q_emb, emb.get('vector_data') if emb else None)
            lexical=0.05 if q.lower() in (doc.get('title','')+' '+doc.get('extracted_text','')).lower() else 0
            total=round(float(score+lexical),4)
            if total>0: doc['score']=total; results.append(doc)
        results=sorted(results,key=lambda d:d.get('score',0),reverse=True)[:20]
        log_action(request.session.get('user_id'),'Semantic search',None,{'query':q,'results':len(results)})
    return render(request,'search.html',{'query':q,'results':results})

def document_detail(request, document_id):
    if not require_login(request): return redirect('login')
    doc=documents.find_one({'_id':ObjectId(document_id)})
    if not doc or not allowed_for_doc(request, doc): messages.error(request,'Document not found or access denied.'); return redirect('dashboard')
    log_action(request.session.get('user_id'),'Viewed document',document_id)
    return render(request,'document_detail.html',{'doc':doc})

def delete_document(request, document_id):
    if not require_login(request): return redirect('login')
    doc=documents.find_one({'_id':ObjectId(document_id)})
    if not doc or not allowed_for_doc(request, doc): messages.error(request,'Access denied.'); return redirect('dashboard')
    if request.method=='POST':
        documents.update_one({'_id':ObjectId(document_id)},{'$set':{'status':'deleted','deleted_at':datetime.utcnow()}})
        log_action(request.session.get('user_id'),'Deleted document',document_id)
        messages.success(request,'Document removed from active list.'); return redirect('document_list')
    return render(request,'confirm_delete.html',{'doc':doc})

def admin_panel(request):
    if not require_login(request): return redirect('login')
    if not require_admin(request): messages.error(request,'Admin access only.'); return redirect('dashboard')
    return render(request,'admin_panel.html',{'users':list(users.find().sort('created_at',-1).limit(20)),'logs':list(audit_logs.find().sort('timestamp',-1).limit(20)),'documents':list(documents.find().sort('upload_date',-1).limit(20))})

def manage_categories(request):
    if not require_login(request) or not require_admin(request): return redirect('dashboard')
    if request.method=='POST':
        name=request.POST.get('category_name','').strip(); desc=request.POST.get('description','').strip()
        if name: categories.update_one({'category_name':name},{'$set':{'category_name':name,'description':desc}},upsert=True); messages.success(request,'Category saved.')
    return render(request,'categories.html',{'categories':list(categories.find().sort('category_name',1))})

def manage_users(request):
    if not require_login(request) or not require_admin(request): return redirect('dashboard')
    return render(request,'users.html',{'users':list(users.find().sort('created_at',-1))})

def audit_log_view(request):
    if not require_login(request) or not require_admin(request): return redirect('dashboard')
    return render(request,'logs.html',{'logs':list(audit_logs.find().sort('timestamp',-1).limit(200))})

def reports_view(request):
    if not require_login(request): return redirect('login')
    query={} if require_admin(request) else {'uploaded_by':request.session.get('user_id')}
    data=[]
    for c in categories.find().sort('category_name',1): data.append({'category':c['category_name'],'count':documents.count_documents({**query,'category':c['category_name']})})
    return render(request,'reports.html',{'data':data})
