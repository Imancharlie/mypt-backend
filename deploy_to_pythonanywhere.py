#!/usr/bin/env python
"""
Deployment script for PythonAnywhere
This script helps you deploy your Django app to PythonAnywhere
"""

import os
import subprocess
import sys

def print_step(step, description):
    print(f"\n{'='*60}")
    print(f"STEP {step}: {description}")
    print(f"{'='*60}")

def run_command(command, description):
    print(f"\n🔧 {description}")
    print(f"Command: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ Success: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e.stderr}")
        return False

def main():
    print("🚀 PythonAnywhere Deployment Guide")
    print("=" * 60)
    
    print("\n📋 PRE-DEPLOYMENT CHECKLIST:")
    print("1. ✅ AI enhancement feature is working locally")
    print("2. ✅ API key is configured")
    print("3. ✅ All tests pass")
    print("4. ✅ Code is committed to git")
    
    print("\n📝 MANUAL STEPS FOR PYTHONANYWHERE:")
    print("=" * 60)
    
    print_step(1, "SETUP PYTHONANYWHERE ACCOUNT")
    print("""
    1. Go to https://www.pythonanywhere.com/
    2. Create a free account
    3. Go to the 'Web' tab
    4. Click 'Add a new web app'
    5. Choose 'Manual configuration'
    6. Choose Python 3.11
    """)
    
    print_step(2, "UPLOAD YOUR CODE")
    print("""
    1. Go to the 'Files' tab
    2. Navigate to your home directory
    3. Upload your project files or clone from git:
       git clone https://github.com/yourusername/your-repo.git
    """)
    
    print_step(3, "SETUP VIRTUAL ENVIRONMENT")
    print("""
    1. Go to the 'Consoles' tab
    2. Open a Bash console
    3. Navigate to your project directory
    4. Create virtual environment:
       python3.11 -m venv venv
    5. Activate virtual environment:
       source venv/bin/activate
    6. Install requirements:
       pip install -r requirements.txt
    """)
    
    print_step(4, "CONFIGURE ENVIRONMENT VARIABLES")
    print("""
    1. In your project directory, create .env file:
       nano .env
    2. Add the production environment variables (see env.production)
    3. Make sure to set:
       - DEBUG=False
       - Your actual PythonAnywhere domain in ALLOWED_HOSTS
       - Your production SECRET_KEY
       - Your ANTHROPIC_API_KEY
    """)
    
    print_step(5, "CONFIGURE WSGI FILE")
    print("""
    1. Go to the 'Web' tab
    2. Click on your web app
    3. Click 'WSGI configuration file'
    4. Replace the content with:
    """)
    
    wsgi_content = '''import os
import sys

# Add your project directory to the sys.path
path = '/home/yourusername/your-project-directory'
if path not in sys.path:
    sys.path.append(path)

# Set the Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.production_settings'

# Import Django's WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
'''
    print(wsgi_content)
    
    print_step(6, "RUN MIGRATIONS")
    print("""
    1. Go to the 'Consoles' tab
    2. Open a Bash console
    3. Navigate to your project directory
    4. Activate virtual environment:
       source venv/bin/activate
    5. Run migrations:
       python manage.py migrate
    6. Create superuser (optional):
       python manage.py createsuperuser
    """)
    
    print_step(7, "COLLECT STATIC FILES")
    print("""
    1. In the same console:
       python manage.py collectstatic --noinput
    """)
    
    print_step(8, "CONFIGURE WEB APP")
    print("""
    1. Go to the 'Web' tab
    2. Click on your web app
    3. Set the following:
       - Source code: /home/yourusername/your-project-directory
       - Working directory: /home/yourusername/your-project-directory
       - WSGI configuration file: (use the one from step 5)
    """)
    
    print_step(9, "SETUP STATIC FILES")
    print("""
    1. In the 'Web' tab, go to 'Static files'
    2. Add:
       URL: /static/
       Directory: /home/yourusername/your-project-directory/staticfiles
    3. Add:
       URL: /media/
       Directory: /home/yourusername/your-project-directory/media
    """)
    
    print_step(10, "RELOAD WEB APP")
    print("""
    1. Go to the 'Web' tab
    2. Click 'Reload yourusername.pythonanywhere.com'
    3. Wait for the reload to complete
    """)
    
    print_step(11, "TEST THE DEPLOYMENT")
    print("""
    1. Visit your site: https://yourusername.pythonanywhere.com
    2. Test the login functionality
    3. Test the AI enhancement feature
    4. Check the error logs if needed
    """)
    
    print("\n🔧 TROUBLESHOOTING:")
    print("=" * 60)
    print("""
    If you encounter issues:
    
    1. Check error logs:
       - Go to 'Web' tab → 'Log files' → 'Error log'
    
    2. Common issues:
       - Import errors: Check virtual environment activation
       - Module not found: Check requirements.txt installation
       - Database errors: Run migrations
       - Static files not loading: Check static files configuration
       - CORS errors: Check CORS_ALLOWED_ORIGINS in production_settings.py
    
    3. Test AI enhancement:
       - Check if ANTHROPIC_API_KEY is set correctly
       - Test with the simple_api_test.py script
    """)
    
    print("\n✅ DEPLOYMENT COMPLETE!")
    print("Your AI enhancement feature should now be working on PythonAnywhere!")

if __name__ == "__main__":
    main()

