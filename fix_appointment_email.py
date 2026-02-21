import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'docusai_project.settings')
django.setup()

from website.models import Appointment
from django.contrib.auth.models import User

print("Updating appointment email to match a user...")

# Get the appointment
appointment = Appointment.objects.first()
if appointment:
    print(f"\nCurrent appointment:")
    print(f"  Patient: {appointment.patient_name}")
    print(f"  Email: {appointment.patient_email}")
    
    # Get a user (let's use 'prabhas' since the patient name is PRABHAS)
    user = User.objects.filter(username='prabhas').first()
    if user:
        appointment.patient_email = user.email
        appointment.save()
        print(f"\nUpdated appointment email to: {user.email}")
        print(f"Now login with username 'prabhas' to see your appointment!")
    else:
        print("\nUser 'prabhas' not found")
else:
    print("No appointments found")
