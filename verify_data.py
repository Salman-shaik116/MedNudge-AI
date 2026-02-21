import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'docusai_project.settings')
django.setup()

from website.models import Appointment, Doctor
from django.contrib.auth.models import User

print("=" * 50)
print("DATABASE VERIFICATION")
print("=" * 50)

# Check doctors
doctors = Doctor.objects.all()
print(f"\nTotal Doctors: {doctors.count()}")
for doc in doctors:
    print(f"  - Dr. {doc.name} ({doc.specialization})")

# Check appointments
appointments = Appointment.objects.all()
print(f"\nTotal Appointments: {appointments.count()}")
for apt in appointments:
    print(f"  - {apt.patient_name} with Dr. {apt.doctor.name} on {apt.appointment_date} at {apt.time_slot}")

# Check users
users = User.objects.all()
print(f"\nTotal Users: {users.count()}")
for user in users:
    print(f"  - {user.username} ({user.email})")
    user_appointments = Appointment.objects.filter(patient_email=user.email)
    print(f"    Appointments: {user_appointments.count()}")

print("\n" + "=" * 50)
print("VERIFICATION COMPLETE")
print("=" * 50)
