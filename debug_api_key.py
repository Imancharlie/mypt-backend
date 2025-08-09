#!/usr/bin/env python
"""
Debug script to check API key loading in Django context
"""

import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def debug_api_key():
    print("🔍 Debugging API Key Loading in Django Context...")
    
    # Check environment variable directly
    api_key = os.getenv('ANTHROPIC_API_KEY')
    print(f"📋 API Key from os.getenv: {'✅ Set' if api_key and api_key != 'your-api-key-here' else '❌ Not set or invalid'}")
    
    if api_key:
        print(f"🔑 API Key length: {len(api_key)} characters")
        print(f"🔑 API Key starts with: {api_key[:10]}...")
    
    # Check Django settings
    from django.conf import settings
    print(f"📋 Django settings module: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
    
    # Check if the anthropic_client is properly initialized
    from apps.reports.views import anthropic_client
    print(f"📋 Anthropic client: {'✅ Initialized' if anthropic_client is not None else '❌ Not initialized'}")
    
    # Test the client directly
    if anthropic_client is not None:
        try:
            response = anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=50,
                messages=[{"role": "user", "content": "Say 'Test'"}]
            )
            print("✅ Anthropic client test successful!")
            print(f"📝 Response: {response.content[0].text}")
        except Exception as e:
            print(f"❌ Anthropic client test failed: {str(e)}")
    else:
        print("❌ Anthropic client is None - API key not loaded properly")
    
    # Check the specific line that's failing
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != 'your-api-key-here':
        print("✅ API key check would pass")
    else:
        print("❌ API key check would fail")

if __name__ == "__main__":
    debug_api_key()
