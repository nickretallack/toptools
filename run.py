#!/usr/bin/env python
from toptools import app as application

def setup_app():
    from toptools.models import setup_database
    setup_database()

if __name__ == '__main__':
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    application.run(debug=True, host='0.0.0.0', port=8080)
