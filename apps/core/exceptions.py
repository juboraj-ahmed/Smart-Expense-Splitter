"""
Custom exception handlers for DRF.
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    """
    Custom exception handler that formats errors consistently.
    """
    response = exception_handler(exc, context)
    
    if response is not None:
        # Format error response
        if isinstance(response.data, dict):
            if 'detail' in response.data:
                response.data = {
                    'error': str(response.data['detail']),
                    'code': getattr(exc, 'default_code', 'error')
                }
            else:
                response.data = {
                    'error': 'Validation failed',
                    'code': 'validation_error',
                    'details': response.data
                }
        
        # Add status code
        response.data['status_code'] = response.status_code
    
    return response
