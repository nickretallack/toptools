import sys, os

# Make sure the application is in the python path
sys.path.insert(0, os.path.dirname(__file__))

# WSGI disables stdout.  Lets work around that.
sys.stdout = sys.stderr

from run import application
