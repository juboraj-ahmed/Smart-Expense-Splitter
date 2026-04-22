"""
Serializers for accounts app.
Handles user data validation and transformation for REST API.
"""

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User data.
    
    Used for reading user information, trust scores, profiles.
    Returns public-facing user information (no sensitive data).
    """
    
    trust_level = serializers.CharField(source='get_trust_level', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'trust_score',
            'trust_level',
            'bio',
            'phone',
            'age',
            'location',
            'occupation',
            'university',
            'avatar_url',
            'created_at',
        ]
        read_only_fields = ['id', 'trust_score', 'created_at']

    def validate_username(self, value):
        """Username must be unique (case-insensitive)."""
        qs = User.objects.filter(username__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This username is already taken by another user.")
        return value


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    
    Validates:
    - Username uniqueness
    - Email validity and uniqueness
    - Password strength (8+ chars, uppercase, digit)
    - Password confirmation match
    """
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        help_text="Password must be at least 8 characters with uppercase and number"
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True
    )
    
    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'password',
            'password_confirm',
            'first_name',
            'last_name',
        ]
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
        }
    
    def validate_username(self, value):
        """Username must be unique and 3+ characters."""
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters.")
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken by another user.")
        return value
    
    def validate_email(self, value):
        """Email must be unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value
    
    def validate_password(self, value):
        """Validate password strength."""
        try:
            validate_password(value)
        except DjangoValidationError as errors:
            raise serializers.ValidationError(list(errors))
        return value
    
    def validate(self, data):
        """Ensure passwords match."""
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': 'Passwords do not match.'
            })
        return data
    
    def create(self, validated_data):
        """Create user with password hashing."""
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    
    Accepts email + password and returns JWT tokens.
    """
    
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        """Authenticate user with email and password."""
        email = data.get('email')
        password = data.get('password')
        
        # Get user by email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password.")
        
        # Check password
        if not user.check_password(password):
            raise serializers.ValidationError("Invalid email or password.")
        
        # Check if user is active
        if not user.is_active:
            raise serializers.ValidationError("This account is inactive.")
        
        data['user'] = user
        return data


class TokenSerializer(serializers.Serializer):
    """
    Returns JWT tokens for authenticated user.
    """
    
    access_token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)
    user = UserSerializer(read_only=True)
    
    @staticmethod
    def get_tokens(user):
        """Generate JWT tokens for user."""
        refresh = RefreshToken.for_user(user)
        return {
            'refresh_token': str(refresh),
            'access_token': str(refresh.access_token),
        }


class TrustScoreSerializer(serializers.Serializer):
    """
    Detailed trust score breakdown for a user.
    """
    
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    current_score = serializers.IntegerField()
    previous_score = serializers.IntegerField()
    
    score_breakdown = serializers.DictField(
        help_text="Base score, penalties, and bonuses"
    )
    metrics = serializers.DictField(
        help_text="Payment history metrics"
    )
    last_updated = serializers.DateTimeField(
        help_text="When score was last recalculated"
    )
    history = serializers.ListField(
        help_text="Recent score changes"
    )
