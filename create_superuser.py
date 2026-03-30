import os
import django

try:
    from dotenv import load_dotenv
    from pathlib import Path

    # Load env vars from a local .env file (useful for local/dev).
    # On Render/production, env vars are provided by the platform.
    _base_dir = Path(__file__).resolve().parent
    load_dotenv(dotenv_path=_base_dir / '.env', override=False)
except Exception:
    pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'docusai_project.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'Superuser "{username}" created successfully!')
else:
    print(f'Superuser "{username}" already exists.')
