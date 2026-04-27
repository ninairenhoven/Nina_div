#!/bin/bash
cd /var/www/eventor
exec venv/bin/gunicorn app:app --bind 127.0.0.1:5001 --workers 2
