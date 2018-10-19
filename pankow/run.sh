python manage.py pankow & service rabbitmq-server start & C_FORCE_ROOT=1 celery -A pankow.exch_tasks worker --loglevel=info
