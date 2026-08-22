from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.conf import settings
from django.utils import timezone
import secrets
import random
import logging
import requests
from .serializers import UserRegistrationSerializer, UserProfileSerializer, UserSerializer
from .models import EmailVerificationOTP, UserProfile


logger = logging.getLogger(__name__)


def generate_otp():
    """Generate a 6-digit OTP code."""
    return str(random.randint(100000, 999999))


def send_otp_email(request, user):
    """Send a 6-digit OTP code to a user's email for verification."""
    # Invalidate any existing OTPs for this user
    EmailVerificationOTP.objects.filter(user=user, is_used=False).update(is_used=True)

    # Generate new OTP
    code = generate_otp()
    expires_at = timezone.now() + timezone.timedelta(minutes=10)  # OTP expires in 10 minutes
    otp = EmailVerificationOTP.objects.create(user=user, code=code, expires_at=expires_at)

    # DEBUG: Print OTP to terminal
    print(f"\n{'='*60}")
    print(f"🔐 OTP EMAIL DEBUG INFO")
    print(f"{'='*60}")
    print(f"Sending OTP to: {user.email}")
    print(f"Username: {user.username}")
    print(f"User ID: {user.id}")
    print(f"OTP Code: {code}")
    print(f"Expires at: {expires_at}")
    print(f"Admin Bypass Code: {settings.ADMIN_ACTIVATION_CODE}")
    print(f"{'='*60}\n")

    subject = 'Your MyPT Verification Code'
    text_body = (
        f'Hello {user.first_name or user.username},\n\n'
        f'Your verification code is: {code}\n\n'
        'This code will expire in 10 minutes. If you did not request this code, you can ignore this email.'
    )
    html_body = (
        f'<p>Hello {user.first_name or user.username},</p>'
        f'<p>Your verification code is: <strong>{code}</strong></p>'
        '<p>This code will expire in 10 minutes. If you did not request this code, you can ignore this email.</p>'
    )
    message = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [user.email])
    message.send(fail_silently=False)
    return otp


def send_activation_email(request, user):
    """Send a one-time, password-reset-style activation link to a user."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    activation_url = request.build_absolute_uri(
        reverse('activate-account', kwargs={'uidb64': uid, 'token': token})
    )
    subject = 'Activate your MyPT account'
    text_body = (
        f'Hello {user.first_name or user.username},\n\n'
        'Thanks for registering for MyPT. Activate your account by opening this link:\n'
        f'{activation_url}\n\n'
        'If you did not create this account, you can ignore this email.'
    )
    html_body = (
        f'<p>Hello {user.first_name or user.username},</p>'
        '<p>Thanks for registering for MyPT. Please activate your account:</p>'
        f'<p><a href="{activation_url}">Activate my account</a></p>'
        '<p>If you did not create this account, you can ignore this email.</p>'
    )
    message = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [user.email])
    message.attach_alternative(html_body, 'text/html')
    message.send(fail_silently=False)


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

        # Send SMS notification for new registration
        try:
            from .sms_service import send_registration_sms
            user_name = user.get_full_name() or user.username
            send_registration_sms(user.email, user_name)
        except Exception as e:
            # Log error but don't fail registration
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send registration SMS: {str(e)}")

        return Response({
            'success': True,
            'message': 'Account created successfully. You can now log in.',
            'data': {
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                },
            },
        }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def activate_account(request, uidb64, token):
    """Activate a new account from the one-time link sent by email."""
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=['is_active'])
            return Response({'success': True, 'message': 'Your account has been activated. You can now sign in.'})
        return Response({'success': True, 'message': 'Your account is already active.'})

    return Response(
        {'success': False, 'message': 'This activation link is invalid or has expired.'},
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def resend_activation_email(request):
    """Resend a 6-digit OTP code without revealing whether an email exists."""
    email = (request.data.get('email') or '').strip()
    user = User.objects.filter(email__iexact=email, is_active=False).first()
    if user:
        try:
            send_otp_email(request, user)
        except Exception:
            logger.exception('OTP email could not be resent for user %s', user.pk)
            return Response(
                {'success': False, 'message': 'Unable to send the verification code. Please try again later.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
    return Response({'success': True, 'message': 'If the account needs verification, a code has been sent.'})


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def verify_otp(request):
    """Verify a 6-digit OTP code to activate account, with admin code bypass option."""
    otp_code = (request.data.get('otp') or '').strip()
    email = (request.data.get('email') or '').strip()
    admin_code = (request.data.get('admin_code') or '').strip()

    # DEBUG: Log verification attempt
    print(f"\n{'='*60}")
    print(f"🔐 OTP VERIFICATION DEBUG INFO")
    print(f"{'='*60}")
    print(f"Email: {email}")
    print(f"OTP Code: {otp_code}")
    print(f"Admin Code: {admin_code}")
    print(f"Configured Admin Code: {settings.ADMIN_ACTIVATION_CODE}")
    print(f"{'='*60}\n")

    # Check if admin code is provided as bypass
    if admin_code:
        configured_code = settings.ADMIN_ACTIVATION_CODE
        print(f"DEBUG: Comparing admin_code '{admin_code}' with configured '{configured_code}'")
        if configured_code and secrets.compare_digest(admin_code, configured_code):
            # Admin code valid - activate the user
            user = User.objects.filter(email__iexact=email).first()
            if not user:
                print(f"DEBUG: User not found for email {email}")
                return Response({'success': False, 'message': 'No account matches that email.'}, status=status.HTTP_404_NOT_FOUND)
            print(f"DEBUG: User found: {user.username}, is_active: {user.is_active}")
            if not user.is_active:
                user.is_active = True
                user.save(update_fields=['is_active'])
                print(f"DEBUG: User activated")
            return Response({'success': True, 'message': 'Account activated successfully using admin code.'})
        else:
            print(f"DEBUG: Admin code comparison failed")
            return Response({'success': False, 'message': 'Invalid admin activation code.'}, status=status.HTTP_403_FORBIDDEN)

    # Regular OTP verification
    if not otp_code or not email:
        return Response(
            {'success': False, 'message': 'Both email and OTP code are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.filter(email__iexact=email).first()
    if not user:
        print(f"DEBUG: User not found for email {email}")
        return Response({'success': False, 'message': 'No account matches that email.'}, status=status.HTTP_404_NOT_FOUND)

    print(f"DEBUG: User found: {user.username}, checking OTP {otp_code}")

    # Find valid OTP for this user
    otp = EmailVerificationOTP.objects.filter(
        user=user,
        code=otp_code,
        is_used=False
    ).order_by('-created_at').first()

    if not otp:
        print(f"DEBUG: No valid OTP found for user")
        return Response(
            {'success': False, 'message': 'Invalid verification code.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not otp.is_valid():
        print(f"DEBUG: OTP expired")
        return Response(
            {'success': False, 'message': 'Verification code has expired.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Mark OTP as used
    otp.is_used = True
    otp.save(update_fields=['is_used'])

    # Activate the user
    if not user.is_active:
        user.is_active = True
        user.save(update_fields=['is_active'])

    print(f"DEBUG: OTP verified successfully, user activated")
    return Response({'success': True, 'message': 'Account verified and activated successfully.'})


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def activate_with_admin_code(request):
    """Support-only account activation using the server-configured secret code."""
    supplied_code = request.data.get('admin_code') or ''
    configured_code = settings.ADMIN_ACTIVATION_CODE
    if not configured_code or not secrets.compare_digest(supplied_code, configured_code):
        return Response({'success': False, 'message': 'Invalid admin activation code.'}, status=status.HTTP_403_FORBIDDEN)

    identifier = (request.data.get('email') or request.data.get('username') or '').strip()
    if not identifier:
        return Response(
            {'success': False, 'message': 'Provide the account email or username.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    user = User.objects.filter(email__iexact=identifier).first() or User.objects.filter(username=identifier).first()
    if not user:
        return Response({'success': False, 'message': 'No account matches that email or username.'}, status=status.HTTP_404_NOT_FOUND)

    if not user.is_active:
        user.is_active = True
        user.save(update_fields=['is_active'])
    return Response({'success': True, 'message': 'Account activated successfully.'})


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
def upload_profile_picture(request):
    """Upload profile picture for authenticated user."""
    try:
        user = request.user
        profile = user.profile

        if 'profile_picture' not in request.FILES:
            return Response({
                'success': False,
                'message': 'No profile picture file provided'
            }, status=status.HTTP_400_BAD_REQUEST)

        profile_picture = request.FILES['profile_picture']

        # Validate file size (max 5MB)
        if profile_picture.size > 5 * 1024 * 1024:
            return Response({
                'success': False,
                'message': 'Profile picture size must be less than 5MB'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/gif']
        if profile_picture.content_type not in allowed_types:
            return Response({
                'success': False,
                'message': 'Only JPEG, PNG, and GIF images are allowed'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Delete old profile picture if exists
        if profile.profile_picture:
            profile.profile_picture.delete(save=False)

        # Save new profile picture
        profile.profile_picture = profile_picture
        profile.save()

        # Get the URL of the uploaded image
        profile_picture_url = profile.profile_picture.url if profile.profile_picture else None

        return Response({
            'success': True,
            'message': 'Profile picture uploaded successfully',
            'profile_picture_url': profile_picture_url
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error uploading profile picture: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to upload profile picture. Please try again.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_profile_picture(request):
    """Remove profile picture for authenticated user."""
    try:
        user = request.user
        profile = user.profile

        if not profile.profile_picture:
            return Response({
                'success': False,
                'message': 'No profile picture to remove'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Delete profile picture
        profile.profile_picture.delete(save=False)
        profile.profile_picture = None
        profile.save()

        return Response({
            'success': True,
            'message': 'Profile picture removed successfully'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error removing profile picture: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to remove profile picture. Please try again.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def google_auth(request):
    """Authenticate user using Google Identity Services ID token."""
    # Try to get token from query parameter first, then from body
    id_token = request.query_params.get('id_token') or request.data.get('id_token')

    print("=" * 60)
    print("🔍 GOOGLE AUTH DEBUG")
    print("=" * 60)
    print(f"Request data keys: {request.data.keys() if request.data else 'None'}")
    print(f"Query params keys: {request.query_params.keys()}")
    print(f"ID token present: {bool(id_token)}")
    print(f"ID token length: {len(id_token) if id_token else 0}")
    print(f"ID token first 50 chars: {id_token[:50] if id_token else 'None'}")

    # Decode JWT without verification for debugging
    try:
        import base64
        import json
        parts = id_token.split('.')
        if len(parts) == 3:
            header = json.loads(base64.urlsafe_b64decode(parts[0] + '=='))
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=='))
            print(f"JWT Header: {json.dumps(header, indent=2)}")
            print(f"JWT Payload: {json.dumps(payload, indent=2)}")
            print(f"Token aud (audience): {payload.get('aud')}")
            print(f"Token iss (issuer): {payload.get('iss')}")
            print(f"Token exp (expiration): {payload.get('exp')}")
            print(f"Token email: {payload.get('email')}")
            print(f"Token email_verified: {payload.get('email_verified')}")
            print(f"Expected client ID: 817800310507-4bvn6jnon6qdhnkndfk5d5v8e5ntr78j.apps.googleusercontent.com")
    except Exception as e:
        print(f"Failed to decode JWT for debugging: {e}")

    print("=" * 60)

    if not id_token:
        return Response(
            {'success': False, 'message': 'ID token is required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Verify the ID token with Google
        print("📡 Calling Google tokeninfo endpoint...")
        response = requests.get(
            f'https://oauth2.googleapis.com/tokeninfo?id_token={id_token}'
        )

        print(f"Google response status: {response.status_code}")
        print(f"Google response body: {response.text[:1000] if response.text else 'Empty'}")

        if response.status_code != 200:
            print(f"❌ Token verification failed with status {response.status_code}")
            error_data = response.json() if response.text else {}
            print(f"Error details: {error_data}")
            return Response(
                {'success': False, 'message': f'Invalid ID token: {error_data.get("error_description", "Token verification failed")}'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        
        token_info = response.json()
        email = token_info.get('email')
        
        if not email:
            return Response(
                {'success': False, 'message': 'Email not found in token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Check if user exists
        user = User.objects.filter(email__iexact=email).first()
        
        if user:
            # User exists, log them in
            if not user.is_active:
                user.is_active = True
                user.save(update_fields=['is_active'])

            # Get profile picture from Google token info, or generate initials
            profile_picture = token_info.get('picture', '')
            if not profile_picture:
                # Generate initials from user's name
                first_name = user.first_name or ''
                last_name = user.last_name or ''
                initials = f"{first_name[0] if first_name else ''}{last_name[0] if last_name else ''}".upper()
                profile_picture = initials

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                'success': True,
                'message': 'Authentication successful.',
                'data': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'full_name': user.get_full_name(),
                        'picture': profile_picture,
                    },
                    'is_new_user': False
                }
            })
        else:
            # New user - return user data for registration
            first_name = token_info.get('given_name', '')
            last_name = token_info.get('family_name', '')
            picture = token_info.get('picture', '')

            # Generate initials if no picture
            if not picture:
                initials = f"{first_name[0] if first_name else ''}{last_name[0] if last_name else ''}".upper()
                picture = initials

            return Response({
                'success': True,
                'message': 'New user detected. Please complete registration.',
                'data': {
                    'is_new_user': True,
                    'user': {
                        'email': email,
                        'first_name': first_name,
                        'last_name': last_name,
                        'full_name': f"{first_name} {last_name}".strip(),
                        'picture': picture,
                    }
                }
            })
        
    except Exception as e:
        logger.exception('Google authentication error: %s', str(e))
        return Response(
            {'success': False, 'message': f'Authentication failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def google_complete_registration(request):
    """Complete registration for Google-authenticated users."""
    email = request.data.get('email')
    phone_number = request.data.get('phone_number')
    student_id = request.data.get('student_id', '')
    program = request.data.get('program')
    year_of_study = request.data.get('year_of_study')
    pt_phase = request.data.get('pt_phase', 'PT1')
    department = request.data.get('department', '')
    company_name = request.data.get('company_name', '')
    company_region = request.data.get('company_region', '')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')
    picture = request.data.get('picture', '')
    
    # Handle empty string for year_of_study
    if year_of_study == '' or year_of_study is None:
        year_of_study = None
    
    # Handle empty string for student_id to avoid unique constraint violation
    if student_id == '' or student_id is None:
        student_id = None
    
    # Derive department from program if not provided
    if not department and program:
        from apps.users.models import UserProfile
        department_mapping = {
            'computer_science': 'School of Computing',
            'information_technology': 'School of Computing',
            'software_engineering': 'School of Computing',
            'computer_engineering': 'School of Engineering',
            'data_science': 'School of Computing',
            'cybersecurity': 'School of Computing',
            'network_engineering': 'School of Engineering',
        }
        # Try to derive from program key
        for key, dept in department_mapping.items():
            if key in program.lower():
                department = dept
                break
        # Default fallback
        if not department:
            department = 'School of Computing'
    
    if not email or not phone_number or not program:
        return Response(
            {'success': False, 'message': 'Email, phone number, and program are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    try:
        # Generate a random password for the user (they won't use it)
        import secrets
        import string
        password = ''.join(secrets.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(32))
        
        # Generate username from email
        username = email.split('@')[0]
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        # Create user with Google data
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=True
        )
        
        # Create or update profile with Google data
        from apps.users.models import UserProfile
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.phone_number = phone_number
        profile.student_id = student_id
        profile.program = program
        profile.year_of_study = year_of_study
        profile.pt_phase = pt_phase
        profile.department = department
        profile.company_name = company_name
        profile.company_region = company_region
        profile.picture = picture  # Save Google profile picture
        profile.save()
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'success': True,
            'message': 'Registration completed successfully.',
            'data': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                }
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.exception('Google registration error: %s', str(e))
        return Response(
            {'success': False, 'message': 'Registration failed.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) 
