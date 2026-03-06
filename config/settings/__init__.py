# config/settings/__init__.py
import os

# Determine which settings file to load based on ENVIRONMENT variable
environment = os.getenv('DJANGO_ENVIRONMENT', 'development')

if environment == 'production':
    from .production import *
else:
    from .development import *
