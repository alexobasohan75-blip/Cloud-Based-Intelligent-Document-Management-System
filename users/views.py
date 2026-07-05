from datetime import datetime
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.shortcuts import render, redirect
from bson import ObjectId
from config.mongo import users
from audit.utils import log_action

def register_view(request):
    if request.method=='POST':
        name=request.POST.get('name','').strip(); email=request.POST.get('email','').strip().lower(); password=request.POST.get('password',''); role=request.POST.get('role','user')
        if role not in ['user','admin']: role='user'
        if not name or not email or not password:
            messages.error(request,'All fields are required.'); return redirect('register')
        if users.find_one({'email':email}):
            messages.error(request,'Email already exists.'); return redirect('register')
        result=users.insert_one({'name':name,'email':email,'password_hash':make_password(password),'role':role,'status':'active','created_at':datetime.utcnow()})
        request.session['user_id']=str(result.inserted_id); request.session['name']=name; request.session['role']=role
        log_action(str(result.inserted_id),'Registered account')
        return redirect('dashboard')
    return render(request,'register.html')

def login_view(request):
    if request.method=='POST':
        email=request.POST.get('email','').strip().lower(); password=request.POST.get('password','')
        user=users.find_one({'email':email,'status':{'$ne':'blocked'}})
        if user and check_password(password, user.get('password_hash','')):
            request.session['user_id']=str(user['_id']); request.session['name']=user.get('name'); request.session['role']=user.get('role','user')
            log_action(str(user['_id']),'Logged in')
            return redirect('dashboard')
        messages.error(request,'Invalid login details or blocked account.')
    return render(request,'login.html')

def logout_view(request):
    uid=request.session.get('user_id'); log_action(uid,'Logged out'); request.session.flush(); return redirect('login')

def profile_view(request):
    if not request.session.get('user_id'): return redirect('login')
    user=users.find_one({'_id':ObjectId(request.session['user_id'])})
    return render(request,'profile.html',{'user':user})
