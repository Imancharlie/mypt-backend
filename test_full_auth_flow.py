import urllib.request
import urllib.error
import json

# Step 1: Login and get tokens
login_data = {"username": "audit_test_user", "password": "TestPass123!"}
url = "http://localhost:8000/api/auth/login/"
headers = {
    "Content-Type": "application/json",
    "Origin": "http://localhost:3000"
}

req = urllib.request.Request(url, data=json.dumps(login_data).encode('utf-8'), headers=headers, method='POST')

with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode('utf-8'))
    access_token = data.get('access')
    refresh_token = data.get('refresh')

print(f"✅ Logged in, got tokens")

# Step 2: Try to call profile endpoint with access token (should work)
profile_url = "http://localhost:8000/api/auth/profile/"
profile_headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {access_token}",
    "Origin": "http://localhost:3000"
}

profile_req = urllib.request.Request(profile_url, headers=profile_headers, method='GET')

try:
    with urllib.request.urlopen(profile_req) as response:
        print(f"✅ Profile call with valid token: {response.status}")
except urllib.error.HTTPError as e:
    print(f"❌ Profile call failed: {e.code}")
    print(f"   Response: {e.read().decode('utf-8')}")

# Step 3: Try to refresh with refresh token
refresh_url = "http://localhost:8000/api/auth/refresh/"
refresh_data = {"refresh": refresh_token}
refresh_headers = {
    "Content-Type": "application/json",
    "Origin": "http://localhost:3000"
}

refresh_req = urllib.request.Request(refresh_url, data=json.dumps(refresh_data).encode('utf-8'), headers=refresh_headers, method='POST')

try:
    with urllib.request.urlopen(refresh_req) as response:
        refresh_resp = json.loads(response.read().decode('utf-8'))
        new_access = refresh_resp.get('access')
        print(f"✅ Token refresh: {response.status}")
        print(f"   Got new access token: {new_access[:20]}...")
        
        # Step 4: Try profile with NEW token
        new_profile_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {new_access}",
            "Origin": "http://localhost:3000"
        }
        new_profile_req = urllib.request.Request(profile_url, headers=new_profile_headers, method='GET')
        
        try:
            with urllib.request.urlopen(new_profile_req) as response:
                print(f"✅ Profile call with refreshed token: {response.status}")
        except urllib.error.HTTPError as e:
            print(f"❌ Profile call after refresh failed: {e.code}")
            print(f"   Response: {e.read().decode('utf-8')}")
except urllib.error.HTTPError as e:
    print(f"❌ Refresh failed: {e.code}")
    print(f"   Response: {e.read().decode('utf-8')}")
