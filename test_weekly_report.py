import os
import django
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from apps.users.models import UserProfile
from apps.reports.models import DailyReport, WeeklyReport, MainJobOperation
from apps.exporter.services import ExportService

def create_sample_weekly_report():
    """Create a sample weekly report with daily reports and operations"""
    
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='testuser2',
        defaults={
            'email': 'test2@example.com',
            'first_name': 'Test',
            'last_name': 'User2'
        }
    )
    
    # Get or create user profile
    profile, created = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'student_id': '2023001',
            'program': 'MECHANICAL',
            'year_of_study': 3,
            'pt_phase': 'PT1',
            'department': 'Mechanical Engineering',
            'supervisor_name': 'Dr. John Doe',
            'supervisor_email': 'john.doe@university.edu',
            'phone_number': '+1234567890'
        }
    )
    
    # Create a weekly report
    week_start = datetime.now().date() - timedelta(days=datetime.now().weekday())
    week_end = week_start + timedelta(days=4)  # Monday to Friday
    
    weekly_report, created = WeeklyReport.objects.get_or_create(
        student=user,
        week_number=1,
        defaults={
            'start_date': week_start,
            'end_date': week_end,
            'summary': 'This week focused on learning electronics and circuit design fundamentals.',
            'main_job_title': 'Creating an Audio Amplifier Circuit',
            'main_job_description': 'Design and build a functional audio amplifier circuit on PCB',
            'objectives_met': 'Successfully designed and built a working audio amplifier circuit',
            'learning_outcomes': 'Gained practical experience in PCB design, soldering, and circuit troubleshooting',
            'supervisor_comments': 'Excellent progress in understanding circuit design principles',
            'status': 'DRAFT'
        }
    )
    
    # Create daily reports for the week
    daily_activities = [
        {
            'date': week_start,
            'description': 'Learned the basics of soldering, including handling tools, techniques, and safety measures.',
            'hours_spent': 6
        },
        {
            'date': week_start + timedelta(days=1),
            'description': 'Studied how to design an electric circuit using an electric design unit, covering schematics and principles.',
            'hours_spent': 6
        },
        {
            'date': week_start + timedelta(days=2),
            'description': 'Focused on designing a printed circuit board (PCB) for a basic circuit, using CAD tools.',
            'hours_spent': 5
        },
        {
            'date': week_start + timedelta(days=3),
            'description': 'Learned electronics troubleshooting techniques to identify and fix common faults in circuits.',
            'hours_spent': 6
        },
        {
            'date': week_start + timedelta(days=4),
            'description': 'Designed an audio amplifier circuit on a PCB, selecting the required components and tracing the layout.',
            'hours_spent': 5
        }
    ]
    
    for activity in daily_activities:
        DailyReport.objects.get_or_create(
            student=user,
            date=activity['date'],
            week_number=1,
            defaults={
                'description': activity['description'],
                'hours_spent': activity['hours_spent'],
                'skills_learned': 'Electronics, PCB design, Soldering',
                'challenges_faced': 'Understanding complex circuit diagrams',
                'supervisor_feedback': 'Good progress in practical skills'
            }
        )
    
    # Create main job operations
    operations_data = [
        {
            'step_number': 1,
            'operation_name': 'Component Placement',
            'operation_description': 'Components was placed on the PCB following the circuit diagram while ensuring proper orientation',
            'tools_used': 'Capacitors, resistors, audio jack, LM386, speakers',
            'time_spent': 2,
            'safety_measures': 'Wear safety glasses, work in well-ventilated area',
            'outcome': 'All components properly placed on PCB'
        },
        {
            'step_number': 2,
            'operation_name': 'Soldering',
            'operation_description': 'Carefully soldering the components to the PCB, ensuring clean connections and no shorts between adjacent pins or traces',
            'tools_used': 'Soldering gun, blower, soldering wires, jumpers',
            'time_spent': 3,
            'safety_measures': 'Use fume extractor, wear safety glasses',
            'outcome': 'All components securely soldered'
        },
        {
            'step_number': 3,
            'operation_name': 'Power Connection',
            'operation_description': 'Attaching the power supply, audio input jack, and speaker to the respective terminals on the PCB',
            'tools_used': 'Audio jack, Battery, speaker, PCB',
            'time_spent': 1,
            'safety_measures': 'Check polarity, ensure proper connections',
            'outcome': 'Power and audio connections completed'
        },
        {
            'step_number': 4,
            'operation_name': 'Testing and Adjustment',
            'operation_description': 'Powering the circuit for testing, play an audio signal, and test the output. Adjust any settings like volume',
            'tools_used': 'Multimeter, battery, speaker, audio jack, laptop as a source of signals',
            'time_spent': 2,
            'safety_measures': 'Check voltage levels, test with low volume first',
            'outcome': 'Circuit functioning properly with good audio output'
        }
    ]
    
    for op_data in operations_data:
        MainJobOperation.objects.get_or_create(
            weekly_report=weekly_report,
            step_number=op_data['step_number'],
            defaults={
                'operation_name': op_data['operation_name'],
                'operation_description': op_data['operation_description'],
                'tools_used': op_data['tools_used'],
                'time_spent': op_data['time_spent'],
                'safety_measures': op_data['safety_measures'],
                'outcome': op_data['outcome']
            }
        )
    
    print(f"✅ Sample weekly report created successfully!")
    print(f"📊 Week Number: {weekly_report.week_number}")
    print(f"📅 Date Range: {weekly_report.start_date} to {weekly_report.end_date}")
    print(f"👤 Student: {user.get_full_name()}")
    print(f"📝 Daily Reports: {weekly_report.daily_reports.count()}")
    print(f"🔧 Operations: {weekly_report.operations.count()}")
    print(f"⏰ Total Hours: {sum(daily.hours_spent for daily in weekly_report.daily_reports.all())}")
    
    return weekly_report

def test_export():
    """Test the export functionality"""
    weekly_report = create_sample_weekly_report()
    
    print("\n🔄 Testing export functionality...")
    
    try:
        # Test DOCX export
        docx_response = ExportService.export_weekly_report_docx(weekly_report)
        print(f"✅ DOCX Export: {docx_response.status_code}")
        
        # Test HTML export (for PDF)
        html_response = ExportService.export_weekly_report_pdf(weekly_report)
        print(f"✅ HTML Export: {html_response.status_code}")
        
        print("\n📄 Export files generated successfully!")
        print("📋 The weekly report now matches the CoET template format:")
        print("   - College header")
        print("   - Report identification")
        print("   - Daily activities table")
        print("   - Main job operations table")
        print("   - Signature section")
        
    except Exception as e:
        print(f"❌ Export error: {e}")

if __name__ == "__main__":
    test_export() 