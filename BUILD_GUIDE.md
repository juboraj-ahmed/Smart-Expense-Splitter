# Smart Expense Splitter - Step-by-Step Build Guide

## 📋 Prerequisites

### System Requirements
- Python 3.9+
- PostgreSQL 12+ (optional for production)
- Redis (optional for caching/celery, not required for basic version)
- Git
- pip

### Development Tools
- VS Code or PyCharm
- Postman or curl (for API testing)
- DbVisualizer or pgAdmin (for DB inspection)

---

## 🚀 Phase 1: Initial Setup (30 mins)

### Step 1.1: Create Virtual Environment

```bash
# Navigate to project directory
cd "Fintech Project"

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### Step 1.2: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install from requirements.txt
pip install -r requirements.txt
```

### Step 1.3: Create .env File

Create `.env` file in project root:

```bash
# Django
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (defaults to SQLite for development)
DB_ENGINE=django.db.backends.sqlite3
# DB_NAME=expense_splitter  # For PostgreSQL

# Auth
JWT_SECRET_KEY=your-jwt-secret-key-here

# Logging
LOG_LEVEL=INFO
DJANGO_LOG_LEVEL=INFO

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

### Step 1.4: Create Django Migrations

```bash
# Create migrations for all models
python manage.py makemigrations

# Apply migrations to database
python manage.py migrate

# Verify by checking database
python manage.py dbshell
```

### Step 1.5: Create Superuser

```bash
python manage.py createsuperuser
# Follow prompts to create admin account
```

### Step 1.6: Run Development Server

```bash
python manage.py runserver

# Should see:
# Starting development server at http://127.0.0.1:8000/
```

**Verify it's working:**
```bash
curl http://localhost:8000/api/v1/root/
# Should return API root JSON
```

---

## 📦 Phase 2: Models & Core Features (2-3 hours)

### Step 2.1: Verify Models

Models are already created in:
- `apps/accounts/models.py` - User, TrustScoreAudit
- `apps/groups/models.py` - Group, Membership
- `apps/expenses/models.py` - Expense, Split, Payment

### Step 2.2: Create Admin Interface

```bash
# Edit apps/accounts/admin.py
# Register User model
from django.contrib import admin
from apps.accounts.models import User, TrustScoreAudit

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'trust_score', 'created_at')
    search_fields = ('username', 'email')
    list_filter = ('trust_score', 'created_at')

@admin.register(TrustScoreAudit)
class TrustScoreAuditAdmin(admin.ModelAdmin):
    list_display = ('user', 'old_score', 'new_score', 'reason', 'computed_at')
    readonly_fields = ('user', 'old_score', 'new_score', 'computed_at')
```

Similar registrations for groups and expenses.

### Step 2.3: Test Models in Shell

```bash
python manage.py shell

# Create users
from apps.accounts.models import User
alice = User.objects.create_user(username='alice', email='alice@test.com', password='Pass123')
bob = User.objects.create_user(username='bob', email='bob@test.com', password='Pass123')

# Create group
from apps.groups.models import Group
group = Group.objects.create(name='Test Group', created_by=alice)

# Add members
group.add_member(alice, role='admin')
group.add_member(bob, role='member')

# Create expense
from apps.expenses.models import Expense, Split
from decimal import Decimal
expense = Expense.objects.create(
    group=group,
    paid_by=alice,
    amount=Decimal('100.00'),
    description='Pizza'
)

# Create splits
Split.objects.create(expense=expense, user=alice, amount=Decimal('50.00'))
Split.objects.create(expense=expense, user=bob, amount=Decimal('50.00'))

print(expense.get_total_split())  # Should be 100.00
```

---

## 🔐 Phase 3: Authentication & Views (2-3 hours)

### Step 3.1: Implement Account Views

Edit `apps/accounts/views.py`:

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from apps.accounts.serializers import (
    RegisterSerializer,
    LoginSerializer,
    TokenSerializer,
    UserSerializer,
    TrustScoreSerializer,
)

User = get_user_model()


class RegisterView(APIView):
    """
    POST /api/v1/auth/register/
    Public endpoint for user registration.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Generate tokens
            tokens = TokenSerializer.get_tokens(user)
            return Response({
                'user': UserSerializer(user).data,
                **tokens,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    POST /api/v1/auth/login/
    Public endpoint for user login.
    Returns JWT tokens.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            tokens = TokenSerializer.get_tokens(user)
            return Response({
                'user': UserSerializer(user).data,
                **tokens,
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for reading user data.
    GET /api/v1/users/ - List all users
    GET /api/v1/users/{id}/ - Get specific user
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['trust_score', 'created_at']
    ordering = ['-created_at']


class TrustScoreView(APIView):
    """
    GET /api/v1/users/{user_id}/trust-score/
    Returns detailed trust score breakdown for a user.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Import service in function to avoid circular imports
        from apps.expenses.services import TrustScoreService
        
        score_data = TrustScoreService.get_detailed_score(user)
        serializer = TrustScoreSerializer(score_data)
        return Response(serializer.data)
```

### Step 3.2: Test Authentication

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPass123!",
    "password_confirm": "TestPass123!"
  }'

# Save the access_token from response

# Login
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!"
  }'

# Get current user (with token)
curl -X GET http://localhost:8000/api/v1/users/me/ \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
```

---

## 💰 Phase 4: Expense & Settlement Logic (3-4 hours)

### Step 4.1: Create Services Layer

Create `apps/expenses/services.py`:

This file contains business logic for:
- Calculating balances
- Creating expenses with validation
- Recording settlements
- Computing trust scores

(See next section for code)

### Step 4.2: Create Expense Views

Create `apps/expenses/views.py`:

```python
from rest_framework import viewsets, status
from rest_framework.views import APIView  
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.expenses.models import Expense, Split, Payment
from apps.groups.models import Group
```

(See detailed views section below)

### Step 4.3: Test Expense Creation

```bash
TOKEN=<your_token>

# Create group first
curl -X POST http://localhost:8000/api/v1/groups/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Trip Group",
    "description": "Summer vacation"
  }'

# Save group_id from response

# Add another member
curl -X POST http://localhost:8000/api/v1/groups/1/add_member/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 2}'

# Create expense
curl -X POST http://localhost:8000/api/v1/expenses/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": 1,
    "amount": "100.00",
    "description": "Pizza",
    "splits": [
      {"user_id": 1, "amount": "50.00"},
      {"user_id": 2, "amount": "50.00"}
    ]
  }'
```

---

## 🚀 Phase 5: Trust Score & Advanced Features (2-3 hours)

### Step 5.1: Implement Trust Score Service

Create comprehensive `TrustScoreService` with:
- Score calculation algorithm
- Penalty/bonus logic
- Historical tracking

(Detailed code in services section)

### Step 5.2: Add Signals for Automatic Updates

Create `apps/expenses/signals.py`:

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.expenses.models import Payment
from apps.expenses.services import TrustScoreService


@receiver(post_save, sender=Payment)
def update_trust_score_on_payment(sender, instance, created, **kwargs):
    """
    Recalculate trust score when payment is recorded.
    """
    if created:
        TrustScoreService.recalculate_score(instance.from_user)
        # Positive signal for punctual payer
```

### Step 5.3: Add Celery Tasks (Optional)

Create `apps/expenses/tasks.py`:

```python
from celery import shared_task
from apps.accounts.models import User
from apps.expenses.services import TrustScoreService


@shared_task
def recalculate_all_trust_scores():
    """
    Nightly task: recalculate all users' trust scores.
    Catches drifting overdue amounts.
    """
    users = User.objects.all()
    for user in users:
        TrustScoreService.recalculate_score(user)
```

---

## 🧪 Phase 6: Testing & Documentation (2 hours)

### Step 6.1: Unit Tests

Create `apps/expenses/tests.py`:

```python
from django.test import TestCase
from apps.accounts.models import User
from apps.groups.models import Group
from apps.expenses.models import Expense, Split, Payment
from decimal import Decimal


class ExpenseModelTest(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            username='alice',
            email='alice@test.com',
            password='Pass123'
        )
        self.group = Group.objects.create(created_by=self.alice)
        self.group.add_member(self.alice)
    
    def test_create_expense(self):
        expense = Expense.objects.create(
            group=self.group,
            paid_by=self.alice,
            amount=Decimal('100.00')
        )
        self.assertEqual(expense.amount, Decimal('100.00'))
    
    def test_split_validation(self):
        expense = Expense.objects.create(
            group=self.group,
            paid_by=self.alice,
            amount=Decimal('100.00')
        )
        Split.objects.create(
            expense=expense,
            user=self.alice,
            amount=Decimal('50.00')
        )
        self.assertEqual(expense.get_total_split(), Decimal('50.00'))


class PaymentTest(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user('alice', 'a@t.com', 'Pass123')
        self.bob = User.objects.create_user('bob', 'b@t.com', 'Pass123')
        self.group = Group.objects.create(created_by=self.alice)
    
    def test_cannot_pay_yourself(self):
        with self.assertRaises(Exception):
            Payment.objects.create(
                from_user=self.alice,
                to_user=self.alice,  # Same user!
                group=self.group,
                amount=Decimal('100.00')
            )


if __name__ == '__main__':
    import django
    django.setup()
```

### Step 6.2: Run Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test apps.expenses

# With verbose output
python manage.py test --verbosity=2
```

### Step 6.3: API Documentation

Use Postman or Swagger:

```bash
# Install drf-spectacular for auto-generated docs
pip install drf-spectacular

# Add to INSTALLED_APPS
# Then run:
python manage.py spectacular --file schema.yml

# Serve docs at /api/schema/swagger-ui/
```

---

## 📊 Testing Checklist

- [ ] User registration works
- [ ] JWT login returns tokens
- [ ] Create group and add members
- [ ] Create expense with splits
- [ ] Record settlement payment
- [ ] Calculate balance correctly
- [ ] Trust score updates on payment
- [ ] Cannot create negative amounts
- [ ] Cannot settle more than owed
- [ ] Cannot pay yourself

---

## 🚀 Deployment (Production)

### Step 1: Configure PostgreSQL

```bash
# Create database
createdb expense_splitter

# Update .env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=expense_splitter
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

### Step 2: Update Settings for Production

In `config/settings.py`:

```python
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']
SECRET_KEY = os.getenv('SECRET_KEY')  # Strong random key!
```

### Step 3: Run Collectstatic

```bash
python manage.py collectstatic
```

### Step 4: Use Gunicorn

```bash
pip install gunicorn

# Run with gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

### Step 5: Nginx Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }
    
    location /static/ {
        alias /path/to/project/staticfiles/;
    }
}
```

---

## 📈 Next Steps for Scaling

1. **Add Frontend React App**
   - Dashboard showing balances
   - Expense entry form
   - Settlement UI

2. **Add Notifications**
   - Email on due payment
   - SMS reminders
   - Push notifications (mobile app)

3. **Analytics**
   - Spending trends
   - Expense categories by user
   - Most frequent partners

4. **Advanced Features**
   - Recurring expenses
   - Budgeting
   - Export to PDF/Excel
   - Multiple currencies

---

## 🆘 Troubleshooting

### Issue: Migrations Fail
```bash
# Reset database
python manage.py flush
python manage.py migrate
```

### Issue: JWT Token Not Working
```bash
# Verify JWT is configured in settings.py
# Check token expiration time
# Use token refresh endpoint
```

### Issue: CORS Errors
```bash
# Check CORS_ALLOWED_ORIGINS in settings.py
# Verify frontend origin matches
```

### Issue: Performance Issues
```bash
# Add indexes to frequently queried fields
python manage.py sqlsequencereset apps.accounts | python manage.py dbshell
```

---

## 📚 Useful Commands

```bash
# Create migration
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Check pending migrations
python manage.py migrate --plan

# Shell with Django context
python manage.py shell

# Run tests
python manage.py test

# Create superuser
python manage.py createsuperuser

# Database backup
python manage.py dumpdata > backup.json

# Database restore
python manage.py loaddata backup.json
```

