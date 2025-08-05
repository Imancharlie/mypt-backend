#!/usr/bin/env python3
"""
Setup script for Industrial Practical Training Report Generator
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False


def create_env_file():
    """Create .env file from template"""
    if not os.path.exists('.env'):
        print("\nCreating .env file from template...")
        try:
            with open('env.example', 'r') as template:
                content = template.read()
            
            with open('.env', 'w') as env_file:
                env_file.write(content)
            
            print("✓ .env file created successfully")
            print("⚠️  Please edit .env file with your configuration")
            return True
        except FileNotFoundError:
            print("✗ env.example file not found")
            return False
    else:
        print("✓ .env file already exists")
        return True


def main():
    """Main setup function"""
    print("🚀 Setting up Industrial Practical Training Report Generator")
    print("=" * 60)
    
    # Check Python version
    if sys.version_info < (3, 11):
        print("✗ Python 3.11+ is required")
        sys.exit(1)
    
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Create virtual environment
    if not os.path.exists('venv'):
        if not run_command('python -m venv venv', 'Creating virtual environment'):
            sys.exit(1)
    else:
        print("✓ Virtual environment already exists")
    
    # Activate virtual environment and install dependencies
    if os.name == 'nt':  # Windows
        activate_cmd = 'venv\\Scripts\\activate'
        pip_cmd = 'venv\\Scripts\\pip'
    else:  # Unix/Linux/MacOS
        activate_cmd = 'source venv/bin/activate'
        pip_cmd = 'venv/bin/pip'
    
    # Install requirements
    if not run_command(f'{pip_cmd} install -r requirements.txt', 'Installing dependencies'):
        sys.exit(1)
    
    # Create .env file
    if not create_env_file():
        sys.exit(1)
    
    # Create necessary directories
    directories = ['logs', 'static', 'media', 'templates/exports']
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")
    
    print("\n" + "=" * 60)
    print("🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Edit .env file with your configuration")
    print("2. Set up PostgreSQL database")
    print("3. Run: python manage.py makemigrations")
    print("4. Run: python manage.py migrate")
    print("5. Run: python manage.py createsuperuser")
    print("6. Run: python manage.py runserver")
    print("\nFor detailed instructions, see README.md")


if __name__ == '__main__':
    main() 