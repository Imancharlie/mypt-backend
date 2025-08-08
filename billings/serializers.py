from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserBalance, Transaction


class UserBalanceSerializer(serializers.ModelSerializer):
    """Serializer for UserBalance model."""
    user = serializers.ReadOnlyField(source='user.username')
    user_full_name = serializers.ReadOnlyField(source='user.get_full_name')
    can_use_ai = serializers.ReadOnlyField(source='can_use_ai_enhancement')
    
    class Meta:
        model = UserBalance
        fields = [
            'id', 'user', 'user_full_name', 'available_tokens', 'payment_status',
            'tokens_used', 'can_use_ai', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'available_tokens', 'tokens_used', 'created_at', 'updated_at']


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model."""
    user = serializers.ReadOnlyField(source='user.username')
    user_full_name = serializers.ReadOnlyField(source='user.get_full_name')
    confirmed_by_name = serializers.ReadOnlyField(source='confirmed_by.get_full_name')
    tokens_generated = serializers.ReadOnlyField()
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'user', 'user_full_name', 'user_phone_number', 'sender_name',
            'payment_method', 'wakala_name', 'transaction_status', 'amount',
            'tokens_generated', 'confirmed_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'transaction_status', 'tokens_generated', 'confirmed_by_name', 'created_at', 'updated_at']


class TransactionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating transactions."""
    
    class Meta:
        model = Transaction
        fields = [
            'user_phone_number', 'sender_name', 'payment_method', 
            'wakala_name', 'amount'
        ]
    
    def validate(self, data):
        """Validate transaction data."""
        payment_method = data.get('payment_method')
        wakala_name = data.get('wakala_name')
        
        # If payment method is WAKALA, wakala_name is required
        if payment_method == 'WAKALA' and not wakala_name:
            raise serializers.ValidationError("Wakala name is required when using money agent payment method.")
        
        # If payment method is DIRECT, wakala_name should be empty
        if payment_method == 'DIRECT' and wakala_name:
            raise serializers.ValidationError("Wakala name should not be provided for direct payment method.")
        
        return data
    
    def create(self, validated_data):
        """Create transaction for the current user."""
        user = self.context['request'].user
        validated_data['user'] = user
        
        # Set default sender name if not provided
        if not validated_data.get('sender_name'):
            validated_data['sender_name'] = user.get_full_name() or user.username
        
        return super().create(validated_data)


class StaffTransactionCreateSerializer(serializers.ModelSerializer):
    """Serializer for staff to create transactions on behalf of users."""
    user_id = serializers.IntegerField(write_only=True)
    user_username = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = Transaction
        fields = [
            'user_id', 'user_username', 'user_phone_number', 'sender_name',
            'payment_method', 'wakala_name', 'amount'
        ]
    
    def validate_user_id(self, value):
        """Validate that user exists."""
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist.")
        return value
    
    def validate(self, data):
        """Validate transaction data."""
        payment_method = data.get('payment_method')
        wakala_name = data.get('wakala_name')
        
        # If payment method is WAKALA, wakala_name is required
        if payment_method == 'WAKALA' and not wakala_name:
            raise serializers.ValidationError("Wakala name is required when using money agent payment method.")
        
        # If payment method is DIRECT, wakala_name should be empty
        if payment_method == 'DIRECT' and wakala_name:
            raise serializers.ValidationError("Wakala name should not be provided for direct payment method.")
        
        return data
    
    def create(self, validated_data):
        """Create transaction for the specified user."""
        user_id = validated_data.pop('user_id')
        user = User.objects.get(id=user_id)
        validated_data['user'] = user
        
        # Set default sender name if not provided
        if not validated_data.get('sender_name'):
            validated_data['sender_name'] = user.get_full_name() or user.username
        
        return super().create(validated_data)


class TransactionApprovalSerializer(serializers.ModelSerializer):
    """Serializer for approving transactions."""
    
    class Meta:
        model = Transaction
        fields = ['transaction_status']
        read_only_fields = ['transaction_status']


class TokenUsageSerializer(serializers.Serializer):
    """Serializer for token usage tracking."""
    usage_type = serializers.ChoiceField(choices=[
        ('FULLFILLED', 'Fullfilled (5 days)'),
        ('PARTIAL', 'Partial (3-4 days)'),
        ('EMPTY', 'Empty (less than 3 days)')
    ])
    weekly_report_id = serializers.IntegerField()
    
    def validate_usage_type(self, value):
        """Validate usage type."""
        return value
    
    def validate_weekly_report_id(self, value):
        """Validate weekly report exists."""
        from apps.reports.models import WeeklyReport
        try:
            WeeklyReport.objects.get(id=value, student=self.context['request'].user)
        except WeeklyReport.DoesNotExist:
            raise serializers.ValidationError("Weekly report does not exist.")
        return value
