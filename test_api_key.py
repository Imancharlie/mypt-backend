#!/usr/bin/env python
"""
Test script to verify API key configuration and Claude client setup
"""

import os
import anthropic

def test_api_key():
    print("🔍 Testing API Key Configuration...")
    
    # Check environment variable
    api_key = os.getenv('ANTHROPIC_API_KEY')
    print(f"📋 API Key from env: {'✅ Set' if api_key and api_key != 'your-api-key-here' else '❌ Not set or invalid'}")
    
    if api_key and api_key != 'your-api-key-here':
        print(f"🔑 API Key length: {len(api_key)} characters")
        print(f"🔑 API Key starts with: {api_key[:10]}...")
        
        # Test Claude client creation
        try:
            client = anthropic.Anthropic(api_key=api_key)
            print("✅ Claude client created successfully")
            
            # Test a simple API call
            try:
                response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=100,
                    messages=[
                        {
                            "role": "user",
                            "content": "Say 'Hello, API is working!'"
                        }
                    ]
                )
                print("✅ Claude API call successful!")
                print(f"📝 Response: {response.content[0].text}")
                return True
            except Exception as e:
                print(f"❌ Claude API call failed: {str(e)}")
                return False
                
        except Exception as e:
            print(f"❌ Claude client creation failed: {str(e)}")
            return False
    else:
        print("❌ No valid API key found")
        return False

if __name__ == "__main__":
    import django
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    
    success = test_api_key()
    if success:
        print("\n🎉 API Key is properly configured and working!")
    else:
        print("\n❌ API Key configuration needs to be fixed!")
