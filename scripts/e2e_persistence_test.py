import os
import sys
import pathlib
import django

# Ensure project root is on PYTHONPATH so `config` module is importable
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from apps.reports.models import DailyReport, WeeklyReport
from datetime import date, timedelta

def run():
    u, created = User.objects.get_or_create(username='audit_test_user', defaults={'email':'audit@example.com'})
    if created:
        u.set_password('TestPass123!')
        u.save()

    # Create five daily reports (Monday-Friday) for week 1
    for i in range(5):
        d = date(2026, 8, 3) + timedelta(days=i)
        obj, c = DailyReport.objects.update_or_create(
            student=u,
            date=d,
            defaults={
                'week_number': 1,
                'description': 'E2E test',
                'hours_spent': 8.0
            }
        )

    # Trigger weekly aggregation
    wr = WeeklyReport.create_from_daily_reports(student=u, week_number=1)
    if wr:
        print('WEEKLY_CREATED', wr.id, wr.week_number, wr.start_date, wr.end_date, float(wr.total_hours))
    else:
        print('WEEKLY_CREATED None')

    print('DAILY_COUNT', DailyReport.objects.filter(student=u, week_number=1).count())

if __name__ == '__main__':
    run()
