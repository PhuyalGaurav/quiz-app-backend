## Deploying Your Quiz App Backend for Mobile App Integration

This guide will help you deploy your Django REST Framework backend to production for integration with your React Native mobile app.

### 1. Choose a Hosting Provider

Good options for Django hosting include:
- **Heroku**
- **DigitalOcean App Platform**
- **AWS Elastic Beanstalk**
- **Google Cloud Run**
- **Render**

### 2. Production Setup Checklist

1. **Environment Variables**
   - Move all sensitive information to environment variables
   - Create a separate `.env` file for production

2. **Static and Media Files**
   - Configure AWS S3 for media file storage (already done in your app)
   - Set up proper CORS headers for S3 bucket

3. **Database**
   - Set up a production database (PostgreSQL recommended)
   - Update `DATABASE_URL` environment variable

4. **Security Settings**
   ```python
   # Production settings
   DEBUG = False
   ALLOWED_HOSTS = ['your-app-domain.com', 'api.your-app-domain.com']
   SECURE_SSL_REDIRECT = True
   SECURE_HSTS_SECONDS = 31536000  # 1 year
   SECURE_HSTS_INCLUDE_SUBDOMAINS = True
   SECURE_HSTS_PRELOAD = True
   SECURE_CONTENT_TYPE_NOSNIFF = True
   SESSION_COOKIE_SECURE = True
   CSRF_COOKIE_SECURE = True
   ```

5. **CORS Settings for Production**
   ```python
   CORS_ALLOWED_ORIGINS = [
       "https://your-mobile-app-domain.com",
       "app://your-mobile-app",  # For React Native app scheme
   ]
   CORS_ALLOW_CREDENTIALS = True
   ```

6. **Gunicorn and WSGI**
   - Use Gunicorn as WSGI server
   - Create a Procfile for Heroku:
     ```
     web: gunicorn config.wsgi --log-file -
     ```

7. **Requirements**
   - Ensure requirements.txt is up-to-date
   - Add production dependencies like gunicorn:
     ```
     pip freeze > requirements.txt
     ```

### 3. SSL/TLS Configuration

Ensure your app is served over HTTPS:
1. Use a service like Let's Encrypt for SSL certificates
2. Most platforms (Heroku, AWS, etc.) handle this automatically
3. Configure your mobile app to only accept HTTPS connections

### 4. API Documentation in Production

Make Swagger available in production, but with authentication:

```python
schema_view = get_schema_view(
    openapi.Info(
        title="Quiz App API",
        default_version='v1',
        description="API for Quiz App",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.IsAuthenticated], # Change for production
)
```

### 5. Setting Up a Custom Domain

1. Purchase a domain (e.g., from Namecheap, GoDaddy)
2. Configure DNS records to point to your hosting provider
3. Set up SSL certificate for your domain
4. Update ALLOWED_HOSTS and CORS settings with your domain

### 6. Monitoring and Logging

1. Set up Sentry.io for error tracking:
   ```bash
   pip install sentry-sdk
   ```

2. Configure Sentry in settings.py:
   ```python
   import sentry_sdk
   from sentry_sdk.integrations.django import DjangoIntegration

   sentry_sdk.init(
       dsn="https://your-sentry-dsn.ingest.sentry.io/project-id",
       integrations=[DjangoIntegration()],
       traces_sample_rate=0.5,
       send_default_pii=True
   )
   ```

3. Set up logging to track API usage:
   ```python
   LOGGING = {
       'version': 1,
       'disable_existing_loggers': False,
       'formatters': {
           'verbose': {
               'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
               'style': '{',
           },
           'simple': {
               'format': '{levelname} {message}',
               'style': '{',
           },
       },
       'handlers': {
           'console': {
               'level': 'INFO',
               'class': 'logging.StreamHandler',
               'formatter': 'verbose'
           },
           'file': {
               'level': 'INFO',
               'class': 'logging.FileHandler',
               'filename': '/path/to/django/logs/app.log',
               'formatter': 'verbose'
           },
       },
       'loggers': {
           'django': {
               'handlers': ['console', 'file'],
               'level': 'INFO',
               'propagate': True,
           },
           'quiz': {
               'handlers': ['console', 'file'],
               'level': 'INFO',
               'propagate': True,
           },
       },
   }
   ```

### 7. Automating Deployment with CI/CD

Set up CI/CD using GitHub Actions:

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Run tests
      run: |
        python manage.py test
    - name: Deploy to Heroku
      uses: akhileshns/heroku-deploy@v3.12.12
      with:
        heroku_api_key: ${{ secrets.HEROKU_API_KEY }}
        heroku_app_name: "your-app-name"
        heroku_email: ${{ secrets.HEROKU_EMAIL }}
```

### 8. Database Migration in Production

Always back up your database before migrations:

```bash
# For PostgreSQL
pg_dump -U username -h hostname database_name > backup.sql

# Run migrations
python manage.py migrate
```

### 9. API Versioning

Consider adding API versioning for future changes:

```python
REST_FRAMEWORK = {
    # Other settings...
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1'],
}
```

### 10. Performance Optimization

1. Add caching with Redis:
   ```bash
   pip install django-redis
   ```

2. Configure caching in settings.py:
   ```python
   CACHES = {
       'default': {
           'BACKEND': 'django_redis.cache.RedisCache',
           'LOCATION': 'redis://your-redis-url:6379/1',
           'OPTIONS': {
               'CLIENT_CLASS': 'django_redis.client.DefaultClient',
           }
       }
   }
   ```

3. Cache API responses for better performance:
   ```python
   from django.utils.decorators import method_decorator
   from django.views.decorators.cache import cache_page

   @method_decorator(cache_page(60*15), name='dispatch')
   def list(self, request, *args, **kwargs):
       return super().list(request, *args, **kwargs)
   ```

### 11. Testing Before Production

1. Run a full test suite:
   ```bash
   python manage.py test
   ```

2. Test with real mobile app integration
3. Perform load testing to ensure it can handle expected traffic

### 12. Documentation

Make sure your API documentation is accurate and up-to-date.

1. Update Swagger documentation
2. Keep README and other documentation files updated
3. Document deployment process for your team

### 13. Mobile App Integration Testing

1. Test push notifications
2. Test deep linking functionality
3. Test offline functionality
4. Test file uploads and downloads
5. Verify JWT token refresh works correctly

With these steps, your Quiz App backend will be properly configured for production use with your React Native mobile app.
