from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from .models import MedicalReport, InAppNotification, PushSubscription, Appointment
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_GET
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from urllib.parse import urlencode
from datetime import datetime, timedelta
from mediscanner.analyzer import analyze_medical_report
from mediscanner.symptom_agent import SymptomAgent
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import hashlib
import time
import threading
import json
import os
import uuid
import secrets


def _get_smtp_sender_credentials() -> tuple[str, str]:
    sender_email = (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip()
    sender_password = getattr(settings, 'EMAIL_HOST_PASSWORD', '') or ''

    if not sender_email or not sender_password:
        raise RuntimeError(
            'Email sending is not configured. Set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD (env vars).'
        )

    return sender_email, sender_password


def _open_smtp_connection() -> smtplib.SMTP:
    host = getattr(settings, 'EMAIL_HOST', 'smtp.gmail.com')
    port = int(getattr(settings, 'EMAIL_PORT', 587))
    use_tls = bool(getattr(settings, 'EMAIL_USE_TLS', True))

    server = smtplib.SMTP(host, port)
    server.set_debuglevel(0)
    if use_tls:
        server.starttls()
    return server


def _get_vapid_public_key():
    return os.environ.get('VAPID_PUBLIC_KEY', '').strip()


def _get_vapid_private_key():
    return os.environ.get('VAPID_PRIVATE_KEY', '').strip()


@require_GET
def push_public_key(request):
    return JsonResponse({'publicKey': _get_vapid_public_key()})


@login_required(login_url='website:signin')
@require_POST
def push_subscribe(request):
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        payload = {}

    sub = payload.get('subscription') or {}
    endpoint = sub.get('endpoint')
    keys = sub.get('keys') or {}
    p256dh = keys.get('p256dh')
    auth = keys.get('auth')

    if not endpoint or not p256dh or not auth:
        return JsonResponse({'ok': False, 'error': 'Invalid subscription payload.'}, status=400)

    endpoint_hash = hashlib.sha256(endpoint.encode('utf-8')).hexdigest()

    obj, _created = PushSubscription.objects.update_or_create(
        endpoint_hash=endpoint_hash,
        defaults={'user': request.user, 'endpoint': endpoint, 'p256dh': p256dh, 'auth': auth},
    )

    if obj.user_id != request.user.id:
        obj.user = request.user
        obj.p256dh = p256dh
        obj.auth = auth
        obj.save(update_fields=['user', 'p256dh', 'auth', 'updated_at'])

    return JsonResponse({'ok': True})


@login_required(login_url='website:signin')
@require_POST
def push_unsubscribe(request):
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        payload = {}

    endpoint = payload.get('endpoint')
    if not endpoint:
        return JsonResponse({'ok': False, 'error': 'Missing endpoint.'}, status=400)

    endpoint_hash = hashlib.sha256(endpoint.encode('utf-8')).hexdigest()

    deleted, _ = PushSubscription.objects.filter(user=request.user, endpoint_hash=endpoint_hash).delete()
    return JsonResponse({'ok': True, 'deleted': deleted})


@require_GET
def service_worker(request):
    js = """
self.addEventListener('push', function (event) {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (e) { data = {}; }

    const title = data.title || 'Mednudge AI Reminder';
    const hasId = !!data.notification_id;
  const options = {
    body: data.body || '',
        data: { url: data.url || '/', notification_id: data.notification_id || null },
        actions: hasId ? [
            { action: 'taken', title: 'Taken' },
            { action: 'snooze_10', title: 'Snooze 10m' },
        ] : [],
        requireInteraction: hasId,
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function (event) {
    const data = (event.notification && event.notification.data) ? event.notification.data : {};
    const url = data.url || '/';
    const notificationId = data.notification_id;

    async function postJson(path, payload){
        try{
            await fetch(path, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload || {}),
            });
        }catch(e){}
    }

    event.notification.close();

    if(event.action === 'taken' && notificationId){
        event.waitUntil(Promise.all([
            postJson('/api/notifications/taken/', { notification_id: notificationId }),
            clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (clientList) {
                for (const client of clientList) {
                    if (client.url === url && 'focus' in client) return client.focus();
                }
                if (clients.openWindow) return clients.openWindow(url);
            })
        ]));
        return;
    }

    if(event.action === 'snooze_10' && notificationId){
        event.waitUntil(Promise.all([
            postJson('/api/notifications/snooze/', { notification_id: notificationId, minutes: 10 }),
            clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (clientList) {
                for (const client of clientList) {
                    if (client.url === url && 'focus' in client) return client.focus();
                }
                if (clients.openWindow) return clients.openWindow(url);
            })
        ]));
        return;
    }

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (clientList) {
            for (const client of clientList) {
                if (client.url === url && 'focus' in client) return client.focus();
            }
            if (clients.openWindow) return clients.openWindow(url);
        })
    );
});
"""
    return HttpResponse(js, content_type='application/javascript')


@login_required(login_url='website:signin')
@never_cache
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

        try:
            result = analyze_medical_report(file)
        except ValueError as exc:
            return render(request, "website/upload.html", {
                "error": str(exc)
            })
        except Exception:
            return render(request, "website/upload.html", {
                "error": "We couldn't process that file right now. Please try another file format or upload a clearer image."
            })

        try:
            file.seek(0)
        except Exception:
            pass

        report = MedicalReport.objects.create(
            user=request.user if request.user.is_authenticated else None,
            report_file=file,
            analysis=result
        )
        

        return render(request, "website/result.html", {
            "analysis": result,
            "report_id": report.id,
            "report_has_reminder_plan": bool(report.reminder_plan),
        })

    return render(request, "website/upload.html")



@never_cache
def signup(request):
    if request.user.is_authenticated:
        return redirect('website:dashboard')

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


@never_cache
def signin(request):
    next_url = request.POST.get('next') or request.GET.get('next')
    safe_next_url = None
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        safe_next_url = next_url

    if request.user.is_authenticated:
        return redirect(safe_next_url or 'website:dashboard')

    if request.method == "POST":
        email = (request.POST.get('email') or request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''

        if not email or not password:
            messages.error(request, 'Please enter your email and password.')
            signin_url = reverse('website:signin')
            if safe_next_url:
                signin_url = f"{signin_url}?{urlencode({'next': safe_next_url})}"
            return redirect(signin_url)

        user_obj = User.objects.filter(email__iexact=email).first()
        user = None
        if user_obj:
            user = authenticate(request, username=user_obj.username, password=password)

        if user is not None:
            login(request, user)
            return redirect(safe_next_url or 'website:dashboard')

        messages.error(request, 'Invalid email or password')
        signin_url = reverse('website:signin')
        if safe_next_url:
            signin_url = f"{signin_url}?{urlencode({'next': safe_next_url})}"
        return redirect(signin_url)

    return render(request, 'website/signin.html')

@never_cache
def signout(request):
    logout(request)
    messages.success(request, "Logged out successfully")
    return redirect('website:signin')


@login_required(login_url='website:signin')
@never_cache
def dashboard(request):
    user_reports = MedicalReport.objects.filter(user=request.user).order_by('-uploaded_at')
    recent_reports = list(user_reports[:5])

    task_progress = load_user_progress(request.user.email)
    tracker_completion_rate = calculate_user_completion_rate(request.user.email)

    today = timezone.localdate()
    upcoming_appointments = list(
        Appointment.objects.filter(
            patient_email=request.user.email,
            appointment_date__gte=today,
        )
        .select_related('doctor')
        .order_by('appointment_date', 'time_slot', '-created_at')[:5]
    )

    context = {
        'recent_reports': recent_reports,
        'upcoming_appointments': upcoming_appointments,
        'task_progress': task_progress,
        'tracker_completion_rate': tracker_completion_rate,
        'report_count': user_reports.count(),
        'appointment_count': len(upcoming_appointments),
        'tracker_count': len(task_progress),
    }
    
    return render(request, 'website/dashboard_v2.html', context)

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
                sender_email, sender_password = _get_smtp_sender_credentials()
                
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
                
                server = _open_smtp_connection()
                try:
                    server.login(sender_email, sender_password)
                    server.send_message(msg)
                finally:
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
@never_cache
def view_report(request, report_id):
    report = get_object_or_404(MedicalReport, id=report_id, user=request.user)
    return render(request, 'website/result.html', {
        'analysis': report.analysis,
        'report_id': report.id,
        'report_has_reminder_plan': bool(report.reminder_plan),
        'bfcache_reload_guard': True,
    })


def _build_simple_week_plan(*, include_exercise: bool, include_diet: bool, include_medicine: bool):
    week_plan = {}

    for day_index in range(7):
        day_bucket = {
            "exercises": [],
            "foods": [],
            "tablets": [],
        }

        if include_exercise:
            day_bucket["exercises"].extend([
                {
                    "id": f"ex-{day_index}-1",
                    "name": "Brisk walking",
                    "detail": "20–30 minutes at a comfortable pace",
                    "tag": "Cardio",
                    "time": "7:00 AM",
                },
                {
                    "id": f"ex-{day_index}-2",
                    "name": "Light stretching",
                    "detail": "10 minutes (full body)",
                    "tag": "Mobility",
                    "time": "7:30 PM",
                },
            ])

        if include_diet:
            day_bucket["foods"].extend([
                {
                    "id": f"food-{day_index}-1",
                    "name": "Breakfast",
                    "detail": "High-fiber meal (oats/whole grains) + fruit",
                    "tag": "Balanced",
                    "time": "8:30 AM",
                },
                {
                    "id": f"food-{day_index}-2",
                    "name": "Lunch",
                    "detail": "Protein + vegetables + complex carbs",
                    "tag": "Balanced",
                    "time": "1:00 PM",
                },
                {
                    "id": f"food-{day_index}-3",
                    "name": "Snack",
                    "detail": "Fruit + handful of nuts (if suitable)",
                    "tag": "Snack",
                    "time": "5:00 PM",
                },
                {
                    "id": f"food-{day_index}-4",
                    "name": "Dinner",
                    "detail": "Light dinner + vegetables",
                    "tag": "Light",
                    "time": "8:30 PM",
                },
            ])

        if include_medicine:
            day_bucket["tablets"].extend([
                {
                    "id": f"med-{day_index}-1",
                    "name": "Morning medication",
                    "detail": "As prescribed by your clinician",
                    "tag": "Prescription",
                    "time": "9:00 AM",
                },
                {
                    "id": f"med-{day_index}-2",
                    "name": "Evening medication",
                    "detail": "As prescribed by your clinician",
                    "tag": "Prescription",
                    "time": "9:00 PM",
                },
            ])

        week_plan[day_index] = day_bucket

    return week_plan


def _parse_time_string(time_str: str):
    if not time_str:
        return datetime.strptime("09:00 AM", "%I:%M %p").time()

    cleaned = str(time_str).strip()
    for fmt in ("%I:%M %p", "%I %p"):
        try:
            return datetime.strptime(cleaned, fmt).time()
        except Exception:
            continue

    return datetime.strptime("09:00 AM", "%I:%M %p").time()


def _schedule_notifications_for_report(*, user, report: MedicalReport, week_plan: dict):
    now = timezone.now()
    tz = timezone.get_current_timezone()
    today = timezone.localdate()
    start_of_week = today - timedelta(days=today.weekday())

    # Avoid duplicates if user re-adds the plan.
    InAppNotification.objects.filter(
        user=user,
        report=report,
        delivered_at__isnull=True,
        scheduled_for__gte=now,
    ).delete()

    notifications_to_create = []

    def add_for_item(day_index: int, notification_type: str, item: dict):
        scheduled_time = _parse_time_string(item.get("time"))
        scheduled_date = start_of_week + timedelta(days=int(day_index))
        scheduled_dt = timezone.make_aware(datetime.combine(scheduled_date, scheduled_time), tz)
        if scheduled_dt <= now:
            scheduled_dt = scheduled_dt + timedelta(days=7)

        title = item.get("name") or "Reminder"
        detail = item.get("detail") or ""
        time_label = str(item.get("time") or "").strip()

        if notification_type == "exercise":
            title = f"Exercise • {title}"
        elif notification_type == "diet":
            title = f"Diet • {title}"
        elif notification_type == "medicine":
            title = f"Medicine • {title}"
        else:
            title = f"Reminder • {title}"

        if time_label:
            body = f"{detail}\nTime: {time_label}".strip()
        else:
            body = detail

        notifications_to_create.append(
            InAppNotification(
                user=user,
                report=report,
                notification_type=notification_type,
                title=title[:140],
                body=body,
                scheduled_for=scheduled_dt,
            )
        )

    for day_index, day_bucket in (week_plan or {}).items():
        try:
            normalized_day_index = int(day_index)
        except Exception:
            continue

        for item in (day_bucket or {}).get("exercises", []) or []:
            add_for_item(normalized_day_index, "exercise", item)
        for item in (day_bucket or {}).get("foods", []) or []:
            add_for_item(normalized_day_index, "diet", item)
        for item in (day_bucket or {}).get("tablets", []) or []:
            add_for_item(normalized_day_index, "medicine", item)

    if notifications_to_create:
        InAppNotification.objects.bulk_create(notifications_to_create)


def _normalize_day_key(day_index):
    try:
        return str(int(day_index))
    except Exception:
        return None


@login_required(login_url='website:signin')
@require_POST
def upsert_reminder_item_api(request):
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        payload = {}

    report_id = payload.get('report_id')
    day_index = payload.get('day_index')
    bucket = payload.get('bucket')
    item = payload.get('item') or {}

    if not report_id:
        return JsonResponse({'ok': False, 'error': 'Missing report_id.'}, status=400)
    day_key = _normalize_day_key(day_index)
    if day_key is None:
        return JsonResponse({'ok': False, 'error': 'Invalid day_index.'}, status=400)

    allowed_buckets = {'exercises', 'foods', 'tablets'}
    if bucket not in allowed_buckets:
        return JsonResponse({'ok': False, 'error': 'Invalid bucket.'}, status=400)

    name = str(item.get('name') or '').strip()
    detail = str(item.get('detail') or '').strip()
    tag = str(item.get('tag') or '').strip()
    time_str = str(item.get('time') or '').strip()

    if not name:
        return JsonResponse({'ok': False, 'error': 'Name is required.'}, status=400)
    if not time_str:
        return JsonResponse({'ok': False, 'error': 'Time is required (e.g. 9:00 AM).'}, status=400)

    # Validate time format (falls back to default if invalid)
    try:
        _parse_time_string(time_str)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Invalid time format. Use e.g. 9:00 AM.'}, status=400)

    report = get_object_or_404(MedicalReport, id=report_id, user=request.user)

    reminder_plan = report.reminder_plan if isinstance(report.reminder_plan, dict) else {}
    week_plan = reminder_plan.get('week_plan') if isinstance(reminder_plan.get('week_plan'), dict) else {}

    day_bucket = week_plan.get(day_key) or week_plan.get(int(day_key))
    if not isinstance(day_bucket, dict):
        day_bucket = {'exercises': [], 'foods': [], 'tablets': []}

    for k in ('exercises', 'foods', 'tablets'):
        if not isinstance(day_bucket.get(k), list):
            day_bucket[k] = []

    item_id = str(item.get('id') or '').strip()
    if not item_id:
        prefix = {'exercises': 'ex', 'foods': 'food', 'tablets': 'med'}[bucket]
        item_id = f"{prefix}-{day_key}-{uuid.uuid4().hex[:8]}"

    updated_item = {
        'id': item_id,
        'name': name,
        'detail': detail,
        'tag': tag,
        'time': time_str,
    }

    replaced = False
    for idx, existing in enumerate(day_bucket[bucket]):
        if isinstance(existing, dict) and str(existing.get('id') or '') == item_id:
            day_bucket[bucket][idx] = updated_item
            replaced = True
            break
    if not replaced:
        day_bucket[bucket].append(updated_item)

    # Ensure day bucket is persisted under string key (JSON-safe)
    week_plan[day_key] = day_bucket
    reminder_plan['week_plan'] = week_plan
    report.reminder_plan = reminder_plan
    report.save(update_fields=['reminder_plan'])

    _schedule_notifications_for_report(user=request.user, report=report, week_plan=week_plan)

    return JsonResponse({'ok': True, 'item': updated_item, 'day_index': int(day_key), 'bucket': bucket})


@login_required(login_url='website:signin')
@require_POST
def delete_reminder_item_api(request):
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        payload = {}

    report_id = payload.get('report_id')
    day_index = payload.get('day_index')
    bucket = payload.get('bucket')
    item_id = str(payload.get('item_id') or '').strip()

    if not report_id:
        return JsonResponse({'ok': False, 'error': 'Missing report_id.'}, status=400)
    day_key = _normalize_day_key(day_index)
    if day_key is None:
        return JsonResponse({'ok': False, 'error': 'Invalid day_index.'}, status=400)

    allowed_buckets = {'exercises', 'foods', 'tablets'}
    if bucket not in allowed_buckets:
        return JsonResponse({'ok': False, 'error': 'Invalid bucket.'}, status=400)
    if not item_id:
        return JsonResponse({'ok': False, 'error': 'Missing item_id.'}, status=400)

    report = get_object_or_404(MedicalReport, id=report_id, user=request.user)
    reminder_plan = report.reminder_plan if isinstance(report.reminder_plan, dict) else {}
    week_plan = reminder_plan.get('week_plan') if isinstance(reminder_plan.get('week_plan'), dict) else {}

    day_bucket = week_plan.get(day_key) or week_plan.get(int(day_key))
    if not isinstance(day_bucket, dict):
        return JsonResponse({'ok': True, 'deleted': 0})

    items = day_bucket.get(bucket)
    if not isinstance(items, list):
        return JsonResponse({'ok': True, 'deleted': 0})

    before = len(items)
    day_bucket[bucket] = [x for x in items if not (isinstance(x, dict) and str(x.get('id') or '') == item_id)]
    deleted = before - len(day_bucket[bucket])

    week_plan[day_key] = day_bucket
    reminder_plan['week_plan'] = week_plan
    report.reminder_plan = reminder_plan
    report.save(update_fields=['reminder_plan'])

    _schedule_notifications_for_report(user=request.user, report=report, week_plan=week_plan)

    return JsonResponse({'ok': True, 'deleted': deleted, 'day_index': int(day_key), 'bucket': bucket, 'item_id': item_id})


@login_required(login_url='website:signin')
@require_POST
def create_reminder_plan(request):
    report_id = request.POST.get('report_id')
    include_exercise = bool(request.POST.get('include_exercise'))
    include_diet = bool(request.POST.get('include_diet'))
    include_medicine = bool(request.POST.get('include_medicine'))

    if not report_id:
        messages.error(request, 'Missing report id.')
        return redirect('website:reports')

    if not (include_exercise or include_diet or include_medicine):
        messages.error(request, 'Select at least one plan to add to reminders.')
        return redirect('website:view_report', report_id=report_id)

    report = get_object_or_404(MedicalReport, id=report_id, user=request.user)

    week_plan = _build_simple_week_plan(
        include_exercise=include_exercise,
        include_diet=include_diet,
        include_medicine=include_medicine,
    )
    report.reminder_plan = {
        "week_plan": week_plan,
        "include_exercise": include_exercise,
        "include_diet": include_diet,
        "include_medicine": include_medicine,
    }
    report.save(update_fields=['reminder_plan'])

    _schedule_notifications_for_report(user=request.user, report=report, week_plan=week_plan)

    messages.success(request, 'Added your selected plan(s) to the Reminder dashboard for this report.')
    reminder_url = reverse('website:reminder')
    return redirect(f"{reminder_url}?{urlencode({'report_id': report.id})}")

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

@login_required(login_url='website:signin')
def get_user_trackers_api(request):
    """API to get all trackers for the logged-in user"""
    try:
        progress_file = os.path.join(os.path.dirname(__file__), 'progress_data.json')
        trackers = []
        if os.path.exists(progress_file):
            with open(progress_file, 'r') as f:
                progress_data = json.load(f)
            for tid, data in progress_data.items():
                if data.get('user_email') == request.user.email:
                    trackers.append({
                        'tracker_id': tid,
                        'user_name': data.get('user_name', ''),
                        'completion_rate': data.get('completion_rate', 0),
                        'last_updated': data.get('last_updated', ''),
                        'tasks': data.get('tasks', {})
                    })
        trackers.sort(key=lambda x: x['last_updated'], reverse=True)
        return JsonResponse({'success': True, 'trackers': trackers})
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

@ensure_csrf_cookie
def ai_doctor(request):
    return render(request, 'website/ai-doctor.html')

def lab_test(request):
    return render(request, 'website/lab-test.html')

def second_opinion(request):
    return render(request, 'website/second-opinion.html')

def blog(request):
    return render(request, 'website/blog.html')


@require_POST
def ai_doctor_chat_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "auth_required"}, status=401)

    try:
        payload = json.loads((request.body or b"{}").decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    message = (payload.get("message") or "").strip()
    history = payload.get("history")

    if not message:
        return JsonResponse({"error": "message_required"}, status=400)

    if len(message) > 4000:
        return JsonResponse({"error": "message_too_long"}, status=400)

    if history is not None and not isinstance(history, list):
        return JsonResponse({"error": "history_must_be_list"}, status=400)

    try:
        agent = SymptomAgent()
        reply = agent.reply(message=message, history=history)
    except Exception as exc:
        import logging

        logger = logging.getLogger(__name__)
        logger.exception("AI doctor chat failed")

        # In production, keep the response generic. In DEBUG, include a short hint.
        from django.conf import settings

        debug_detail = None
        if getattr(settings, "DEBUG", False):
            debug_detail = f"{type(exc).__name__}: {str(exc)[:300]}"

        reply_text = "The AI Doctor service is temporarily unavailable. Please try again in a moment."
        if debug_detail:
            reply_text = f"AI Doctor misconfigured (DEBUG): {debug_detail}"

        return JsonResponse(
            {
                "error": "ai_unavailable",
                "reply": reply_text,
                **({"detail": debug_detail} if debug_detail else {}),
            },
            status=500,
        )

    if not reply:
        reply = "I couldn't generate a response. Please rephrase your symptoms and include when they started."

    return JsonResponse({"reply": reply})

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

@never_cache
def forgot_password(request):
    from .models import PasswordResetCode

    def _hash_code(*, user_id: int, code: str) -> str:
        raw = f"{settings.SECRET_KEY}|{user_id}|{code}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _send_reset_code_email(*, to_email: str, code: str) -> None:
        sender_email, sender_password = _get_smtp_sender_credentials()

        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = 'Your Mednudge AI password reset code'

        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #0f172a;">
            <div style="max-width: 560px; margin: 0 auto; padding: 24px;">
              <h2 style="margin: 0 0 12px;">Password reset code</h2>
              <p style="margin: 0 0 16px; color: #334155;">Use this 6-digit code to reset your password:</p>
              <div style="font-size: 28px; font-weight: 800; letter-spacing: 6px; padding: 16px; background: #eff6ff; border-radius: 12px; display: inline-block;">{code}</div>
              <p style="margin: 16px 0 0; color: #64748b;">This code expires in 10 minutes. If you didn't request this, you can ignore this email.</p>
            </div>
          </body>
        </html>
        """
        msg.attach(MIMEText(html_body, 'html'))

        server = _open_smtp_connection()
        try:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        finally:
            server.quit()

    context = {
        'step': 'request',
        'email': '',
    }

    if request.method == 'POST':
        step = (request.POST.get('step') or 'request').strip()
        email = (request.POST.get('email') or '').strip()
        context['email'] = email

        if step == 'request':
            if not email:
                messages.error(request, 'Please enter your email address.')
                return render(request, 'website/forgot-password.html', context)

            user = User.objects.filter(email__iexact=email).first()
            if not user:
                return redirect('website:signin')

            code = f"{secrets.randbelow(1000000):06d}"
            expires_at = timezone.now() + timedelta(minutes=10)

            PasswordResetCode.objects.create(
                user=user,
                email=user.email,
                code_hash=_hash_code(user_id=user.id, code=code),
                expires_at=expires_at,
            )

            try:
                _send_reset_code_email(to_email=user.email, code=code)
            except Exception:
                messages.error(request, "We couldn't send the reset code right now. Please try again.")
                return render(request, 'website/forgot-password.html', context)

            context['step'] = 'verify'
            messages.success(request, 'A 6-digit reset code has been sent to your email.')
            return render(request, 'website/forgot-password.html', context)

        if step == 'verify':
            code = (request.POST.get('code') or '').strip()
            new_password = request.POST.get('new_password') or ''
            confirm_password = request.POST.get('confirm_password') or ''

            context['step'] = 'verify'

            if not email:
                messages.error(request, 'Missing email. Please start again.')
                context['step'] = 'request'
                return render(request, 'website/forgot-password.html', context)

            user = User.objects.filter(email__iexact=email).first()
            if not user:
                return redirect('website:signin')

            if not (code.isdigit() and len(code) == 6):
                messages.error(request, 'Enter the 6-digit code from your email.')
                return render(request, 'website/forgot-password.html', context)

            if not new_password or len(new_password) < 6:
                messages.error(request, 'New password must be at least 6 characters.')
                return render(request, 'website/forgot-password.html', context)

            if new_password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return render(request, 'website/forgot-password.html', context)

            now = timezone.now()
            reset_obj = (
                PasswordResetCode.objects.filter(
                    user=user,
                    used_at__isnull=True,
                    expires_at__gt=now,
                )
                .order_by('-created_at')
                .first()
            )

            if not reset_obj:
                messages.error(request, 'Reset code expired. Please request a new code.')
                context['step'] = 'request'
                return render(request, 'website/forgot-password.html', context)

            if reset_obj.code_hash != _hash_code(user_id=user.id, code=code):
                messages.error(request, 'Invalid code. Please try again.')
                return render(request, 'website/forgot-password.html', context)

            user.set_password(new_password)
            user.save(update_fields=['password'])
            reset_obj.used_at = now
            reset_obj.save(update_fields=['used_at'])

            messages.success(request, 'Password updated. Please sign in.')
            return redirect('website:signin')

    return render(request, 'website/forgot-password.html', context)

@ensure_csrf_cookie
@login_required(login_url='website:signin')
@never_cache
def reminder_page(request):
    report_id = request.GET.get('report_id')
    report = None
    if report_id:
        report = MedicalReport.objects.filter(id=report_id, user=request.user).first()

    if not report:
        report = MedicalReport.objects.filter(user=request.user).order_by('-uploaded_at').first()

    analysis_json = "{}"
    if report and report.reminder_plan and isinstance(report.reminder_plan, dict):
        week_plan = report.reminder_plan.get('week_plan') or {}
        try:
            analysis_json = json.dumps(week_plan)
        except Exception:
            analysis_json = "{}"

    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    return render(request, 'website/reminder.html', {
        'days': days,
        'report_id': report.id if report else None,
        'analysis_json': analysis_json,
    })


@login_required(login_url='website:signin')
def due_notifications_api(request):
    now = timezone.now()
    due = (
        InAppNotification.objects.filter(
            user=request.user,
            delivered_at__isnull=True,
            taken_at__isnull=True,
            snoozed_until__isnull=True,
            scheduled_for__lte=now,
        )
        .order_by('scheduled_for')
        [:20]
    )

    return JsonResponse({
        'notifications': [
            {
                'id': n.id,
                'title': n.title,
                'body': n.body,
                'type': n.notification_type,
                'scheduled_for': n.scheduled_for.isoformat(),
                'report_id': n.report_id,
            }
            for n in due
        ]
    })


@login_required(login_url='website:signin')
@require_POST
def ack_notifications_api(request):
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        payload = {}

    ids = payload.get('ids') or []
    if not isinstance(ids, list):
        ids = []

    now = timezone.now()
    updated = InAppNotification.objects.filter(
        user=request.user,
        id__in=ids,
        delivered_at__isnull=True,
    ).update(delivered_at=now)

    return JsonResponse({'updated': updated})


@csrf_exempt
@require_POST
def notification_taken_api(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return JsonResponse({'ok': False, 'error': 'Unauthorized'}, status=401)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        payload = {}

    notification_id = payload.get('notification_id')
    if not notification_id:
        return JsonResponse({'ok': False, 'error': 'Missing notification_id.'}, status=400)

    now = timezone.now()
    updated = (
        InAppNotification.objects.filter(user=request.user, id=notification_id)
        .update(taken_at=now, read_at=now)
    )

    return JsonResponse({'ok': True, 'updated': updated})


@csrf_exempt
@require_POST
def notification_snooze_api(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return JsonResponse({'ok': False, 'error': 'Unauthorized'}, status=401)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        payload = {}

    notification_id = payload.get('notification_id')
    minutes = payload.get('minutes')
    try:
        minutes = int(minutes)
    except Exception:
        minutes = 10
    minutes = max(1, min(minutes, 180))

    if not notification_id:
        return JsonResponse({'ok': False, 'error': 'Missing notification_id.'}, status=400)

    notif = InAppNotification.objects.filter(user=request.user, id=notification_id).first()
    if not notif:
        return JsonResponse({'ok': False, 'error': 'Not found.'}, status=404)

    now = timezone.now()
    snooze_to = now + timedelta(minutes=minutes)

    # Mark the current one as snoozed so it doesn't count as missed.
    notif.snoozed_until = snooze_to
    notif.read_at = now
    notif.save(update_fields=['snoozed_until', 'read_at'])

    new_notif = InAppNotification.objects.create(
        user=request.user,
        report=notif.report,
        notification_type=notif.notification_type,
        title=notif.title,
        body=notif.body,
        scheduled_for=snooze_to,
    )

    return JsonResponse({'ok': True, 'snoozed_to': snooze_to.isoformat(), 'new_id': new_notif.id})

# Doctor Registration Views
from .forms import DoctorForm, AppointmentForm
from .models import Doctor

@login_required(login_url='website:signin')
@never_cache
def doctor_register(request):
    if not (request.user.is_staff or request.user.is_superuser):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Only admins can register doctors.'}, status=403)
        messages.error(request, 'Only admins can register doctors.')
        return redirect('website:doctors_list')

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
@never_cache
def doctors_list(request):
    doctors = Doctor.objects.all().order_by('-created_at')
    my_appointments = []
    if request.user.is_authenticated:
        my_appointments = Appointment.objects.filter(patient_email=request.user.email).order_by('-created_at')
    return render(request, 'website/doctors_list.html', {'doctors': doctors, 'my_appointments': my_appointments})

@login_required(login_url='website:signin')
@never_cache
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
                sender_email, sender_password = _get_smtp_sender_credentials()
                
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
                
                server = _open_smtp_connection()
                try:
                    server.login(sender_email, sender_password)
                    server.send_message(msg_patient)
                    server.send_message(msg_doctor)
                finally:
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
