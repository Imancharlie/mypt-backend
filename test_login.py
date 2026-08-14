import urllib.request
import urllib.error
import json

# Test login
login_data = {
    "username": "audit_test_user",
    "password": "TestPass123!"
}

url = "http://localhost:8000/api/auth/login/"
headers = {
    "Content-Type": "application/json",
    "Origin": "http://localhost:3000"
}

req = urllib.request.Request(
    url,
    data=json.dumps(login_data).encode('utf-8'),
    headers=headers,
    method='POST'
)

try:
    with urllib.request.urlopen(req) as response:
        print("Status Code:", response.status)
        data = json.loads(response.read().decode('utf-8'))
        print("Response:", json.dumps(data, indent=2))
        
        # Extract tokens
        access_token = data.get('access')
        refresh_token = data.get('refresh')
        print("\nTokens extracted:")
        print(f"Access: {access_token[:20] if access_token else 'None'}...")
        print(f"Refresh: {refresh_token[:20] if refresh_token else 'None'}...")
        
        # Test token refresh
        if refresh_token:
            refresh_data = {"refresh": refresh_token}
            refresh_url = "http://localhost:8000/api/auth/refresh/"
            refresh_req = urllib.request.Request(
                refresh_url,
                data=json.dumps(refresh_data).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            
            try:
                with urllib.request.urlopen(refresh_req) as refresh_response:
                    print(f"\nRefresh test status: {refresh_response.status}")
                    refresh_data_resp = json.loads(refresh_response.read().decode('utf-8'))
                    print(f"Refresh response: {json.dumps(refresh_data_resp, indent=2)}")
            except urllib.error.HTTPError as e:
                print(f"Refresh failed: {e.code}")
                print(f"Response: {e.read().decode('utf-8')}")
except urllib.error.HTTPError as e:
    print(f"Login failed: {e.code}")
    print(f"Response: {e.read().decode('utf-8')}")
