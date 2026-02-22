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
import threading


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

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
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

def signout(request):
    logout(request)
    messages.success(request, "Logged out successfully")
    return redirect('website:signin')


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
        'task_progress': load_user_progress(request.user.email),
        'completion_rate': calculate_user_completion_rate(request.user.email),
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
        
        # Generate unique progress link
        timestamp = str(int(time.time()))
        unique_id = hashlib.md5(f"{recipient_email}{timestamp}".encode()).hexdigest()[:8]
        
        # Get the current site domain
        domain = request.get_host()
        protocol = 'https' if request.is_secure() else 'http'
        progress_url = f"{protocol}://{domain}/progress/{unique_id}/?name={recipient_name}&email={recipient_email}"
        
        # Send email in background thread to avoid timeout
        def send_email_async():
            try:
                sender_email = "geethageetha7817@gmail.com"
                sender_password = "egkw lkki fzxp giir"
                
                msg = MIMEMultipart('alternative')
                msg['From'] = sender_email
                msg['To'] = recipient_email
                msg['Subject'] = f'🏥 Your Weekly Health Plan - {recipient_name}'
                
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
                
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.set_debuglevel(0)
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
                server.quit()
            except Exception as e:
                print(f"Email error: {e}")
        
        # Start email sending in background
        thread = threading.Thread(target=send_email_async)
        thread.daemon = True
        thread.start()
        
        # Respond immediately
        messages.success(request, f'Health tracker email is being sent to {recipient_name}!')
        messages.info(request, f'Unique Tracker ID: HT-{unique_id.upper()}')
    
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

def load_user_progress(user_email):
    """Load progress data for specific user"""
    try:
        progress_file = os.path.join(os.path.dirname(__file__), 'progress_data.json')
        
        if os.path.exists(progress_file):
            with open(progress_file, 'r') as f:
                progress_data = json.load(f)
                
            progress_list = []
            for tracker_id, data in progress_data.items():
                if data.get('user_email', '') == user_email:
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
            
            progress_list.sort(key=lambda x: x['last_updated'], reverse=True)
            return progress_list
    except Exception as e:
        print(f"Error loading progress: {e}")
    
    return []

def calculate_user_completion_rate(user_email):
    """Calculate completion rate for specific user"""
    progress_list = load_user_progress(user_email)
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

def article(request, article_id):
    articles = {
        '1': {
            'title': 'How AI Doctors Are Revolutionizing Preventive Healthcare',
            'category': 'AI DOCTOR',
            'icon': '🤖',
            'date': 'Dec 28, 2025',
            'read_time': '8',
            'views': '2.4K',
            'content': '''<h2>The Rise of AI in Healthcare</h2>
<p>Artificial Intelligence is transforming the healthcare landscape in unprecedented ways. AI-powered symptom checkers and virtual doctors are now capable of catching health issues before they become serious problems, marking a new era in preventive medicine.</p>

<h3>Early Detection Saves Lives</h3>
<p>Studies show that early detection of diseases can improve survival rates by up to 90%. AI doctors analyze patterns in your symptoms, medical history, and lifestyle factors to identify potential health risks months or even years before traditional methods.</p>

<h3>Key Benefits of AI Doctors</h3>
<ul>
<li><strong>24/7 Availability:</strong> Get medical advice anytime, anywhere without waiting for appointments</li>
<li><strong>Personalized Care:</strong> AI analyzes your unique health profile to provide tailored recommendations</li>
<li><strong>Cost-Effective:</strong> Reduce unnecessary doctor visits and catch issues early when treatment is less expensive</li>
<li><strong>Data-Driven Insights:</strong> Leverage millions of medical cases to provide accurate assessments</li>
</ul>

<h3>Real-World Impact</h3>
<p>Healthcare providers using AI diagnostic tools have reported a 40% reduction in misdiagnosis rates. Patients benefit from faster, more accurate assessments that lead to better health outcomes.</p>

<h2>The Future is Here</h2>
<p>As AI technology continues to evolve, we're moving toward a future where preventive healthcare is accessible to everyone. The combination of human expertise and AI capabilities creates a powerful tool for maintaining optimal health.</p>'''
        },
        '2': {
            'title': 'Understanding Your Blood Test Results: A Complete Guide',
            'category': 'LAB TESTS',
            'icon': '🧪',
            'date': 'Dec 25, 2025',
            'read_time': '6',
            'views': '5.2K',
            'content': '''<h2>Decoding Your Blood Work</h2>
<p>Blood tests are one of the most powerful diagnostic tools available, yet many people struggle to understand what their results mean. This comprehensive guide will help you decode 20+ common blood biomarkers.</p>

<h3>Complete Blood Count (CBC)</h3>
<p>The CBC measures different components of your blood:</p>
<ul>
<li><strong>Red Blood Cells (RBC):</strong> Carry oxygen throughout your body. Low levels may indicate anemia.</li>
<li><strong>White Blood Cells (WBC):</strong> Fight infections. High levels may suggest infection or inflammation.</li>
<li><strong>Platelets:</strong> Help blood clot. Abnormal levels can affect bleeding and clotting.</li>
<li><strong>Hemoglobin:</strong> Protein in red blood cells. Low levels cause fatigue and weakness.</li>
</ul>

<h3>Metabolic Panel</h3>
<p>This panel checks your body's chemical balance and metabolism:</p>
<ul>
<li><strong>Glucose:</strong> Blood sugar levels. High levels may indicate diabetes risk.</li>
<li><strong>Calcium:</strong> Important for bones and muscles. Abnormal levels affect many body functions.</li>
<li><strong>Electrolytes:</strong> Sodium, potassium, chloride maintain fluid balance.</li>
</ul>

<h3>Lipid Panel</h3>
<p>Measures cholesterol and triglycerides to assess heart disease risk:</p>
<ul>
<li><strong>Total Cholesterol:</strong> Should be below 200 mg/dL</li>
<li><strong>LDL (Bad Cholesterol):</strong> Should be below 100 mg/dL</li>
<li><strong>HDL (Good Cholesterol):</strong> Should be above 60 mg/dL</li>
<li><strong>Triglycerides:</strong> Should be below 150 mg/dL</li>
</ul>

<h2>Taking Action</h2>
<p>Understanding your blood test results empowers you to make informed decisions about your health. Always discuss results with your healthcare provider to create a personalized health plan.</p>'''
        },
        '3': {
            'title': 'Top 5 AI Tools That Could Add 10 Years to Your Life',
            'category': 'PREVENTION',
            'icon': '🛡️',
            'date': 'Dec 22, 2025',
            'read_time': '10',
            'views': '12K',
            'content': '''<h2>The Longevity Revolution</h2>
<p>Advances in AI technology are transforming longevity medicine and preventive care. These evidence-based tools are helping people live longer, healthier lives.</p>

<h3>1. AI-Powered Health Monitoring</h3>
<p>Wearable devices combined with AI algorithms continuously monitor vital signs and detect anomalies before they become serious. Studies show users catch health issues 3x faster than traditional methods.</p>

<h3>2. Personalized Nutrition Planning</h3>
<p>AI analyzes your genetics, microbiome, and lifestyle to create customized meal plans that optimize your health. Users report 40% improvement in energy levels and 25% reduction in chronic inflammation.</p>

<h3>3. Predictive Disease Modeling</h3>
<p>Machine learning models analyze your health data to predict disease risk years in advance. Early intervention can prevent or delay onset of chronic conditions like diabetes and heart disease.</p>

<h3>4. Mental Health Support</h3>
<p>AI-powered mental health apps provide 24/7 support, cognitive behavioral therapy, and stress management techniques. Regular use reduces anxiety and depression symptoms by up to 50%.</p>

<h3>5. Sleep Optimization</h3>
<p>AI sleep coaches analyze your sleep patterns and provide personalized recommendations to improve sleep quality. Better sleep is linked to reduced disease risk and increased lifespan.</p>

<h2>The Science Behind Longevity</h2>
<p>Research shows that lifestyle factors account for 70% of longevity outcomes. These AI tools help you optimize the controllable factors that determine how long and how well you live.</p>

<h3>Getting Started</h3>
<p>You don't need to use all these tools at once. Start with one or two that address your biggest health concerns, then gradually incorporate others as you build healthy habits.</p>'''
        },
        '4': {
            'title': 'Why Lab Test Interpretation Accuracy Matters More Than Ever',
            'category': 'RESEARCH',
            'icon': '🔬',
            'date': 'Dec 20, 2025',
            'read_time': '7',
            'views': '3.8K',
            'content': '''<h2>The Hidden Crisis in Healthcare</h2>
<p>A groundbreaking new study reveals that 68% of patients misunderstand their lab results, leading to delayed treatment, unnecessary anxiety, and poor health outcomes.</p>

<h3>The Communication Gap</h3>
<p>Despite advances in medical testing, there's a significant gap between test results and patient understanding. Doctors often lack time to explain results thoroughly, leaving patients confused and uncertain about their health status.</p>

<h3>What Doctors Aren't Telling You</h3>
<ul>
<li><strong>Reference Ranges Vary:</strong> "Normal" ranges differ by lab, age, gender, and ethnicity</li>
<li><strong>Trends Matter More:</strong> A single result means less than tracking changes over time</li>
<li><strong>Context is Critical:</strong> Results must be interpreted alongside symptoms and medical history</li>
<li><strong>Optimal vs. Normal:</strong> Being in the "normal" range doesn't mean optimal health</li>
</ul>

<h3>The Cost of Misunderstanding</h3>
<p>Misinterpreted lab results lead to:</p>
<ul>
<li>Delayed diagnosis and treatment</li>
<li>Unnecessary follow-up tests and procedures</li>
<li>Increased healthcare costs</li>
<li>Patient anxiety and stress</li>
<li>Poor medication adherence</li>
</ul>

<h2>The Solution: AI-Powered Interpretation</h2>
<p>Modern AI tools can analyze lab results in context, explain what numbers mean in plain language, and provide actionable recommendations. This bridges the communication gap and empowers patients to take control of their health.</p>

<h3>Taking Control of Your Health</h3>
<p>Don't just accept lab results at face value. Ask questions, seek second opinions, and use technology to better understand your health data. Your health is too important to leave to chance.</p>'''
        }
    }
    
    article = articles.get(article_id)
    if not article:
        return redirect('website:blog')
    
    return render(request, 'website/article.html', {'article': article})

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
            
            # Use your permanent Google Meet link
            meet_link = "https://meet.google.com/fox-bczh-rrv"  # Replace with your actual Meet link
            appointment.meet_link = meet_link
            appointment.save()
            
            # Send email to patient and doctor
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
    
    # Use saved meet link or default
    meet_link = appointment.meet_link or "https://meet.google.com/your-meeting-code"  # Replace with your actual Meet link
    
    return render(request, 'website/appointment_meeting.html', {'appointment': appointment, 'meet_link': meet_link})
