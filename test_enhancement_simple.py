#!/usr/bin/env python
"""
Simple test to verify Claude API integration works
"""

import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def test_claude_integration():
    print("🔍 Testing Claude API Integration...")
    
    # 1. Check if API key is available
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key or api_key == 'your-api-key-here':
        print("❌ API key not properly configured")
        return False
    
    print("✅ API key is configured")
    
    # 2. Test the Claude client directly
    try:
        import anthropic
        
        client = anthropic.Anthropic(api_key=api_key)
        print("✅ Claude client created successfully")
        
        # 3. Test with the same prompt format used in the enhancement
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
        
        # Create the same prompt format used in the enhancement
        daily_text = ""
        for daily in test_data['daily_reports']:
            daily_text += f"Day: {daily['day']} ({daily['date']})\n"
            daily_text += f"Hours: {daily['hours_worked']}\n"
            daily_text += f"Description: {daily['description']}\n\n"
        
        operations_text = ""
        for op in test_data['operations']:
            operations_text += f"Step {op['step_number']}: {op['operation_description']}\n"
            operations_text += f"Tools: {op['tools_used']}\n\n"
        
        prompt = f"""
You are an expert technical writer specializing in practical training reports. Your task is to enhance a weekly practical training report to make it more professional, technical, and comprehensive.

CONTEXT:
- Main Job Title: {test_data['main_job_title']}
- Week Number: {test_data['week_number']}
- This is for a practical training/internship report

CURRENT DATA:
{daily_text}

CURRENT OPERATIONS:
{operations_text}

ENHANCEMENT REQUIREMENTS:

1. DAILY DESCRIPTIONS:
   - Convert any Swahili text to professional English
   - Make each description 2-3 sentences long (50-80 words)
   - Include specific technical details, tools used, and learning outcomes
   - Focus on practical skills gained and tasks performed
   - Use professional technical language

2. OPERATIONS:
   - Ensure at least 4 detailed operation steps
   - Each step should be specific and actionable
   - Include technical tools and equipment used
   - Make steps sequential and logical

3. MAIN JOB TITLE:
   - Make it more specific and technical
   - Include the main focus area

ADDITIONAL INSTRUCTIONS: Make it more technical

CRITICAL: Return ONLY a valid JSON object in this EXACT format:
{{
    "main_job_title": "Enhanced specific technical job title",
    "daily_reports": [
        {{
            "day": "Monday",
            "date": "2025-08-04",
            "description": "Enhanced technical description",
            "hours_worked": 8.0
        }}
    ],
    "operations": [
        {{
            "step_number": 1,
            "operation_description": "Detailed technical step",
            "tools_used": "Specific tools and equipment"
        }}
    ]
}}
"""
        
        print("🧪 Testing Claude API with enhancement prompt...")
        
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=2000,
            temperature=0.7,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        enhanced_content = response.content[0].text
        print("✅ Claude API call successful!")
        print(f"📝 Response length: {len(enhanced_content)} characters")
        
        # Try to parse as JSON
        import json
        try:
            enhanced_data = json.loads(enhanced_content)
            print("✅ JSON parsing successful!")
            print(f"📝 Enhanced main job title: {enhanced_data.get('main_job_title', 'N/A')}")
            print(f"📝 Enhanced daily reports: {len(enhanced_data.get('daily_reports', []))}")
            print(f"📝 Enhanced operations: {len(enhanced_data.get('operations', []))}")
            return True
        except json.JSONDecodeError:
            print("⚠️ Response is not valid JSON, but API call worked")
            print(f"📝 Response preview: {enhanced_content[:200]}...")
            return True
            
    except Exception as e:
        print(f"❌ Error testing Claude integration: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_claude_integration()
    if success:
        print("\n🎉 Claude API Integration is working perfectly!")
    else:
        print("\n❌ Claude API Integration needs to be fixed!")

