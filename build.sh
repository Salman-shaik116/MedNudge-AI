#!/usr/bin/env bash
set -o errexit

if command -v apt-get >/dev/null 2>&1; then
	if command -v sudo >/dev/null 2>&1; then
		sudo apt-get update
		sudo apt-get install -y tesseract-ocr
	else
		apt-get update
		apt-get install -y tesseract-ocr
	fi
fi

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
python create_superuser.py