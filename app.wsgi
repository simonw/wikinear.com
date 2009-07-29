import os, sys

paths = '/home/simon/sites/wikinear.com', '/home/simon/sites/wikinear.com/wikinear'
for path in paths:
    if not path in sys.path:
        sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'wikinear.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

