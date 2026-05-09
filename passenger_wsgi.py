# Lightweight WSGI bootstrap used by Passenger.
# Place this file in the application root (project root). PassengerStartupFile
# in `passenger_django.conf` points to this file.

import os
import sys

# Adjust PYTHONPATH to include project root
PROJECT_ROOT = os.path.dirname(__file__)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Ensure the project's virtualenv site-packages are available on sys.path.
# This helps Passenger find installed packages (like Django) if Passenger
# doesn't automatically use the same virtualenv or if packages are only in
# the virtualenv site-packages directory.
VENV_PATH = '/home/dbitsdemo/virtualenv/projects/Python/cartify-backend/3.9'
VENV_SITE_PACKAGES = os.path.join(VENV_PATH, 'lib', 'python3.9', 'site-packages')
if os.path.isdir(VENV_SITE_PACKAGES) and VENV_SITE_PACKAGES not in sys.path:
    sys.path.insert(0, VENV_SITE_PACKAGES)

# Set the Django settings module if not already set by server env
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')

# Activate virtualenv if needed (Passenger should already use PassengerPython)
# If you need to activate the virtualenv manually, uncomment and update the path.
# Example for Python 3.9.23 virtualenv:
# activate_this = '/home/dbitsdemo/virtualenv/projects/Python/cartify-backend/3.9/bin/activate_this.py'
# with open(activate_this) as f:
#     exec(f.read(), dict(__file__=activate_this))

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
