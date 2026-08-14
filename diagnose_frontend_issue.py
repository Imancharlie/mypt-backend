#!/usr/bin/env python
"""
Comprehensive diagnostic script to test the exact flow that's failing on the frontend
"""
import os
import sys
import json
import requests
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status

# Configuration
BASE_URL = 'http://localhost:8000/api'
TEST_USERNAME = 'audit_test_user'
TEST_PASSWORD = 'TestPass123!'

print("=" * 80)
print("🔍 FRONTEND ISSUE DIAGNOSTIC TEST")
print("=" * 80)
print(f"Timestamp: {datetime.now()}")
print(f"Base URL: {BASE_URL}")
print(f"Test User: {TEST_USERNAME}")
print()

# =============================================================================
# TEST 1: Direct Backend Test (Django Test Client)
# =============================================================================
print("\n" + "=" * 80)
print("TEST 1: Direct Backend Tests (Django ORM + Test Client)")
print("=" * 80)

from rest_framework.test import APIClient
client = APIClient()

# Test 1a: Health check
print("\n[1a] Testing health endpoint...")
try:
    response = client.get(f'{BASE_URL}/auth/health/')
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.data}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("  ✓ Health check passed")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Test 1b: Login with test user
print("\n[1b] Testing login endpoint...")
print(f"  Credentials: username={TEST_USERNAME}, password={TEST_PASSWORD}")
login_data = {
    'username': TEST_USERNAME,
    'password': TEST_PASSWORD
}
try:
    response = client.post(f'{BASE_URL}/auth/login/', login_data, format='json')
    print(f"  Status: {response.status_code}")
    print(f"  Response keys: {list(response.data.keys()) if hasattr(response, 'data') else 'N/A'}")
    
    if response.status_code == 200:
        print(f"  ✓ Login successful!")
        tokens = response.data
        access_token = tokens.get('access')
        refresh_token = tokens.get('refresh')
        user_data = tokens.get('user')
        
        print(f"  - Access token: {access_token[:20]}..." if access_token else "  - Access token: MISSING")
        print(f"  - Refresh token: {refresh_token[:20]}..." if refresh_token else "  - Refresh token: MISSING")
        print(f"  - User data: {user_data}")
        
        # Test 1c: Profile with access token
        print("\n[1c] Testing profile endpoint with access token...")
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = client.get(f'{BASE_URL}/auth/profile/')
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print(f"  ✓ Profile fetch successful!")
            print(f"  Response: {json.dumps(response.data, indent=2)[:200]}...")
        else:
            print(f"  ✗ Profile fetch failed: {response.status_code}")
            print(f"  Response: {response.data}")
        
        # Test 1d: Token refresh
        print("\n[1d] Testing token refresh...")
        client.credentials()  # Clear credentials
        refresh_data = {'refresh': refresh_token}
        response = client.post(f'{BASE_URL}/auth/refresh/', refresh_data, format='json')
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print(f"  ✓ Token refresh successful!")
            new_access = response.data.get('access')
            print(f"  - New access token: {new_access[:20]}..." if new_access else "  - New access token: MISSING")
        else:
            print(f"  ✗ Token refresh failed: {response.status_code}")
            print(f"  Response: {response.data}")
    else:
        print(f"  ✗ Login failed with status {response.status_code}")
        print(f"  Response: {response.data}")
        
except Exception as e:
    print(f"  ✗ Error during login test: {e}")
    import traceback
    traceback.print_exc()

# =============================================================================
# TEST 2: Raw HTTP Requests (Simulating Frontend Axios Calls)
# =============================================================================
print("\n" + "=" * 80)
print("TEST 2: Raw HTTP Requests (Simulating Frontend)")
print("=" * 80)

session = requests.Session()
session.headers.update({
    'Content-Type': 'application/json',
    'X-Request-Nonce': 'test-nonce-12345'
})

# Test 2a: Health check with raw HTTP
print("\n[2a] Testing health endpoint (raw HTTP)...")
try:
    response = session.get(f'{BASE_URL}/auth/health/')
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")
    assert response.status_code == 200
    print("  ✓ Health check passed")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Test 2b: Login with raw HTTP (exactly like frontend)
print("\n[2b] Testing login endpoint (raw HTTP - exactly like frontend)...")
login_data = {
    'username': TEST_USERNAME,
    'password': TEST_PASSWORD
}
print(f"  Request headers: {dict(session.headers)}")
print(f"  Request body: {json.dumps(login_data)}")

try:
    response = session.post(f'{BASE_URL}/auth/login/', json=login_data)
    print(f"  Status: {response.status_code}")
    print(f"  Response headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        print(f"  ✓ Login successful!")
        tokens = response.json()
        access_token = tokens.get('access')
        refresh_token = tokens.get('refresh')
        user_data = tokens.get('user')
        
        print(f"  - Access token: {access_token[:20]}..." if access_token else "  - Access token: MISSING")
        print(f"  - Refresh token: {refresh_token[:20]}..." if refresh_token else "  - Refresh token: MISSING")
        print(f"  - User data: {user_data}")
        
        # Test 2c: Profile fetch with access token
        print("\n[2c] Testing profile endpoint with access token (raw HTTP)...")
        profile_headers = session.headers.copy()
        profile_headers['Authorization'] = f'Bearer {access_token}'
        print(f"  Request headers: Authorization={profile_headers.get('Authorization', 'MISSING')}")
        
        response = session.get(f'{BASE_URL}/auth/profile/', headers=profile_headers)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"  ✓ Profile fetch successful!")
            profile_data = response.json()
            print(f"  Response keys: {list(profile_data.keys())}")
        else:
            print(f"  ✗ Profile fetch failed: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            print(f"  Response headers: {dict(response.headers)}")
        
        # Test 2d: Token refresh
        print("\n[2d] Testing token refresh (raw HTTP)...")
        refresh_data = {'refresh': refresh_token}
        print(f"  Request body: {json.dumps(refresh_data)}")
        
        response = session.post(f'{BASE_URL}/auth/refresh/', json=refresh_data)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"  ✓ Token refresh successful!")
            new_tokens = response.json()
            new_access = new_tokens.get('access')
            print(f"  - New access token: {new_access[:20]}..." if new_access else "  - New access token: MISSING")
        else:
            print(f"  ✗ Token refresh failed: {response.status_code}")
            print(f"  Response: {response.text}")
            
    else:
        print(f"  ✗ Login failed with status {response.status_code}")
        print(f"  Response: {response.text}")
        
except Exception as e:
    print(f"  ✗ Error during raw HTTP test: {e}")
    import traceback
    traceback.print_exc()

# =============================================================================
# TEST 3: CORS Preflight Test
# =============================================================================
print("\n" + "=" * 80)
print("TEST 3: CORS Preflight Test")
print("=" * 80)

print("\n[3a] Testing OPTIONS preflight for login endpoint...")
try:
    headers = {
        'Origin': 'http://localhost:3000',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'content-type, x-request-nonce'
    }
    response = requests.options(f'{BASE_URL}/auth/login/', headers=headers)
    print(f"  Status: {response.status_code}")
    print(f"  CORS Headers:")
    for key in response.headers:
        if 'Access-Control' in key or 'allow' in key.lower():
            print(f"    {key}: {response.headers[key]}")
    
    if response.status_code == 200:
        print("  ✓ CORS preflight passed")
    else:
        print("  ✗ CORS preflight failed")
except Exception as e:
    print(f"  ✗ Error: {e}")

# =============================================================================
# TEST 4: Check settings
# =============================================================================
print("\n" + "=" * 80)
print("TEST 4: Backend Settings Check")
print("=" * 80)

from django.conf import settings

print(f"\nCORS_ALLOWED_ORIGINS: {settings.CORS_ALLOWED_ORIGINS}")
print(f"CORS_ALLOW_CREDENTIALS: {settings.CORS_ALLOW_CREDENTIALS}")
print(f"CORS_ALLOW_HEADERS: {settings.CORS_ALLOW_HEADERS[:3]}..." if len(settings.CORS_ALLOW_HEADERS) > 3 else f"CORS_ALLOW_HEADERS: {settings.CORS_ALLOW_HEADERS}")
print(f"SIMPLE_JWT ACCESS_TOKEN_LIFETIME: {settings.SIMPLE_JWT.get('ACCESS_TOKEN_LIFETIME')}")
print(f"SIMPLE_JWT REFRESH_TOKEN_LIFETIME: {settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME')}")

print("\n" + "=" * 80)
print("✓ DIAGNOSTIC TEST COMPLETE")
print("=" * 80)
