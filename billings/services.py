from decimal import Decimal
from django.contrib.auth.models import User
from .models import UserBalance, Transaction
from apps.reports.models import WeeklyReport, DailyReport


class BillingService:
    """Service class for billing operations."""
    
    @staticmethod
    def get_user_balance(user):
        """Get or create user balance."""
        balance, created = UserBalance.objects.get_or_create(user=user)
        return balance
    
    @staticmethod
    def can_use_ai_enhancement(user):
        """Check if user can use AI enhancement."""
        balance = BillingService.get_user_balance(user)
        return balance.can_use_ai_enhancement()
    
    @staticmethod
    def calculate_usage_cost(weekly_report):
        """Calculate token cost based on weekly report completion."""
        daily_reports = weekly_report.get_daily_reports()
        filled_days = daily_reports.count()
        
        if filled_days == 5:
            return 300  # FULLFILLED
        elif filled_days >= 3:
            return 400  # PARTIAL
        else:
            return 500  # EMPTY
    
    @staticmethod
    def deduct_tokens_for_ai_enhancement(user, weekly_report):
        """Deduct tokens for AI enhancement based on report completion."""
        balance = BillingService.get_user_balance(user)
        token_cost = BillingService.calculate_usage_cost(weekly_report)
        
        if balance.deduct_tokens(token_cost):
            return {
                'success': True,
                'tokens_deducted': token_cost,
                'remaining_tokens': balance.available_tokens,
                'usage_type': 'FULLFILLED' if token_cost == 300 else 'PARTIAL' if token_cost == 400 else 'EMPTY'
            }
        else:
            return {
                'success': False,
                'message': 'Insufficient tokens',
                'available_tokens': balance.available_tokens,
                'required_tokens': token_cost
            }
    
    @staticmethod
    def process_payment(user, amount, payment_method='DIRECT', **kwargs):
        """Process a new payment transaction."""
        transaction = Transaction.objects.create(
            user=user,
            amount=amount,
            payment_method=payment_method,
            **kwargs
        )
        return transaction
    
    @staticmethod
    def approve_transaction(transaction_id, confirmed_by):
        """Approve a transaction and update user balance."""
        try:
            transaction = Transaction.objects.get(id=transaction_id)
            if transaction.approve_transaction(confirmed_by):
                return {
                    'success': True,
                    'message': 'Transaction approved successfully',
                    'tokens_generated': transaction.tokens_generated
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to approve transaction'
                }
        except Transaction.DoesNotExist:
            return {
                'success': False,
                'message': 'Transaction not found'
            }
    
    @staticmethod
    def get_payment_summary(user):
        """Get payment summary for a user."""
        balance = BillingService.get_user_balance(user)
        transactions = Transaction.objects.filter(user=user).order_by('-created_at')
        
        total_spent = sum(t.amount for t in transactions if t.transaction_status == 'APPROVED')
        pending_transactions = transactions.filter(transaction_status='PENDING').count()
        
        return {
            'balance': balance,
            'total_spent': total_spent,
            'pending_transactions': pending_transactions,
            'recent_transactions': transactions[:5]
        }


class TokenUsageTracker:
    """Track token usage for AI enhancements."""
    
    @staticmethod
    def track_weekly_report_enhancement(user, weekly_report):
        """Track token usage for weekly report AI enhancement."""
        return BillingService.deduct_tokens_for_ai_enhancement(user, weekly_report)
    
    @staticmethod
    def get_usage_statistics(user):
        """Get token usage statistics for a user."""
        balance = BillingService.get_user_balance(user)
        
        # Get recent AI enhancements
        recent_transactions = Transaction.objects.filter(
            user=user,
            transaction_status='APPROVED'
        ).order_by('-created_at')[:10]
        
        total_tokens_purchased = sum(t.tokens_generated for t in recent_transactions)
        
        return {
            'available_tokens': balance.available_tokens,
            'tokens_used': balance.tokens_used,
            'total_tokens_purchased': total_tokens_purchased,
            'payment_status': balance.payment_status,
            'can_use_ai': balance.can_use_ai_enhancement()
        }
