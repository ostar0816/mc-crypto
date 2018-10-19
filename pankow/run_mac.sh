python manage.py pankow & /usr/local/sbin/rabbitmq-server & C_FORCE_ROOT=1 celery -A pankow.exch_tasks worker --loglevel=info
