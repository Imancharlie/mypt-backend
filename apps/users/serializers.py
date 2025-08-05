from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import UserProfile


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password', 'password_confirm')
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        UserProfile.objects.create(user=user)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    user_details = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'updated_at')
    
    def get_user_details(self, obj):
        return {
            'username': obj.user.username,
            'email': obj.user.email,
            'full_name': f"{obj.user.first_name} {obj.user.last_name}".strip()
        }
    
    def validate_student_id(self, value):
        """Validate student_id uniqueness only if provided"""
        if value:
            # Check if this student_id is already used by another user
            user = self.context['request'].user
            if UserProfile.objects.filter(student_id=value).exclude(user=user).exists():
                raise serializers.ValidationError("A user with this student ID already exists.")
        return value
    
    def to_internal_value(self, data):
        """Convert display names to choice values before validation"""
        # Handle display names for program field
        if 'program' in data and data['program']:
            program_mapping = {
                'BSc. Mechanical Engineering': 'MECHANICAL',
                'BSc. Electrical Engineering': 'ELECTRICAL',
                'BSc. Civil Engineering': 'CIVIL',
                'BSc. Textile Design': 'TEXTILE_DESIGN',
                'BSc. Textile Engineering': 'TEXTILE_ENGINEERING',
                'BSc. Industrial Engineering': 'INDUSTRIAL',
                'BSc. Geomatic Engineering': 'GEOMATIC',
                'BSc. Chemical Engineering': 'CHEMICAL',
                'Bachelor of Architecture': 'ARCHITECTURE',
                'Bachelor of Science in Quantity Surveying': 'QUANTITY_SURVEYING',
            }
            if data['program'] in program_mapping:
                data['program'] = program_mapping[data['program']]
        
        # Handle display names for pt_phase field
        if 'pt_phase' in data and data['pt_phase']:
            phase_mapping = {
                'Practical Training 1': 'PT1',
                'Practical Training 2': 'PT2',
                'Practical Training 3': 'PT3',
            }
            if data['pt_phase'] in phase_mapping:
                data['pt_phase'] = phase_mapping[data['pt_phase']]
        
        # Handle empty strings for numeric fields
        if 'year_of_study' in data and (data['year_of_study'] == '' or data['year_of_study'] == 'null'):
            data['year_of_study'] = None
        
        # Handle null values for string fields
        for field in ['student_id', 'department', 'supervisor_name', 'supervisor_email', 'phone_number', 'company_name', 'company_region']:
            if field in data and data[field] is None:
                data[field] = ''
        
        return super().to_internal_value(data)
    
    def validate(self, attrs):
        """Custom validation for the entire profile"""
        # Ensure year_of_study is within valid range if provided
        year_of_study = attrs.get('year_of_study')
        if year_of_study is not None and year_of_study != '' and year_of_study != 'null':
            try:
                year_int = int(year_of_study)
                if year_int < 1 or year_int > 4:
                    raise serializers.ValidationError("Year of study must be between 1 and 4.")
                attrs['year_of_study'] = year_int
            except (ValueError, TypeError):
                attrs['year_of_study'] = None
        
        return attrs


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'profile')
        read_only_fields = ('id', 'username', 'email') 