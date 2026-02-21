# Quick Reference Guide - Doctor Registration Feature

## 🚀 Quick Start (3 Steps)

### Step 1: Install Dependencies
```bash
pip install Pillow
```

### Step 2: Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 3: Start Server
```bash
python manage.py runserver
```

## 📍 URL Routes

| Page | URL | Description |
|------|-----|-------------|
| Homepage | http://localhost:8000/ | Main landing page |
| Doctor Registration | http://localhost:8000/doctor-register/ | Register as doctor |
| Doctors List | http://localhost:8000/doctors-list/ | View all doctors & book appointments |
| Patient Registration | http://localhost:8000/signup/ | Register as patient |
| Admin Panel | http://localhost:8000/admin/ | Manage doctors & appointments |

## 🎯 How to Use

### Register as Doctor:
1. Go to homepage
2. Click "Getting Started For Free" dropdown
3. Select "Register as Doctor"
4. Fill form (name, email, phone, specialization, experience, qualification, photo)
5. Submit → Auto-redirect to doctors list

### Book Appointment (Patient):
1. Click "Book Appointment" or "Doctors Page" in navigation
2. Browse doctors
3. Select date from date picker
4. Choose time slot (9-11 AM, 11 AM-1 PM, 1-3 PM, 3-5 PM)
5. Click "Book Appointment"
6. Fill patient details (name, email, phone)
7. Confirm → Join video meeting

### View in Admin:
1. Create superuser: `python manage.py createsuperuser`
2. Login to admin: http://localhost:8000/admin/
3. View/manage Doctors and Appointments

## 📊 Models

### Doctor Model Fields:
- name (required)
- email (required, unique)
- phone (required)
- specialization (required) - Dropdown: Cardiology, Dermatology, Neurology, Orthopedics, Pediatrics, General Medicine, Other
- experience (required) - Years as integer
- qualification (required)
- address (optional)
- photo (required) - Max 2MB, JPG/PNG only

### Appointment Model Fields:
- doctor (ForeignKey)
- patient_name (required)
- patient_email (required)
- patient_phone (required)
- appointment_date (required)
- time_slot (required)

## 🎨 UI Features

### Homepage Changes:
- "Getting Started For Free" is now a dropdown
- Two options: "Register as Patient" 👤 and "Register as Doctor" 👨‍⚕️
- Navigation links updated to point to doctors list

### Doctor Registration Page:
- Clean gradient background (purple to blue)
- Form with all fields
- Photo upload with drag-drop
- Real-time validation
- AJAX submission
- Success message with auto-redirect

### Doctors List Page:
- Grid layout (responsive)
- Doctor cards with photos
- Date picker for appointments
- 4 time slot buttons
- Interactive selection (buttons highlight when selected)
- Validation messages

### Appointment Meeting Page:
- Video meeting interface
- Doctor info display
- Control buttons (Mute, Video, Chat, End Call)
- Professional dark theme

## 🔧 Troubleshooting

### Issue: "No module named 'PIL'"
**Solution:** `pip install Pillow`

### Issue: "Table doesn't exist"
**Solution:** Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

### Issue: "Media files not loading"
**Solution:** Check settings.py has:
```python
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

### Issue: "Photo upload fails"
**Solution:** 
- Check file size (max 2MB)
- Check file type (JPG or PNG only)
- Ensure media/doctors/ folder exists

## 📁 File Structure
```
docusai_project-main/
├── website/
│   ├── models.py (Doctor, Appointment models added)
│   ├── views.py (4 new views added)
│   ├── urls.py (4 new URLs added)
│   ├── forms.py (NEW - DoctorForm, AppointmentForm)
│   ├── admin.py (Models registered)
│   └── templates/website/
│       ├── index.html (Modified - dropdown added)
│       ├── doctor_register.html (NEW)
│       ├── doctors_list.html (NEW)
│       ├── book_appointment.html (NEW)
│       └── appointment_meeting.html (NEW)
├── media/
│   └── doctors/ (NEW - stores doctor photos)
└── docusai_project/
    ├── settings.py (MEDIA config added)
    └── urls.py (Already has media config)
```

## ✅ Testing Checklist

- [ ] Doctor registration form loads
- [ ] Can upload photo (JPG/PNG, under 2MB)
- [ ] Form validation works
- [ ] Doctor appears in doctors list after registration
- [ ] Can select date and time slot
- [ ] Appointment booking works
- [ ] Meeting page loads with doctor info
- [ ] Admin panel shows doctors and appointments
- [ ] Dropdown menu works on homepage
- [ ] Navigation links work correctly

## 🎓 Tips

1. **Photo Requirements:** Use JPG or PNG, max 2MB
2. **Specializations:** Choose from 7 predefined options
3. **Time Slots:** 4 slots available per day (2-hour blocks)
4. **Database:** All data stored in existing signup_db MySQL database
5. **Admin Access:** Create superuser to manage via admin panel

## 🔐 Security Features

- CSRF protection enabled
- Photo size validation (2MB max)
- File type validation (JPG/PNG only)
- Email uniqueness enforced
- Form validation on client and server
- SQL injection protection (Django ORM)

## 📞 Support

If you encounter issues:
1. Check console for errors
2. Verify migrations ran successfully
3. Ensure Pillow is installed
4. Check media folder permissions
5. Verify database connection

---
**Ready to go!** Just run the 3 quick start steps and you're all set! 🚀
