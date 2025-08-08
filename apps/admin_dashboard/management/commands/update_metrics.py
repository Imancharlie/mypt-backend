from django.core.management.base import BaseCommand
from apps.admin_dashboard.services import SystemMetricsService, TokenTrackingService
from django.utils import timezone


class Command(BaseCommand):
    help = 'Update system metrics for admin dashboard'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if metrics already exist for today',
        )
    
    def handle(self, *args, **options):
        self.stdout.write('Updating system metrics...')
        
        try:
            # Update daily metrics
            metrics = SystemMetricsService.update_daily_metrics()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully updated metrics for {metrics.date}: '
                    f'{metrics.total_users} users, '
                    f'{metrics.total_reports} reports, '
                    f'{metrics.total_tokens_used} tokens used'
                )
            )
            
            # Get system token stats
            token_stats = TokenTrackingService.get_system_token_stats()
            
            self.stdout.write(
                f'Token Usage Summary: '
                f'Total tokens: {token_stats["total_tokens"]}, '
                f'Total cost: ${token_stats["total_cost"]:.4f}'
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error updating metrics: {str(e)}')
            ) 