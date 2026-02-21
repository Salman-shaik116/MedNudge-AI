from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from .models import MedicalReport
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from mediscanner.analyzer import analyze_medical_report
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import hashlib
import time


@login_required(login_url='website:result')
def reports_list(request):
    reports = MedicalReport.objects.filter(user=request.user)
    return render(request, "website/reports.html", {"reports": reports})

def upload_page(request):
    return render(request, "website/upload.html")

def result_page(request):
    return render(request, "website/result.html")

def analyze_report(request):
    if request.method == "POST":
        file = request.FILES.get("report")

        if not file:
            return render(request, "website/upload.html", {
                "error": "Please upload a file"
            })

        result = analyze_medical_report(file)
        MedicalReport.objects.create(
            user=request.user if request.user.is_authenticated else None,
            report_file=file,
            analysis=result
        )
        

        return render(request, "website/result.html", {
            "analysis": result
        })

    return render(request, "website/upload.html")



def signup(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('website:signup')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        messages.success(request, "Account created successfully")
        return redirect('website:signin')

    return render(request, 'website/signup.html')


def signin(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('website:dashboard')
        else:
            messages.error(request, "Invalid credentials")
            return redirect('website:signin')

    return render(request, 'website/signin.html')


@login_required(login_url='website:signin')
def dashboard(request):
    # Get user's reports
    user_reports = MedicalReport.objects.filter(user=request.user).order_by('-uploaded_at')
    recent_reports = user_reports[:5]
    
    # Get all registered users for recipient selection
    all_users = User.objects.all().exclude(id=request.user.id)
    
    # Week days for tracking
    week_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    context = {
        'user_reports': user_reports,
        'recent_reports': recent_reports,
        'all_users': all_users,
        'week_days': week_days,
        'task_progress': load_all_progress(),
        'completion_rate': calculate_overall_completion_rate(),
    }
    
    return render(request, 'website/dashboard_complete.html', context)

@login_required(login_url='website:signin')
def send_reminder(request):
    if request.method == 'POST':
        recipient_email = request.POST.get('recipient_email')
        recipient_name = request.POST.get('recipient_name')
        recipient_username = request.POST.get('recipient_username')
        
        if not recipient_email or not recipient_name or not recipient_username:
            messages.error(request, 'Please fill in all required fields')
            return redirect('website:dashboard')
        
        try:
            # Generate unique progress link
            timestamp = str(int(time.time()))
            unique_id = hashlib.md5(f"{recipient_email}{timestamp}".encode()).hexdigest()[:8]
            progress_url = f"http://localhost:8000/progress/{unique_id}/?name={recipient_name}&email={recipient_email}"
            
            # Email configuration
            sender_email = "geethageetha7817@gmail.com"
            sender_password = "egkw lkki fzxp giir"
            
            # Create email
            msg = MIMEMultipart('alternative')
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Subject'] = f'🏥 Your Weekly Health Plan - {recipient_name}'
            
            # Create HTML email
            html_body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                               padding: 30px; border-radius: 15px; text-align: center; color: white; margin-bottom: 30px; }}
                    .tracker-btn {{
                        display: inline-block;
                        background: #10b981;
                        color: white;
                        padding: 20px 40px;
                        text-decoration: none;
                        border-radius: 30px;
                        font-weight: bold;
                        font-size: 18px;
                        margin: 25px 0;
                        box-shadow: 0 10px 20px rgba(16, 185, 129, 0.3);
                    }}
                    .section {{ background: #f8fafc; padding: 25px; margin: 20px 0; border-radius: 12px; border-left: 5px solid #667eea; }}
                    .task {{ background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                    .time {{ color: #667eea; font-weight: bold; font-size: 16px; }}
                    .footer {{ text-align: center; padding: 20px; color: #6b7280; font-size: 14px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🏥 Your Weekly Health Plan</h1>
                    <p>Hello {recipient_name} (@{recipient_username})! 👋</p>
                    <p>Week starting {time.strftime('%B %d, %Y')}</p>
                </div>
                
                <div style="text-align: center; padding: 30px;">
                    <h2 style="color: #667eea; margin-bottom: 20px;">📊 Your Personal Health Tracker</h2>
                    <p style="font-size: 16px; margin-bottom: 25px;">Click below to access your personalized weekly health tracker with progress monitoring:</p>
                    <a href="{progress_url}" class="tracker-btn">
                        🚀 Start Your Health Journey
                    </a>
                    <p style="font-size: 14px; color: #6b7280; margin-top: 15px;">
                        <strong>Unique Tracker ID:</strong> HT-{unique_id.upper()}<br>
                        This link is personalized for you and tracks your progress automatically!
                    </p>
                </div>
                
                <div style="padding: 20px;">
                    <div class="section">
                        <h2 style="color: #667eea; margin-bottom: 20px;">🏃 Weekly Exercise Plan</h2>
                        <div class="task">
                            <div class="time">⏰ Daily Morning Exercise</div>
                            <p>30 minutes of brisk walking, cycling, or swimming</p>
                        </div>
                        <div class="task">
                            <div class="time">⏰ Evening Relaxation</div>
                            <p>10-15 minutes of stretching, yoga, or meditation</p>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2 style="color: #667eea; margin-bottom: 20px;">🥗 Nutrition Plan</h2>
                        <div class="task">
                            <div class="time">⏰ 8:30 AM - Healthy Breakfast</div>
                            <p>Oats with fruits, nuts, or whole grain options</p>
                        </div>
                        <div class="task">
                            <div class="time">⏰ 1:00 PM - Nutritious Lunch</div>
                            <p>Balanced meal with proteins, vegetables, and grains</p>
                        </div>
                        <div class="task">
                            <div class="time">⏰ 5:00 PM - Healthy Snack</div>
                            <p>Fresh fruits, nuts, or yogurt</p>
                        </div>
                        <div class="task">
                            <div class="time">⏰ 8:30 PM - Light Dinner</div>
                            <p>Light meal with vegetables and lean proteins</p>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2 style="color: #667eea; margin-bottom: 20px;">💊 Medication Schedule</h2>
                        <div class="task">
                            <div class="time">⏰ 9:00 AM - Morning Supplements</div>
                            <p>Iron tablet after breakfast</p>
                        </div>
                        <div class="task">
                            <div class="time">⏰ 1:30 PM - Afternoon Vitamins</div>
                            <p>Vitamin B12 or other prescribed supplements</p>
                        </div>
                        <div class="task">
                            <div class="time">⏰ 10:00 PM - Evening Supplements</div>
                            <p>Folic acid or bedtime medications</p>
                        </div>
                    </div>
                </div>
                
                <div class="footer">
                    <p>💡 <strong>Pro Tip:</strong> Your progress is automatically saved and synced with the main dashboard!</p>
                    <p>📱 Add this link to your phone's home screen for quick access</p>
                    <p>🎯 Complete all 63 weekly tasks to achieve 100% health score!</p>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            
            messages.success(request, f'Health tracker email sent successfully to {recipient_name}!')
            messages.info(request, f'Progress URL: {progress_url}')
            messages.info(request, f'Unique Tracker ID: HT-{unique_id.upper()}')
            
        except Exception as e:
            messages.error(request, f'Failed to send email: {str(e)}')
    
    return redirect('website:dashboard')

@login_required(login_url='website:signin')
def view_report(request, report_id):
    report = get_object_or_404(MedicalReport, id=report_id, user=request.user)
    return render(request, 'website/result.html', {'analysis': report.analysis})

@login_required(login_url='website:signin')
def delete_report(request, report_id):
    if request.method == 'POST':
        try:
            report = get_object_or_404(MedicalReport, id=report_id, user=request.user)
            report.delete()
            messages.success(request, 'Report deleted successfully!')
        except Exception as e:
            messages.error(request, f'Failed to delete report: {str(e)}')
    
    return redirect('website:dashboard')

@login_required(login_url='website:signin')
def delete_tracker(request, tracker_id):
    if request.method == 'POST':
        try:
            progress_file = os.path.join(os.path.dirname(__file__), 'progress_data.json')
            
            if os.path.exists(progress_file):
                with open(progress_file, 'r') as f:
                    progress_data = json.load(f)
                
                if tracker_id in progress_data:
                    del progress_data[tracker_id]
                    
                    with open(progress_file, 'w') as f:
                        json.dump(progress_data, f, indent=2)
                    
                    messages.success(request, f'Tracker {tracker_id} deleted successfully!')
                else:
                    messages.error(request, 'Tracker not found!')
            else:
                messages.error(request, 'No progress data found!')
                
        except Exception as e:
            messages.error(request, f'Failed to delete tracker: {str(e)}')
    
    return redirect('website:dashboard')

def progress_tracker(request, tracker_id):
    """Public progress tracker view - no login required"""
    return render(request, 'website/progress.html', {
        'tracker_id': tracker_id
    })

# API endpoints for progress synchronization
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import os

@csrf_exempt
def update_progress_api(request, tracker_id):
    """API to update progress data"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            task_id = data.get('task_id')
            completed = data.get('completed', False)
            user_name = data.get('user_name', '')
            user_email = data.get('user_email', '')
            
            # Save progress to JSON file
            progress_file = os.path.join(os.path.dirname(__file__), 'progress_data.json')
            
            if os.path.exists(progress_file):
                with open(progress_file, 'r') as f:
                    progress_data = json.load(f)
            else:
                progress_data = {}
            
            if tracker_id not in progress_data:
                progress_data[tracker_id] = {
                    'user_name': user_name,
                    'user_email': user_email,
                    'tasks': {},
                    'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
                }
            
            progress_data[tracker_id]['tasks'][task_id] = completed
            progress_data[tracker_id]['last_updated'] = time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Calculate completion rate
            completed_tasks = sum(1 for v in progress_data[tracker_id]['tasks'].values() if v)
            total_tasks = 63  # 7 days * 9 tasks
            completion_rate = int((completed_tasks / total_tasks) * 100)
            progress_data[tracker_id]['completion_rate'] = completion_rate
            
            with open(progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2)
            
            return JsonResponse({
                'success': True, 
                'completion_rate': completion_rate,
                'completed_tasks': completed_tasks,
                'total_tasks': total_tasks
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def get_progress_api(request, tracker_id):
    """API to get progress data"""
    try:
        progress_file = os.path.join(os.path.dirname(__file__), 'progress_data.json')
        
        if os.path.exists(progress_file):
            with open(progress_file, 'r') as f:
                progress_data = json.load(f)
                
            if tracker_id in progress_data:
                return JsonResponse({
                    'success': True,
                    'data': progress_data[tracker_id]
                })
        
        return JsonResponse({
            'success': True,
            'data': {
                'tasks': {},
                'completion_rate': 0,
                'user_name': '',
                'user_email': ''
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def load_all_progress():
    """Load all progress data for dashboard"""
    try:
        progress_file = os.path.join(os.path.dirname(__file__), 'progress_data.json')
        
        if os.path.exists(progress_file):
            with open(progress_file, 'r') as f:
                progress_data = json.load(f)
                
            progress_list = []
            for tracker_id, data in progress_data.items():
                completed_tasks = sum(1 for v in data.get('tasks', {}).values() if v)
                total_tasks = 63
                completion_rate = int((completed_tasks / total_tasks) * 100)
                
                progress_list.append({
                    'tracker_id': tracker_id,
                    'user_name': data.get('user_name', 'Unknown'),
                    'user_email': data.get('user_email', ''),
                    'completed_tasks': completed_tasks,
                    'total_tasks': total_tasks,
                    'completion_rate': completion_rate,
                    'last_updated': data.get('last_updated', 'Never'),
                    'created_at': data.get('created_at', 'Unknown')
                })
            
            # Sort by last updated (most recent first)
            progress_list.sort(key=lambda x: x['last_updated'], reverse=True)
            return progress_list
    except Exception as e:
        print(f"Error loading progress: {e}")
    
    return []

def calculate_overall_completion_rate():
    """Calculate overall completion rate from all trackers"""
    progress_list = load_all_progress()
    if not progress_list:
        return 0
    
    total_rate = sum(item['completion_rate'] for item in progress_list)
    return int(total_rate / len(progress_list))

def index(request):
    return render(request, 'website/index.html')

def ai_doctor(request):
    return render(request, 'website/ai-doctor.html')

def lab_test(request):
    return render(request, 'website/lab-test.html')

def second_opinion(request):
    return render(request, 'website/second-opinion.html')

def blog(request):
    return render(request, 'website/blog.html')

def symptoms_guide(request):
    return render(request, 'website/symptoms-guide.html')

def knowledge_base(request):
    return render(request, 'website/knowledge-base.html')

def glossary(request):
    return render(request, 'website/glossary.html')

def pricing(request):
    return render(request, 'website/pricing.html')

def forgot_password(request):
    return render(request, 'website/forgot-password.html')

@login_required(login_url='website:signin')
def reminder_page(request):
    report_id = request.GET.get('report_id')
    if report_id:
        try:
            report = MedicalReport.objects.get(id=report_id, user=request.user)
            analysis = report.analysis
        except MedicalReport.DoesNotExist:
            analysis = ""
    else:
        latest_report = MedicalReport.objects.filter(user=request.user).order_by('-uploaded_at').first()
        analysis = latest_report.analysis if latest_report else ""
    
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    return render(request, 'website/reminder.html', {
        'days': days,
        'diet_plan': analysis,
        'exercise_plan': analysis,
        'medicine_plan': analysis
    })

# Doctor Registration Views
from .forms import DoctorForm, AppointmentForm
from .models import Doctor, Appointment

def doctor_register(request):
    if request.method == 'POST':
        form = DoctorForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Doctor registered successfully!'})
            messages.success(request, 'Doctor registered successfully!')
            return redirect('website:doctors_list')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = form.errors.as_json()
                return JsonResponse({'success': False, 'message': 'Please correct the errors in the form.', 'errors': errors})
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = DoctorForm()
    
    return render(request, 'website/doctor_register.html', {'form': form})

@login_required(login_url='website:signin')
def doctors_list(request):
    doctors = Doctor.objects.all().order_by('-created_at')
    my_appointments = []
    if request.user.is_authenticated:
        my_appointments = Appointment.objects.filter(patient_email=request.user.email).order_by('-created_at')
    return render(request, 'website/doctors_list.html', {'doctors': doctors, 'my_appointments': my_appointments})

@login_required(login_url='website:signin')
def book_appointment(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    date = request.GET.get('date')
    time_slot = request.GET.get('time_slot')
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.doctor = doctor
            appointment.appointment_date = request.POST.get('appointment_date')
            appointment.time_slot = request.POST.get('time_slot')
            appointment.save()
            
            # Generate Google Meet link
            meet_link = f"https://meet.google.com/new"
            
            # Send email to patient
            try:
                sender_email = "geethageetha7817@gmail.com"
                sender_password = "egkw lkki fzxp giir"
                
                # Email to patient
                msg_patient = MIMEMultipart('alternative')
                msg_patient['From'] = sender_email
                msg_patient['To'] = appointment.patient_email
                msg_patient['Subject'] = f'Appointment Confirmed with Dr. {doctor.name}'
                
                html_patient = f"""
                <html><body style="font-family: Arial, sans-serif;">
                <h2 style="color: #667eea;">Appointment Confirmed!</h2>
                <p>Dear {appointment.patient_name},</p>
                <p>Your appointment has been confirmed with:</p>
                <ul>
                    <li><strong>Doctor:</strong> Dr. {doctor.name}</li>
                    <li><strong>Specialization:</strong> {doctor.specialization}</li>
                    <li><strong>Date:</strong> {appointment.appointment_date}</li>
                    <li><strong>Time:</strong> {appointment.time_slot}</li>
                </ul>
                <p><a href="{meet_link}" style="background: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Join Google Meet</a></p>
                </body></html>
                """
                msg_patient.attach(MIMEText(html_patient, 'html'))
                
                # Email to doctor
                msg_doctor = MIMEMultipart('alternative')
                msg_doctor['From'] = sender_email
                msg_doctor['To'] = doctor.email
                msg_doctor['Subject'] = f'New Appointment with {appointment.patient_name}'
                
                html_doctor = f"""
                <html><body style="font-family: Arial, sans-serif;">
                <h2 style="color: #667eea;">New Appointment Scheduled</h2>
                <p>Dear Dr. {doctor.name},</p>
                <p>A new appointment has been scheduled:</p>
                <ul>
                    <li><strong>Patient:</strong> {appointment.patient_name}</li>
                    <li><strong>Email:</strong> {appointment.patient_email}</li>
                    <li><strong>Phone:</strong> {appointment.patient_phone}</li>
                    <li><strong>Date:</strong> {appointment.appointment_date}</li>
                    <li><strong>Time:</strong> {appointment.time_slot}</li>
                </ul>
                <p><a href="{meet_link}" style="background: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Join Google Meet</a></p>
                </body></html>
                """
                msg_doctor.attach(MIMEText(html_doctor, 'html'))
                
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg_patient)
                server.send_message(msg_doctor)
                server.quit()
            except Exception as e:
                print(f"Email error: {e}")
            
            messages.success(request, 'Appointment booked successfully!')
            return redirect('website:appointment_meeting', appointment_id=appointment.id)
    else:
        form = AppointmentForm()
    
    return render(request, 'website/book_appointment.html', {
        'doctor': doctor,
        'form': form,
        'date': date,
        'time_slot': time_slot
    })

def appointment_meeting(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    return render(request, 'website/appointment_meeting.html', {'appointment': appointment})