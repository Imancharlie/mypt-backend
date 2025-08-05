from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.urls import reverse


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request, format=None):
    return Response({
        'message': 'Industrial Practical Training Report Generator API',
        'version': '1.0.0',
        'endpoints': {
            'authentication': '/api/auth/',
            'users': '/api/profile/',
            'companies': '/api/companies/',
            'reports': '/api/reports/',
            'ai_assist': '/api/ai/',
            'export': '/api/export/',
        }
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({
        'status': 'healthy',
        'message': 'API is running successfully'
    }) 