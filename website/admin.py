from django.contrib import admin
from .models import MedicalReport, Doctor, Appointment

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'specialization', 'experience', 'created_at']
    list_filter = ['specialization', 'created_at']
    search_fields = ['name', 'email', 'phone', 'specialization']

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient_name', 'doctor', 'appointment_date', 'time_slot', 'created_at']
    list_filter = ['appointment_date', 'created_at']
    search_fields = ['patient_name', 'patient_email', 'doctor__name']

@admin.register(MedicalReport)
class MedicalReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['user__username']
