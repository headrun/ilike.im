#!/home/headrun/packages/bin/python

import sys
sys.path += ['/var/www/']
from fcgi import WSGIServer
from django.core.handlers.wsgi import WSGIHandler
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'ilike.settings'
os.environ['PYTHON_EGG_CACHE'] = '/tmp'
os.environ['PYTHONPATH'] = '/var/www/'
WSGIServer(WSGIHandler()).run()

