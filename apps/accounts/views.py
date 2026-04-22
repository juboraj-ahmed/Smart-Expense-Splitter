"""
Views for accounts app.
Handles authentication, user management, and trust scores.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from apps.accounts.serializers import (
    RegisterSerializer,
    LoginSerializer,
    TokenSerializer,
    UserSerializer,
    TrustScoreSerializer,
)
from apps.expenses.services import TrustScoreService

User = get_user_model()


class RegisterView(APIView):
    """
    POST /api/v1/auth/register/
    
    Public endpoint for user registration.
    
    Request:
    {
      "username": "alice",
      "email": "alice@example.com",
      "password": "SecurePass123!",
      "password_confirm": "SecurePass123!"
    }
    
    Response: 201 Created
    {
      "user": {...},
      "access_token": "...",
      "refresh_token": "..."
    }
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            tokens = TokenSerializer.get_tokens(user)
            return Response(
                {
                    'user': UserSerializer(user).data,
                    'access_token': tokens['access_token'],
                    'refresh_token': tokens['refresh_token'],
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    POST /api/v1/auth/login/
    
    Public endpoint for login. Returns JWT tokens.
    
    Request:
    {
      "email": "alice@example.com",
      "password": "SecurePass123!"
    }
    
    Response: 200 OK
    {
      "user": {...},
      "access_token": "...",
      "refresh_token": "..."
    }
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            tokens = TokenSerializer.get_tokens(user)
            return Response(
                {
                    'user': UserSerializer(user).data,
                    'access_token': tokens['access_token'],
                    'refresh_token': tokens['refresh_token'],
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for reading and updating user profiles.
    
    GET /api/v1/users/ - List all users (paginated)
    GET /api/v1/users/{id}/ - Get user by ID
    GET /api/v1/users/me/ - Get current authenticated user
    
    Supports:
    - Search by username, email, name
    - Filter by trust_score
    - Ordering by trust_score, created_at
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['trust_score', 'created_at', 'username']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter to non-deleted users."""
        return User.objects.filter(is_active=True)
    
    def list(self, request, *args, **kwargs):
        """Override list to add 'me' endpoint."""
        if request.query_params.get('me'):
            serializer = self.get_serializer(request.user)
            return Response({'user': serializer.data})
        return super().list(request, *args, **kwargs)
        
    def update(self, request, *args, **kwargs):
        user = self.get_object()
        if request.user != user and not request.user.is_staff:
            return Response({"detail": "Not authorized to update this profile."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        user = self.get_object()
        if request.user != user and not request.user.is_staff:
            return Response({"detail": "Not authorized to update this profile."}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)
        
    def create(self, request, *args, **kwargs):
        return Response({"detail": "Use registration endpoint."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "Not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class TrustScoreView(APIView):
    """
    GET /api/v1/users/{user_id}/trust-score/
    
    Returns detailed trust score breakdown for a user.
    Accessible to authenticated users (anyone can view anyonse's trust score).
    
    Response:
    {
      "user_id": 1,
      "username": "alice",
      "current_score": 92,
      "score_breakdown": {...},
      "metrics": {...}
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        score_data = TrustScoreService.get_detailed_score(user)
        serializer = TrustScoreSerializer(score_data)
        return Response(serializer.data, status=status.HTTP_200_OK)
