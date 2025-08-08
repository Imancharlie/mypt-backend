from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal


class UserBalance(models.Model):
    """Model to track user's token balance and payment status."""
    
    PAYMENT_STATUS_CHOICES = [
        ('FREE_TRIAL', 'Free Trial'),
        ('UNSUBSCRIBED', 'Unsubscribed'),
        ('SUBSCRIBED', 'Subscribed'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='balance')
    available_tokens = models.IntegerField(default=400, validators=[MinValueValidator(0)])
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS_CHOICES, 
        default='FREE_TRIAL'
    )
    tokens_used = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_balances'
        verbose_name = 'User Balance'
        verbose_name_plural = 'User Balances'
    
    def __str__(self):
        return f"{self.user.username} - {self.available_tokens} tokens ({self.payment_status})"
    
    def can_use_ai_enhancement(self):
        """Check if user can use AI enhancement based on tokens and status."""
        if self.payment_status == 'FREE_TRIAL':
            return self.available_tokens >= 300  # Minimum for full week enhancement
        elif self.payment_status == 'SUBSCRIBED':
            return self.available_tokens >= 300
        return False
    
    def deduct_tokens(self, amount):
        """Deduct tokens and update usage."""
        if self.available_tokens >= amount:
            self.available_tokens -= amount
            self.tokens_used += amount
            self.save()
            return True
        return False
    
    def add_tokens(self, amount):
        """Add tokens to balance."""
        self.available_tokens += amount
        self.save()
    
    def calculate_tokens_from_amount(self, amount):
        """Calculate tokens based on payment amount: amount * (3/10)."""
        return int(amount * Decimal('0.3'))


class Transaction(models.Model):
    """Model to store payment transaction details."""
    
    PAYMENT_METHOD_CHOICES = [
        ('DIRECT', 'Direct Payment'),
        ('WAKALA', 'Money Agent (Wakala)'),
    ]
    
    TRANSACTION_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    user_phone_number = models.CharField(max_length=15, blank=True, null=True)
    sender_name = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(
        max_length=10, 
        choices=PAYMENT_METHOD_CHOICES, 
        default='DIRECT'
    )
    wakala_name = models.CharField(max_length=100, blank=True, null=True)
    transaction_status = models.CharField(
        max_length=20, 
        choices=TRANSACTION_STATUS_CHOICES, 
        default='PENDING'
    )
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    tokens_generated = models.IntegerField(default=0)
    confirmed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='confirmed_transactions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'transactions'
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.amount} ({self.transaction_status})"
    
    def calculate_tokens(self):
        """Calculate tokens based on amount: amount * (3/10)."""
        return int(self.amount * Decimal('0.3'))
    
    def approve_transaction(self, confirmed_by_user):
        """Approve transaction and update user balance."""
        if self.transaction_status == 'PENDING':
            self.transaction_status = 'APPROVED'
            self.confirmed_by = confirmed_by_user
            self.tokens_generated = self.calculate_tokens()
            self.save()
            
            # Update user balance
            user_balance, created = UserBalance.objects.get_or_create(user=self.user)
            user_balance.add_tokens(self.tokens_generated)
            user_balance.payment_status = 'SUBSCRIBED'
            user_balance.save()
            
            return True
        return False
    
    def is_staff_initialized(self):
        """Check if transaction was initialized by staff."""
        return self.confirmed_by is not None and self.transaction_status == 'PENDING'
