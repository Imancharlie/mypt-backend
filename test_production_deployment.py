#!/usr/bin/env python
"""
Test script to verify production deployment on PythonAnywhere
"""

import os
import django
import requests
import json

# Set up Django with production settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.production_settings')
django.setup()

def test_production_setup():
    print("🔍 Testing Production Deployment...")
    
    # 1. Check if production settings are loaded
    from django.conf import settings
    print(f"✅ Django settings loaded: config.production_settings")
    print(f"✅ DEBUG mode: {settings.DEBUG}")
    print(f"✅ ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    
    # 2. Check if API key is available
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key or api_key == 'your-api-key-here':
        print("❌ API key not properly configured")
        return False
    
    print("✅ API key is configured")
    
    # 3. Test Claude client
    try:
        import anthropic
        
        client = anthropic.Anthropic(api_key=api_key)
        print("✅ Claude client created successfully")
        
        # Test a simple API call
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": "Say 'Production API is working!'"
                }
            ]
        )
        print("✅ Claude API call successful!")
        print(f"📝 Response: {response.content[0].text}")
        
    except Exception as e:
        print(f"❌ Claude API test failed: {str(e)}")
        return False
    
    # 4. Test database connection
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False
    
    # 5. Test static files configuration
    try:
        static_root = settings.STATIC_ROOT
        if os.path.exists(static_root):
            print(f"✅ Static files directory exists: {static_root}")
        else:
            print(f"⚠️ Static files directory missing: {static_root}")
    except Exception as e:
        print(f"❌ Static files test failed: {str(e)}")
    
    # 6. Test CORS configuration
    cors_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
    print(f"✅ CORS allowed origins: {cors_origins}")
    
    # 7. Test logging configuration
    logging_config = getattr(settings, 'LOGGING', {})
    if logging_config:
        print("✅ Logging configuration is set")
    else:
        print("⚠️ No logging configuration found")
    
    return True

def test_enhancement_feature():
    print("\n🧪 Testing AI Enhancement Feature...")
    
    try:
        from apps.reports.views import WeeklyReportViewSet
        
        # Test the enhancement method directly
        viewset = WeeklyReportViewSet()
        
        # Prepare test data
        test_data = {
            'main_job_title': 'Test Production Job',
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

def main():
    print("🚀 Production Deployment Test")
    print("=" * 60)
    
    # Test production setup
    setup_success = test_production_setup()
    
    if setup_success:
        # Test enhancement feature
        enhancement_success = test_enhancement_feature()
        
        if enhancement_success:
            print("\n🎉 Production deployment is working perfectly!")
            print("✅ All tests passed")
            print("✅ AI enhancement feature is ready for production")
        else:
            print("\n❌ AI enhancement feature needs attention")
    else:
        print("\n❌ Production setup needs attention")

if __name__ == "__main__":
    main()
