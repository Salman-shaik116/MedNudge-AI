# Doctor Registration Setup Instructions

## Changes Made:

1. **Models Added** (website/models.py):
   - Doctor model with fields: name, email, phone, specialization, experience, qualification, address, photo
   - Appointment model for booking appointments with doctors

2. **Forms Created** (website/forms.py):
   - DoctorForm for doctor registration
   - AppointmentForm for booking appointments

3. **Views Added** (website/views.py):
   - doctor_register: Handle doctor registration
   - doctors_list: Display all registered doctors
   - book_appointment: Book appointment with a doctor
   - appointment_meeting: Video meeting interface

4. **URLs Added** (website/urls.py):
   - /doctor-register/ - Doctor registration page
   - /doctors-list/ - List of all doctors
   - /book-appointment/<id>/ - Book appointment page
   - /appointment-meeting/<id>/ - Meeting interface

5. **Templates Created**:
   - doctor_register.html - Doctor registration form
   - doctors_list.html - Doctors listing with appointment booking
   - book_appointment.html - Appointment confirmation page
   - appointment_meeting.html - Video meeting interface

6. **Index.html Modified**:
   - Changed "Getting Started For Free" button to a dropdown
   - Added options: "Register as Patient" and "Register as Doctor"
   - Updated navigation links to point to doctors_list

## Setup Steps:

1. **Create media folder**:
   ```bash
   mkdir media
   mkdir media\doctors
   ```

2. **Run migrations**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. **Install Pillow (if not installed)**:
   ```bash
   pip install Pillow
   ```

4. **Run the server**:
   ```bash
   python manage.py runserver
   ```

## Database:
- Uses the same MySQL database (signup_db) configured in settings.py
- All models will be created in the same database

## Features:
- Doctor registration with photo upload
- List all registered doctors
- Book appointments with date and time slot selection
- Video meeting interface for appointments
- Dropdown registration menu for patients and doctors

## Navigation:
- Home page: http://localhost:8000/
- Doctor Registration: http://localhost:8000/doctor-register/
- Doctors List: http://localhost:8000/doctors-list/
- Patient Registration: http://localhost:8000/signup/
