from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserBalanceViewSet, TransactionViewSet, StaffTransactionViewSet,
    TokenUsageViewSet, BillingDashboardViewSet
)

# Create routers
router = DefaultRouter()
router.register(r'balance', UserBalanceViewSet, basename='user-balance')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'staff/transactions', StaffTransactionViewSet, basename='staff-transaction')
router.register(r'token-usage', TokenUsageViewSet, basename='token-usage')
router.register(r'dashboard', BillingDashboardViewSet, basename='billing-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]
