mkdir -p logs
python manage.py collectstatic --noinput
gunicorn --workers 17 --timeout 4000 serviu.wsgi --log-file logs/gunicorn.log