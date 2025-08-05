# MIPT Backend

A Django REST API backend for Practical Training Management System.

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables (see below)
4. Run migrations: `python manage.py migrate`
5. Start the server: `python manage.py runserver`

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database
DATABASE_URL=sqlite:///db.sqlite3

# AI API Keys
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

## Features

- User authentication and profile management
- Company management
- Daily and weekly report creation
- AI-powered report enhancement
- PDF and DOCX export functionality
- Main job and operations management

## API Endpoints

- `/api/auth/` - Authentication endpoints
- `/api/users/` - User management
- `/api/companies/` - Company management
- `/api/reports/` - Report management
- `/api/reports/weekly/` - Weekly reports
- `/api/reports/daily/` - Daily reports

## AI Enhancement

The system uses Anthropic Claude API for enhancing weekly reports with professional technical descriptions. 