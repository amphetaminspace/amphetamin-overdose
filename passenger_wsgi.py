#!/usr/bin/env python3
"""
Passenger WSGI Entry Point for amphetamin_Overdose.
This file is automatically detected by Phusion Passenger.

Place this file in your application's root directory (the same directory as your app).
Passenger will use the 'application' object defined here.

For Passenger configuration, create a passenger.config.json or use .htaccess:
    PassengerPython /path/to/python
    PassengerAppRoot /path/to/amphetamin-overdose
    PassengerAppType wsgi
    PassengerStartupFile passenger_wsgi.py
"""
import os
import sys

# Add the app directory to Python path
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_ROOT)

# Set environment variables for Passenger deployment
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('PAPER_TRADING', 'true')

# Import the Flask application from the web dashboard module
from web.dashboard import application  # noqa: E402

# The 'application' variable is what Passenger uses as the WSGI entry point
# It is already defined in web/dashboard.py as 'application = app'
