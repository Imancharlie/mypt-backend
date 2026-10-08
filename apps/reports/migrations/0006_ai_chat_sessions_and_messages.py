from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('reports', '0005_alter_originaluserinputs_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='AiChatSession',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('week_number', models.IntegerField()),
                ('session_id', models.CharField(blank=True, default='', help_text='Session id on the AI service', max_length=64)),
                ('status', models.CharField(choices=[('in_progress', 'In progress'), ('complete', 'Enhanced')], default='in_progress', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ai_chat_sessions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'ai_chat_sessions',
                'ordering': ['-updated_at'],
                'unique_together': {('student', 'week_number')},
            },
        ),
        migrations.CreateModel(
            name='AiChatMessage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('user', 'User'), ('assistant', 'Assistant')], max_length=10)),
                ('content', models.TextField()),
                ('message_type', models.CharField(default='text', help_text='text | question | ready | complete | error', max_length=20)),
                ('is_pending', models.BooleanField(default=False, help_text='Assistant message still waiting for a reply')),
                ('meta', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='reports.aichatsession')),
            ],
            options={
                'db_table': 'ai_chat_messages',
                'ordering': ['created_at'],
            },
        ),
    ]
