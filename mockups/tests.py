import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mockup_project.settings")

import django
django.setup()

from mockups.tasks import generate_mockup_task

generate_mockup_task.delay("task_id_example", "Hello World")