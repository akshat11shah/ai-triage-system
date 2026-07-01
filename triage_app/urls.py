from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('message/<int:message_id>/', views.message_detail, name='message_detail'),
    path('triage/single/', views.triage_single, name='triage_single'),
    path('triage/batch/', views.triage_batch, name='triage_batch'),
    path('triage/eval/', views.run_eval_view, name='run_eval'),
    path('triage/override/<int:result_id>/', views.override_triage, name='override_triage'),
    path('seed/', views.seed_data_view, name='seed_data'),
    path('kb/manage/', views.manage_kb_article, name='manage_kb_article'),
    path('message/import/', views.import_excel, name='import_excel'),
    path('message/<int:message_id>/generate_reply/', views.generate_reply_api, name='generate_reply_api'),
]
