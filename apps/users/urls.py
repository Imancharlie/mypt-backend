from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomTokenObtainPairView, UserRegistrationView, UserProfileView,
    logout_view, dashboard_data, change_password_view, activate_account,
    resend_activation_email, activate_with_admin_code, verify_otp, google_auth,
    google_complete_registration, upload_profile_picture, remove_profile_picture,
)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint."""
    return Response({
        'status': 'healthy',
        'message': 'Auth service is running'
    })

urlpatterns = [
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('activate/<uidb64>/<token>/', activate_account, name='activate-account'),
    path('resend-activation/', resend_activation_email, name='resend-activation'),
    path('send-email-otp/', resend_activation_email, name='send-email-otp'),
    path('verify-otp/', verify_otp, name='verify-otp'),
    path('verify-email-otp/', verify_otp, name='verify-email-otp'),
    path('activate-with-admin-code/', activate_with_admin_code, name='activate-with-admin-code'),
    path('google-auth/', google_auth, name='google-auth'),
    path('google-complete-registration/', google_complete_registration, name='google-complete-registration'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', logout_view, name='logout'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/upload-picture/', upload_profile_picture, name='upload-profile-picture'),
    path('profile/remove-picture/', remove_profile_picture, name='remove-profile-picture'),
    path('dashboard/', dashboard_data, name='dashboard'),
    path('change-password/', change_password_view, name='change_password'),
    path('health/', health_check, name='health'),
] 
