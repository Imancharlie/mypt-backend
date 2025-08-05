from rest_framework import serializers
from .models import Company
from django.contrib.auth.models import User


class CompanySerializer(serializers.ModelSerializer):
    industry_display = serializers.CharField(source='get_industry_display', read_only=True)
    
    class Meta:
        model = Company
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class CompanyListSerializer(serializers.ModelSerializer):
    industry_display = serializers.CharField(source='get_industry_display', read_only=True)
    student_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = ('id', 'name', 'industry_type', 'industry_display', 'address', 'contact_person', 'student_count')
    
    def get_student_count(self, obj):
        return obj.userprofile_set.count()


class CompanyManagementSerializer(serializers.ModelSerializer):
    """Serializer for company management - allows editing with minimal required fields."""
    industry_display = serializers.CharField(source='get_industry_display', read_only=True)
    is_assigned_to_user = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = (
            'id', 'name', 'address', 'contact_person', 'phone', 'email', 
            'website', 'industry_type', 'industry_display', 'established_year', 
            'description', 'is_active', 'is_assigned_to_user', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_is_assigned_to_user(self, obj):
        """Check if this company is assigned to the current user."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                return request.user.profile.company == obj
            except:
                return False
        return False
    
    def validate_name(self, value):
        """Validate company name is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Company name is required.")
        return value.strip()
    
    def create(self, validated_data):
        """Create company and assign to current user if no company is assigned."""
        company = super().create(validated_data)
        
        # Assign to current user if they don't have a company
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                user_profile = request.user.profile
                if not user_profile.company:
                    user_profile.company = company
                    user_profile.save()
            except:
                pass  # User might not have a profile
        
        return company


class CompanySearchSerializer(serializers.ModelSerializer):
    """Serializer for company search results."""
    industry_display = serializers.CharField(source='get_industry_display', read_only=True)
    
    class Meta:
        model = Company
        fields = ('id', 'name', 'industry_type', 'industry_display', 'address', 'contact_person') 