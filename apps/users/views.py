from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .serializers import UserRegistrationSerializer, UserProfileSerializer, UserSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            # Get the user from the request data
            username = request.data.get('username')
            user = User.objects.get(username=username)
            # Safely check if user has complete profile
            has_complete_profile = False
            try:
                has_complete_profile = user.profile.company_name is not None and user.profile.company_name.strip() != ''
            except:
                has_complete_profile = False
            
            response.data['user'] = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.get_full_name(),
                'has_complete_profile': has_complete_profile
            }
        return response


class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'success': True,
            'message': 'User created successfully',
            'data': {
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }
        }, status=status.HTTP_201_CREATED)


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        user = self.request.user
        try:
            return user.profile
        except:
            # Create a profile for the user if it doesn't exist
            from apps.users.models import UserProfile
            return UserProfile.objects.create(user=user)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password_view(request):
    """Change password for authenticated user."""
    try:
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        
        if not current_password or not new_password:
            return Response({
                'success': False,
                'message': 'Both current_password and new_password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify current password
        user = request.user
        if not user.check_password(current_password):
            return Response({
                'success': False,
                'message': 'Current password is incorrect'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate new password
        if len(new_password) < 8:
            return Response({
                'success': False,
                'message': 'New password must be at least 8 characters long'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Change password
        user.set_password(new_password)
        user.save()
        
        return Response({
            'success': True,
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Error changing password',
            'errors': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.data.get('refresh')
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({
            'success': True,
            'message': 'Successfully logged out'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Error logging out',
            'errors': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_data(request):
    user = request.user
    
    # Safely get profile or create one if it doesn't exist
    try:
        profile = user.profile
    except:
        # Create a profile for the user if it doesn't exist
        from apps.users.models import UserProfile
        profile = UserProfile.objects.create(user=user)
    
    # Get basic stats
    from apps.reports.models import DailyReport, WeeklyReport, GeneralReport
    
    daily_reports_count = DailyReport.objects.filter(student=user).count()
    weekly_reports_count = WeeklyReport.objects.filter(student=user).count()
    completed_weekly_reports = WeeklyReport.objects.filter(student=user, is_complete=True).count()
    
    try:
        general_report = GeneralReport.objects.get(user=user)
        general_report_status = general_report.status
    except GeneralReport.DoesNotExist:
        general_report_status = 'NOT_STARTED'
    
    return Response({
        'success': True,
        'data': {
            'user': UserSerializer(user).data,
            'stats': {
                'daily_reports': daily_reports_count,
                'weekly_reports': weekly_reports_count,
                'completed_weekly_reports': completed_weekly_reports,
                'general_report_status': general_report_status,
            },
            'profile_complete': profile.company_name is not None and profile.company_name.strip() != ''
        }
    }) 