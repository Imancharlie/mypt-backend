from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db import transaction as db_transaction
from .models import UserBalance, Transaction
from .serializers import (
    UserBalanceSerializer, TransactionSerializer, TransactionCreateSerializer,
    StaffTransactionCreateSerializer, TransactionApprovalSerializer, TokenUsageSerializer
)
from apps.reports.models import WeeklyReport, DailyReport


class UserBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for user balance management."""
    serializer_class = UserBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get balance for the current user."""
        return UserBalance.objects.filter(user=self.request.user)
    
    def get_object(self):
        """Get or create balance for the current user."""
        balance, created = UserBalance.objects.get_or_create(user=self.request.user)
        return balance
    
    @action(detail=False, methods=['get'])
    def my_balance(self, request):
        """Get current user's balance."""
        balance = self.get_object()
        serializer = self.get_serializer(balance)
        return Response({
            'success': True,
            'data': serializer.data
        })


class TransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for transaction management."""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = []
    
    def get_queryset(self):
        """Get transactions for the current user."""
        return Transaction.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'create':
            return TransactionCreateSerializer
        return TransactionSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new transaction."""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            transaction = serializer.save()
            return Response({
                'success': True,
                'message': 'Transaction created successfully. Please wait for approval.',
                'data': TransactionSerializer(transaction).data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def verify_payment(self, request, pk=None):
        """Verify payment details submitted by user."""
        transaction = self.get_object()
        
        # Get verification data from request
        user_phone_number = request.data.get('user_phone_number')
        sender_name = request.data.get('sender_name')
        amount = request.data.get('amount')
        
        if not all([user_phone_number, sender_name, amount]):
            return Response({
                'success': False,
                'message': 'All fields are required: user_phone_number, sender_name, amount'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if transaction was initialized by staff
        if transaction.is_staff_initialized():
            # Compare with staff initialization
            if (transaction.user_phone_number == user_phone_number and
                transaction.sender_name == sender_name and
                float(transaction.amount) == float(amount)):
                # Auto-approve if details match
                transaction.approve_transaction(request.user)
                return Response({
                    'success': True,
                    'message': 'Payment verified and approved automatically!',
                    'data': TransactionSerializer(transaction).data
                })
            else:
                return Response({
                    'success': False,
                    'message': 'Payment details do not match staff initialization'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Update transaction with user details
            transaction.user_phone_number = user_phone_number
            transaction.sender_name = sender_name
            transaction.save()
            
            return Response({
                'success': True,
                'message': 'Payment details updated. Waiting for staff approval.',
                'data': TransactionSerializer(transaction).data
            })


class StaffTransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for staff to manage transactions."""
    serializer_class = StaffTransactionCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get all transactions for staff view."""
        if self.request.user.is_staff:
            return Transaction.objects.all()
        return Transaction.objects.none()
    
    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'create':
            return StaffTransactionCreateSerializer
        return TransactionSerializer
    
    def create(self, request, *args, **kwargs):
        """Create transaction on behalf of user."""
        if not request.user.is_staff:
            return Response({
                'success': False,
                'message': 'Staff access required'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            transaction = serializer.save()
            return Response({
                'success': True,
                'message': 'Transaction created successfully. Waiting for user verification.',
                'data': TransactionSerializer(transaction).data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def pending_transactions(self, request):
        """Get all pending transactions."""
        if not request.user.is_staff:
            return Response({
                'success': False,
                'message': 'Staff access required'
            }, status=status.HTTP_403_FORBIDDEN)
        
        pending_transactions = Transaction.objects.filter(transaction_status='PENDING')
        serializer = TransactionSerializer(pending_transactions, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def approve_transaction(self, request, pk=None):
        """Approve a transaction."""
        if not request.user.is_staff:
            return Response({
                'success': False,
                'message': 'Staff access required'
            }, status=status.HTTP_403_FORBIDDEN)
        
        transaction = self.get_object()
        
        if transaction.transaction_status != 'PENDING':
            return Response({
                'success': False,
                'message': 'Transaction is not pending'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Approve transaction
        if transaction.approve_transaction(request.user):
            return Response({
                'success': True,
                'message': 'Transaction approved successfully!',
                'data': TransactionSerializer(transaction).data
            })
        else:
            return Response({
                'success': False,
                'message': 'Failed to approve transaction'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def reject_transaction(self, request, pk=None):
        """Reject a transaction."""
        if not request.user.is_staff:
            return Response({
                'success': False,
                'message': 'Staff access required'
            }, status=status.HTTP_403_FORBIDDEN)
        
        transaction = self.get_object()
        
        if transaction.transaction_status != 'PENDING':
            return Response({
                'success': False,
                'message': 'Transaction is not pending'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        transaction.transaction_status = 'REJECTED'
        transaction.confirmed_by = request.user
        transaction.save()
        
        return Response({
            'success': True,
            'message': 'Transaction rejected successfully',
            'data': TransactionSerializer(transaction).data
        })


class TokenUsageViewSet(viewsets.ViewSet):
    """ViewSet for token usage tracking."""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def track_usage(self, request):
        """Track token usage for AI enhancement."""
        serializer = TokenUsageSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        usage_type = serializer.validated_data['usage_type']
        weekly_report_id = serializer.validated_data['weekly_report_id']
        
        # Get user balance
        user_balance, created = UserBalance.objects.get_or_create(user=request.user)
        
        # Check if user can use AI enhancement
        if not user_balance.can_use_ai_enhancement():
            return Response({
                'success': False,
                'message': 'Insufficient tokens or not subscribed. Please top up your account.',
                'available_tokens': user_balance.available_tokens,
                'payment_status': user_balance.payment_status
            }, status=status.HTTP_402_PAYMENT_REQUIRED)
        
        # Determine token cost based on usage type
        token_costs = {
            'FULLFILLED': 300,  # 5 days filled
            'PARTIAL': 400,      # 3-4 days filled
            'EMPTY': 500         # less than 3 days
        }
        
        token_cost = token_costs.get(usage_type, 500)
        
        # Deduct tokens
        if user_balance.deduct_tokens(token_cost):
            return Response({
                'success': True,
                'message': f'AI enhancement used. {token_cost} tokens deducted.',
                'remaining_tokens': user_balance.available_tokens,
                'usage_type': usage_type,
                'tokens_deducted': token_cost
            })
        else:
            return Response({
                'success': False,
                'message': 'Insufficient tokens for AI enhancement.',
                'available_tokens': user_balance.available_tokens,
                'required_tokens': token_cost
            }, status=status.HTTP_402_PAYMENT_REQUIRED)
    
    @action(detail=False, methods=['get'])
    def usage_history(self, request):
        """Get user's token usage history."""
        user_balance = get_object_or_404(UserBalance, user=request.user)
        
        # Get recent transactions
        recent_transactions = Transaction.objects.filter(
            user=request.user,
            transaction_status='APPROVED'
        ).order_by('-created_at')[:10]
        
        return Response({
            'success': True,
            'data': {
                'current_balance': UserBalanceSerializer(user_balance).data,
                'recent_transactions': TransactionSerializer(recent_transactions, many=True).data
            }
        })


class BillingDashboardViewSet(viewsets.ViewSet):
    """ViewSet for billing dashboard."""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def dashboard_data(self, request):
        """Get billing dashboard data."""
        user_balance, created = UserBalance.objects.get_or_create(user=request.user)
        
        # Get user's transaction history
        transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')[:5]
        
        # Get pending transactions count
        pending_count = Transaction.objects.filter(
            user=request.user,
            transaction_status='PENDING'
        ).count()
        
        # Calculate total spent
        total_spent = sum(t.amount for t in transactions if t.transaction_status == 'APPROVED')
        
        return Response({
            'success': True,
            'data': {
                'balance': UserBalanceSerializer(user_balance).data,
                'recent_transactions': TransactionSerializer(transactions, many=True).data,
                'pending_transactions': pending_count,
                'total_spent': float(total_spent),
                'can_use_ai': user_balance.can_use_ai_enhancement()
            }
        })
    
    @action(detail=False, methods=['get'])
    def payment_info(self, request):
        """Get payment information for users."""
        return Response({
            'success': True,
            'data': {
                'payment_number': '0712345678',  # Replace with actual payment number
                'payment_instructions': [
                    'Send money to the provided number',
                    'Use your name as sender name',
                    'Submit transaction details after payment',
                    'Wait for staff approval'
                ],
                'token_calculation': 'Tokens = Amount × 0.3',
                'usage_costs': {
                    'fullfilled': '300 tokens (5 days filled)',
                    'partial': '400 tokens (3-4 days filled)',
                    'empty': '500 tokens (less than 3 days)'
                }
            }
        })
