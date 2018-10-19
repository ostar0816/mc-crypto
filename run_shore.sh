gunicorn --log-level=DEBUG --timeout 60 -b 0.0.0.0:5000 shore.wsgi --reload
