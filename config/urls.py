from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from users import views as user_views
from documents import views as doc_views
urlpatterns=[
 path('', doc_views.dashboard, name='dashboard'),
 path('register/', user_views.register_view, name='register'),
 path('login/', user_views.login_view, name='login'),
 path('logout/', user_views.logout_view, name='logout'),
 path('profile/', user_views.profile_view, name='profile'),
 path('upload/', doc_views.upload_document, name='upload_document'),
 path('search/', doc_views.search_documents, name='search_documents'),
 path('documents/', doc_views.document_list, name='document_list'),
 path('document/<str:document_id>/', doc_views.document_detail, name='document_detail'),
 path('document/<str:document_id>/delete/', doc_views.delete_document, name='delete_document'),
 path('admin-panel/', doc_views.admin_panel, name='admin_panel'),
 path('admin-panel/categories/', doc_views.manage_categories, name='manage_categories'),
 path('admin-panel/users/', doc_views.manage_users, name='manage_users'),
 path('admin-panel/logs/', doc_views.audit_log_view, name='audit_logs'),
 path('reports/', doc_views.reports_view, name='reports'),
]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
