#!/usr/bin/env python
"""
Test script to verify the enhancement endpoint works
"""

import os
import django
import requests
import json

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from apps.reports.models import WeeklyReport

def test_enhancement_endpoint():
    print("🔍 Testing Enhancement Endpoint...")
    
    # 1. Get a user and create a test weekly report
    user = User.objects.first()
    if not user:
        print("❌ No users found")
        return False
    
    print(f"✅ Found user: {user.username}")
    
    # 2. Get or create a weekly report
    weekly_report, created = WeeklyReport.objects.get_or_create(
        student=user,
        week_number=1,
        defaults={
            'start_date': '2025-08-04',
            'end_date': '2025-08-08',
            'total_hours': 40.0,
            'is_complete': False
        }
    )
    
    print(f"✅ Weekly report: {weekly_report.id} (week {weekly_report.week_number})")
    
    # 3. Get authentication token
    login_data = {
        'username': 'kilimanjaro',
        'password': 'password'  # Try common password
    }
    
    try:
        login_response = requests.post(
            'http://127.0.0.1:8000/api/auth/login/',
            json=login_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if login_response.status_code == 200:
            token_data = login_response.json()
            access_token = token_data.get('access')
            print("✅ Login successful")
        else:
            print(f"❌ Login failed: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return False
    
    # 4. Test the enhancement endpoint
    enhancement_data = {
        'additional_instructions': 'Make it more technical'
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    
    try:
        enhancement_response = requests.post(
            f'http://127.0.0.1:8000/api/reports/weekly/{weekly_report.week_number}/enhance_with_ai/',
            json=enhancement_data,
            headers=headers
        )
        
        print(f"📊 Enhancement response status: {enhancement_response.status_code}")
        print(f"📊 Enhancement response: {enhancement_response.text}")
        
        if enhancement_response.status_code == 200:
            print("✅ Enhancement endpoint working!")
            return True
        else:
            print("❌ Enhancement endpoint failed")
            return False
            
    except Exception as e:
        print(f"❌ Enhancement error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_enhancement_endpoint()
    if success:
        print("\n🎉 Enhancement endpoint is working!")
    else:
        print("\n❌ Enhancement endpoint needs attention!")
