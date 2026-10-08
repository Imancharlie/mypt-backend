from django.db import migrations, models


def mark_enhanced_weekly_reports(apps, schema_editor):
    """Backfill is_ai_enhanced for reports whose AI chat session completed.

    The flag was removed from WeeklyReport before this migration existed, so
    reports enhanced before now have no record of it on the report itself.
    """
    WeeklyReport = apps.get_model('reports', 'WeeklyReport')
    AiChatSession = apps.get_model('reports', 'AiChatSession')

    completed = AiChatSession.objects.filter(status='complete').values_list(
        'student_id', 'week_number'
    )
    for student_id, week_number in completed:
        WeeklyReport.objects.filter(
            student_id=student_id, week_number=week_number
        ).update(is_ai_enhanced=True)


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0006_ai_chat_sessions_and_messages'),
    ]

    operations = [
        migrations.AddField(
            model_name='weeklyreport',
            name='is_ai_enhanced',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
        migrations.RunPython(
            mark_enhanced_weekly_reports,
            migrations.RunPython.noop,
        ),
    ]
