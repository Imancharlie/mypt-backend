#!/usr/bin/env python
"""Test email sending configuration"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

print("=" * 60)
print("📧 EMAIL CONFIGURATION TEST")
print("=" * 60)
print(f"Email Backend: {settings.EMAIL_BACKEND}")
print(f"Email Host: {settings.EMAIL_HOST}")
print(f"Email Port: {settings.EMAIL_PORT}")
print(f"Email Use TLS: {settings.EMAIL_USE_TLS}")
print(f"Email Host User: {settings.EMAIL_HOST_USER}")
print(f"Default From Email: {settings.DEFAULT_FROM_EMAIL}")
print("=" * 60)

try:
    print("\n📤 Sending test email...")
    result = send_mail(
        'Test Email from MIPT Backend',
        'This is a test email to verify email configuration is working correctly.',
        settings.DEFAULT_FROM_EMAIL,
        ['miptsoftware@gmail.com'],
        fail_silently=False,
    )
    print(f"✅ Email sent successfully! (Result: {result})")
except Exception as e:
    print(f"❌ Email sending failed: {e}")
    print(f"Error type: {type(e).__name__}")

print("=" * 60)
