from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# تنظیم متغیر محیطی Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mockup_project.settings')

# ایجاد instance اصلی Celery
app = Celery('mockup_project')

# بارگذاری تنظیمات از فایل settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# کشف و ثبت خودکار تمام tasks در اپ‌ها
app.autodiscover_tasks(lambda: ['mockups'])

# برای debug: چاپ هر بار که celery load شد
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')