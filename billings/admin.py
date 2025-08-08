from django.contrib import admin
from .models import UserBalance, Transaction


@admin.register(UserBalance)
class UserBalanceAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'available_tokens', 'payment_status', 'tokens_used', 
        'created_at', 'updated_at'
    ]
    list_filter = ['payment_status', 'created_at', 'updated_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Balance Information', {
            'fields': ('available_tokens', 'payment_status', 'tokens_used')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'amount', 'payment_method', 'transaction_status', 
        'sender_name', 'confirmed_by', 'created_at'
    ]
    list_filter = [
        'transaction_status', 'payment_method', 'created_at', 
        'updated_at', 'confirmed_by'
    ]
    search_fields = [
        'user__username', 'user__email', 'sender_name', 
        'wakala_name', 'user_phone_number'
    ]
    readonly_fields = ['created_at', 'updated_at', 'tokens_generated']
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Payment Details', {
            'fields': (
                'user_phone_number', 'sender_name', 'payment_method', 
                'wakala_name', 'amount'
            )
        }),
        ('Transaction Status', {
            'fields': ('transaction_status', 'confirmed_by', 'tokens_generated')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Show all transactions to admin."""
        return super().get_queryset(request)
    
    def has_add_permission(self, request):
        """Allow admins to add transactions."""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """Allow admins to change transactions."""
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        """Allow admins to delete transactions."""
        return request.user.is_superuser
