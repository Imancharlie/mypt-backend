#!/usr/bin/env python
"""
Direct test of enhancement functionality without authentication
"""

import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from apps.reports.models import WeeklyReport
from apps.reports.views import WeeklyReportViewSet

def test_direct_enhancement():
    print("🔍 Testing Direct Enhancement...")
    
    # 1. Get a user
    user = User.objects.first()
    if not user:
        print("❌ No users found")
        return False
    
    print(f"✅ Found user: {user.username}")
    
    # 2. Get a weekly report
    weekly_report = WeeklyReport.objects.filter(student=user).first()
    if not weekly_report:
        print("❌ No weekly reports found")
        return False
    
    print(f"✅ Found weekly report: {weekly_report.id} (week {weekly_report.week_number})")
    
    # 3. Test the enhancement directly
    viewset = WeeklyReportViewSet()
    
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
        'week_number': weekly_report.week_number
    }
    
    print("🧪 Testing Claude API call directly...")
    
    # Test the Claude enhancement
    enhanced_data = viewset._enhance_with_claude(test_data, "Make it more technical")
    
    if enhanced_data:
        print("✅ AI enhancement successful!")
        print(f"📝 Enhanced main job title: {enhanced_data.get('main_job_title', 'N/A')}")
        print(f"📝 Enhanced daily reports: {len(enhanced_data.get('daily_reports', []))}")
        print(f"📝 Enhanced operations: {len(enhanced_data.get('operations', []))}")
        return True
    else:
        print("❌ AI enhancement failed")
        return False

if __name__ == "__main__":
    success = test_direct_enhancement()
    if success:
        print("\n🎉 Direct enhancement is working!")
    else:
        print("\n❌ Direct enhancement needs attention!")

