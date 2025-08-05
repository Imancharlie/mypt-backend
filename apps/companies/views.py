from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as filters
from .models import Company
from .serializers import CompanySerializer, CompanyListSerializer
from apps.core.permissions import IsCompanyOwnerOrReadOnly
from django.db import models


class CompanyFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr='icontains')
    industry_type = filters.CharFilter(lookup_expr='exact')
    
    class Meta:
        model = Company
        fields = ['name', 'industry_type', 'is_active']


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated, IsCompanyOwnerOrReadOnly]
    filterset_class = CompanyFilter
    search_fields = ['name', 'industry_type']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CompanyListSerializer
        return CompanySerializer
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search companies by name or industry"""
        query = request.query_params.get('q', '')
        if not query:
            return Response({
                'success': False,
                'message': 'Search query is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        companies = self.get_queryset().filter(
            models.Q(name__icontains=query) | 
            models.Q(industry_type__icontains=query)
        )
        
        serializer = self.get_serializer(companies, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': companies.count()
        })
    
    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        """Get students working at this company"""
        company = self.get_object()
        students = company.userprofile_set.all()
        
        from apps.users.serializers import UserProfileSerializer
        serializer = UserProfileSerializer(students, many=True)
        
        return Response({
            'success': True,
            'data': {
                'company': CompanySerializer(company).data,
                'students': serializer.data,
                'student_count': students.count()
            }
        }) 