import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import hashlib
import time

def test_email():
    try:
        # Test email configuration
        sender_email = "geethageetha7817@gmail.com"
        sender_password = "egkw lkki fzxp giir"
        recipient_email = "potscorpbloggers@gmail.com"  # Replace with actual test email
        recipient_name = "Test User"
        recipient_username = "testuser"
        
        # Generate unique progress link
        timestamp = str(int(time.time()))
        unique_id = hashlib.md5(f"{recipient_email}{timestamp}".encode()).hexdigest()[:8]
        progress_url = f"http://localhost:8000/progress/{unique_id}/?name={recipient_name}&email={recipient_email}"
        
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
                <p style="font-size: 16px; margin-bottom: 25px;">Click below to access your personalized weekly health tracker:</p>
                <a href="{progress_url}" class="tracker-btn">
                    🚀 Start Your Health Journey
                </a>
                <p style="font-size: 14px; color: #6b7280; margin-top: 15px;">
                    <strong>Unique Tracker ID:</strong> HT-{unique_id.upper()}<br>
                    This link is personalized for you!
                </p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        # Test SMTP connection
        print("Testing SMTP connection...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        print("SMTP connection successful!")
        
        # Send test email (uncomment to actually send)
        # server.send_message(msg)
        # print(f"Test email sent to {recipient_email}")
        
        server.quit()
        
        print(f"Email would be sent to: {recipient_email}")
        print(f"Progress URL: {progress_url}")
        print(f"Tracker ID: HT-{unique_id.upper()}")
        
        return True
        
    except Exception as e:
        print(f"Email test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_email()