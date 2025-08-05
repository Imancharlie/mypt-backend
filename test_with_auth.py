#!/usr/bin/env python
"""
Test script with authentication to verify the endpoint works.
"""

import requests
import json

# Base URL
BASE_URL = "http://localhost:8000/api"

def test_with_authentication():
    """Test the endpoint with authentication."""
    print("🧪 Testing with authentication...")
    
    # First, let's try to login to get a token
    login_data = {
        "username": "testuser",
        "password": "testpass123"
    }
    
    try:
        # Try to login
        login_response = requests.post(
            f"{BASE_URL}/auth/login/",
            json=login_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if login_response.status_code == 200:
            token_data = login_response.json()
            access_token = token_data.get('access')
            
            if access_token:
                print("✅ Login successful, got token")
                
                # Now test the weekly report endpoint with authentication
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {access_token}'
                }
                
                # Test data
                test_data = {
                    "week_number": 2,
                    "start_date": "2025-07-28",
                    "end_date": "2025-08-01",
                    "summary": "Week 2 Report",
                    "main_job_title": "AUDIO AMPLIFIER CIRCUIT",
                    "daily_monday": "Worked on circuit design",
                    "hours_monday": 6.0,
                    "daily_tuesday": "Testing components",
                    "hours_tuesday": 8.0,
                    "daily_wednesday": "Assembly work",
                    "hours_wednesday": 7.0,
                    "daily_thursday": "Quality testing",
                    "hours_thursday": 6.0,
                    "daily_friday": "Documentation",
                    "hours_friday": 5.0
                }
                
                print(f"\n📝 Testing PUT with authentication:")
                print(f"📄 Data: {json.dumps(test_data, indent=2)}")
                
                response = requests.put(
                    f"{BASE_URL}/reports/weekly/week/2/",
                    json=test_data,
                    headers=headers
                )
                
                print(f"✅ Status Code: {response.status_code}")
                
                if response.status_code in [200, 201]:
                    print(f"✅ PUT successful!")
                    print(f"📄 Response: {response.json()}")
                else:
                    print(f"❌ PUT failed with status {response.status_code}")
                    print(f"📄 Error: {response.text}")
                    
            else:
                print("❌ No access token in login response")
                print(f"📄 Login response: {login_response.json()}")
        else:
            print(f"❌ Login failed with status {login_response.status_code}")
            print(f"📄 Login error: {login_response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    try:
        test_with_authentication()
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc() 