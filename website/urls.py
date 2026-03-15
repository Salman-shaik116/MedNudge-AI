from django.urls import path
from . import views
app_name = 'website'



urlpatterns = [
    path('', views.index, name='index'),
    path("upload/", views.upload_page, name="upload"),
    path("result/", views.result_page, name="result"),
    path("reports/", views.reports_list, name="reports"),
    path("analyze/", views.analyze_report, name="analyze"),
    path('ai-doctor/', views.ai_doctor, name='ai_doctor'),
    path('lab-test/', views.lab_test, name='lab_test'),
    path('second-opinion/', views.second_opinion, name='second_opinion'),
    path('blog/', views.blog, name='blog'),
    path('article/<str:article_id>/', views.article, name='article'),
    path('symptoms-guide/', views.symptoms_guide, name='symptoms_guide'),
    path('knowledge-base/', views.knowledge_base, name='knowledge_base'),
    path('glossary/', views.glossary, name='glossary'),
    path('pricing/', views.pricing, name='pricing'),
    path('signup/', views.signup, name='signup'),
    path('signin/', views.signin, name='signin'),
    path('signout/', views.signout, name='signout'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('reminder/', views.reminder_page, name='reminder'),
    path('send-reminder/', views.send_reminder, name='send_reminder'),
    path('view-report/<int:report_id>/', views.view_report, name='view_report'),
    path('delete-report/<int:report_id>/', views.delete_report, name='delete_report'),
    path('delete-tracker/<str:tracker_id>/', views.delete_tracker, name='delete_tracker'),
    path('progress/<str:tracker_id>/', views.progress_tracker, name='progress_tracker'),
    path('api/progress/<str:tracker_id>/update/', views.update_progress_api, name='update_progress_api'),
    path('api/progress/<str:tracker_id>/get/', views.get_progress_api, name='get_progress_api'),
    path('api/my-trackers/', views.get_user_trackers_api, name='get_user_trackers_api'),
    # Doctor URLs
    path('doctor-register/', views.doctor_register, name='doctor_register'),
    path('doctors-list/', views.doctors_list, name='doctors_list'),
    path('book-appointment/<int:doctor_id>/', views.book_appointment, name='book_appointment'),
    path('appointment-meeting/<int:appointment_id>/', views.appointment_meeting, name='appointment_meeting'),
]


