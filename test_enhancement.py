#!/usr/bin/env python
"""
Test script to verify AI enhancement feature works end-to-end
"""

import os
import django
import requests
import json

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from apps.reports.models import WeeklyReport, DailyReport, MainJob

def test_enhancement_feature():
    print("🔍 Testing AI Enhancement Feature...")
    
    # 1. Check if API key is available
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key or api_key == 'your-api-key-here':
        print("❌ API key not properly configured")
        return False
    
    print("✅ API key is configured")
    
    # 2. Check if we have test data
    try:
        # Get a user
        user = User.objects.first()
        if not user:
            print("❌ No users found in database")
            return False
        
        print(f"✅ Found user: {user.username}")
        
        # Get a weekly report
        weekly_reports = WeeklyReport.objects.filter(student=user)
        if not weekly_reports.exists():
            print("❌ No weekly reports found for user")
            return False
        
        weekly_report = weekly_reports.first()
        print(f"✅ Found weekly report: {weekly_report.id}")
        
        # 3. Test the enhancement directly
        from apps.reports.views import WeeklyReportViewSet
        
        # Create a mock request
        class MockRequest:
            def __init__(self, user):
                self.user = user
                self.data = {}
        
        mock_request = MockRequest(user)
        
        # Test the enhancement method
        viewset = WeeklyReportViewSet()
        viewset.request = mock_request
        
        # Prepare test data
        test_data = {
            'main_job_title': 'Test Job',
            'daily_reports': [
                {
                    'day': 'Monday',
                    'date': '2025-08-04',
                    'description': 'motor',
                    'hours_worked': 8.0
                }
            ],
            'operations': [],
            'week_number': 1
        }
        
        print("🧪 Testing Claude API call...")
        
        # Test the Claude enhancement
        enhanced_data = viewset._enhance_with_claude(test_data, "Make it more technical")
        
        if enhanced_data:
            print("✅ AI enhancement successful!")
            print(f"📝 Enhanced main job title: {enhanced_data.get('main_job_title', 'N/A')}")
            print(f"📝 Enhanced daily reports: {len(enhanced_data.get('daily_reports', []))}")
            return True
        else:
            print("❌ AI enhancement failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing enhancement: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_enhancement_feature()
    if success:
        print("\n🎉 AI Enhancement feature is working perfectly!")
    else:
        print("\n❌ AI Enhancement feature needs to be fixed!")

