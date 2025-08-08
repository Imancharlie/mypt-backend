# 🚀 PythonAnywhere Deployment Checklist

## Pre-Deployment (Local)

### ✅ Code Changes
- [ ] AI enhancement feature is working locally
- [ ] API key is configured and tested
- [ ] All tests pass (`python test_enhancement_simple.py`)
- [ ] Code is committed to git
- [ ] Production settings file is created (`config/production_settings.py`)

### ✅ Files to Upload
- [ ] All project files
- [ ] `requirements.txt` (includes `anthropic` package)
- [ ] `config/production_settings.py`
- [ ] `env.production` (template for environment variables)

## PythonAnywhere Setup

### ✅ Account Setup
- [ ] Create PythonAnywhere account
- [ ] Go to 'Web' tab
- [ ] Add new web app
- [ ] Choose 'Manual configuration'
- [ ] Choose Python 3.11

### ✅ Code Upload
- [ ] Upload project files or clone from git
- [ ] Navigate to project directory
- [ ] Verify all files are present

### ✅ Virtual Environment
- [ ] Open Bash console
- [ ] Navigate to project directory
- [ ] Create virtual environment: `python3.11 -m venv venv`
- [ ] Activate virtual environment: `source venv/bin/activate`
- [ ] Install requirements: `pip install -r requirements.txt`

### ✅ Environment Variables
- [ ] Create `.env` file in project directory
- [ ] Copy content from `env.production`
- [ ] Update with your actual values:
  - `DEBUG=False`
  - `SECRET_KEY=your-production-secret-key`
  - `ALLOWED_HOSTS=yourusername.pythonanywhere.com`
  - `ANTHROPIC_API_KEY=your-actual-api-key`

### ✅ WSGI Configuration
- [ ] Go to 'Web' tab
- [ ] Click on your web app
- [ ] Click 'WSGI configuration file'
- [ ] Replace content with production WSGI configuration
- [ ] Update path to your project directory

### ✅ Database Setup
- [ ] Run migrations: `python manage.py migrate`
- [ ] Create superuser (optional): `python manage.py createsuperuser`
- [ ] Test database connection

### ✅ Static Files
- [ ] Run: `python manage.py collectstatic --noinput`
- [ ] Configure static files in 'Web' tab:
  - URL: `/static/`
  - Directory: `/home/yourusername/your-project-directory/staticfiles`
- [ ] Configure media files:
  - URL: `/media/`
  - Directory: `/home/yourusername/your-project-directory/media`

### ✅ Web App Configuration
- [ ] Set source code path
- [ ] Set working directory
- [ ] Configure WSGI file
- [ ] Reload web app

## Testing

### ✅ Basic Functionality
- [ ] Visit your site: `https://yourusername.pythonanywhere.com`
- [ ] Test login functionality
- [ ] Test basic API endpoints
- [ ] Check error logs

### ✅ AI Enhancement Testing
- [ ] Test API key configuration
- [ ] Test Claude API connection
- [ ] Test enhancement feature
- [ ] Verify enhanced data format

### ✅ Production Test
- [ ] Run: `python test_production_deployment.py`
- [ ] Verify all tests pass
- [ ] Check production settings are loaded
- [ ] Test database connection
- [ ] Test static files

## Troubleshooting

### ❌ Common Issues

#### Import Errors
- [ ] Check virtual environment is activated
- [ ] Verify all packages are installed
- [ ] Check Python version (3.11)

#### Module Not Found
- [ ] Check `requirements.txt` installation
- [ ] Verify `anthropic` package is installed
- [ ] Check import paths

#### Database Errors
- [ ] Run migrations: `python manage.py migrate`
- [ ] Check database file permissions
- [ ] Verify database path

#### Static Files Not Loading
- [ ] Run: `python manage.py collectstatic`
- [ ] Check static files configuration
- [ ] Verify file permissions

#### CORS Errors
- [ ] Check `CORS_ALLOWED_ORIGINS` in production settings
- [ ] Verify frontend domain is included
- [ ] Test with different browsers

#### AI Enhancement Not Working
- [ ] Check `ANTHROPIC_API_KEY` is set correctly
- [ ] Test API key with simple test
- [ ] Check error logs for API errors
- [ ] Verify Claude API is accessible

### ✅ Final Verification

#### Local Testing
```bash
# Test API key
python simple_api_test.py

# Test enhancement feature
python test_enhancement_simple.py

# Test production deployment
python test_production_deployment.py
```

#### Production Testing
```bash
# On PythonAnywhere console
source venv/bin/activate
python test_production_deployment.py
```

## Success Indicators

✅ **All tests pass locally**
✅ **All tests pass on PythonAnywhere**
✅ **Website loads without errors**
✅ **Login functionality works**
✅ **AI enhancement feature works**
✅ **No errors in PythonAnywhere logs**

## Post-Deployment

### ✅ Monitoring
- [ ] Check error logs regularly
- [ ] Monitor API usage
- [ ] Test enhancement feature periodically
- [ ] Monitor website performance

### ✅ Maintenance
- [ ] Keep dependencies updated
- [ ] Monitor API key usage
- [ ] Backup database regularly
- [ ] Update environment variables as needed

---

**🎉 If all items are checked, your AI enhancement feature is successfully deployed to production!**

