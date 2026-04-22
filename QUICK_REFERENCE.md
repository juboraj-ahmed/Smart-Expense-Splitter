# ⚡ Quick Reference Card

## 🚀 Quick Setup (Copy-Paste)

```bash
# Create environment
python -m venv venv
source venv/bin/activate

# Install
pip install -r requirements.txt

# Configure
cp .env.example .env

# Setup database
python manage.py makemigrations
python manage.py migrate

# Admin
python manage.py createsuperuser

# Run
python manage.py runserver

# Access
# API:  http://localhost:8000/api/v1/
# Admin: http://localhost:8000/admin/
```

---

## 📍 Key Files & What They Do

| File | Purpose |
|------|---------|
| `config/settings.py` | All Django config (DB, JWT, APIs) |
| `apps/expenses/services.py` | Core business logic (MOST IMPORTANT) |
| `apps/*/views.py` | API endpoints |
| `apps/*/serializers.py` | Input validation & response formatting |
| `apps/*/models.py` | Database structure |

---

## 🔑 Key Concepts

| Concept | Explanation |
|---------|-------------|
| **Balance** | Doesn't exist as field - calculated on-demand from transactions |
| **Trust Score** | 0-100 based on payment history, updated via signals |
| **Splits** | Individual shares in expense (separate model for flexibility) |
| **Payment** | Settlement transaction (immutable, audit trail) |
| **Atomic** | All-or-nothing transactions (consistency) |

---

## 🛠️ Common Django Commands

```bash
# Migrations
python manage.py makemigrations
python manage.py migrate
python manage.py migrate --plan  # See what will happen

# Database
python manage.py dbshell         # Open database terminal
python manage.py dumpdata > backup.json
python manage.py loaddata backup.json

# Interactive Python
python manage.py shell

# Testing
python manage.py test
python manage.py test apps.expenses --verbosity=2

# Utilities
python manage.py createsuperuser
python manage.py changepassword username
python manage.py collectstatic
```

---

## 🧪 Test API Endpoints (with curl)

### Register
```bash
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@test.com","password":"Pass123!","password_confirm":"Pass123!"}'
```

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Pass123!"}'
# Save TOKEN from response
```

### Create Group
```bash
curl -X POST http://localhost:8000/api/v1/groups/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Trip","description":"Vacation"}'
```

### Create Expense (Equal Split)
```bash
curl -X POST http://localhost:8000/api/v1/expenses/create_equal_split/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"group_id":1,"amount":"100.00","description":"Dinner","participant_ids":[1,2,3]}'
```

### Get Balances
```bash
curl -X GET http://localhost:8000/api/v1/groups/1/balances/ \
  -H "Authorization: Bearer $TOKEN"
```

### Record Payment
```bash
curl -X POST http://localhost:8000/api/v1/settlements/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"group_id":1,"to_user_id":2,"amount":"50.00","description":"Settlement"}'
```

### Get Trust Score
```bash
curl -X GET http://localhost:8000/api/v1/users/1/trust-score/ \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🔍 Debug in Django Shell

```bash
python manage.py shell

# Import models
from apps.accounts.models import User
from apps.groups.models import Group, Membership
from apps.expenses.models import Expense, Split, Payment
from apps.expenses.services import SettlementService

# Create test user
user = User.objects.create_user('test', 'test@test.com', 'Pass123')

# Create group
group = Group.objects.create(name='Test', created_by=user)
Membership.objects.create(group=group, user=user, role='admin')

# Calculate balance
balance = SettlementService.calculate_user_balance(user, group)
print(f"Balance: {balance}")

# Get all expenses
for exp in Expense.objects.filter(group=group):
    print(f"{exp.description}: {exp.amount}")
```

---

## 📊 Database Access

```bash
# SQLite (development)
python manage.py dbshell
sqlite> SELECT * FROM "user";
sqlite> SELECT * FROM expense;

# PostgreSQL (production)
psql -U postgres -d expense_splitter
```

---

## 🔐 Key Security Settings

```python
# In settings.py or .env
DEBUG = False  # Never True in production!
SECRET_KEY = 'change-to-random-key'
ALLOWED_HOSTS = ['yourdomain.com']
CORS_ALLOWED_ORIGINS = ['https://frontend.com']

# JWT
JWT_SECRET_KEY = 'unique-secret'
SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'] = timedelta(hours=24)
```

---

## 📈 Performance Tips

```python
# In views - Efficient queries
.select_related('paid_by', 'group')  # For ForeignKey
.prefetch_related('splits', 'payments')  # For reverse relations
.filter(group_id__in=group_ids)  # Batch queries

# Use pagination
GET /api/v1/expenses/?limit=20&page=1

# Add indexes (in models)
class Meta:
    indexes = [
        models.Index(fields=['group_id', 'user_id']),
    ]
```

---

## 🚨 Common Errors & Fixes

| Error | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'rest_framework'` | `pip install -r requirements.txt` |
| `no such table: expense` | `python manage.py migrate` |
| `Invalid token` | Check token hasn't expired, use refresh endpoint |
| `403 Forbidden` | User isn't member of that group |
| `"Splits total must equal amount"` | Ensure splits sum to expense amount |
| `Cannot settle more than owed` | Balance calculation issue, check in shell |

---

## 📚 Documentation Quick Links

| Document | When To Read |
|----------|--------------|
| [README.md](README.md) | First! Project overview |
| [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) | Architecture overview |
| [BUILD_GUIDE.md](BUILD_GUIDE.md) | Step-by-step setup |
| [API_DESIGN.md](API_DESIGN.md) | When using/building endpoints |
| [ARCHITECTURE.md](ARCHITECTURE.md) | To understand design decisions |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | For schema questions |
| [TRUST_SCORE_ALGORITHM.md](TRUST_SCORE_ALGORITHM.md) | To understand scoring |
| [TESTING_GUIDE.md](TESTING_GUIDE.md) | To test endpoints |

---

## 💻 Useful Scripts

### Create Test Data
```python
# In shell
from django.contrib.auth import get_user_model
from apps.groups.models import Group, Membership

User = get_user_model()

# Create users
for name in ['alice', 'bob', 'charlie']:
    User.objects.create_user(name, f'{name}@test.com', 'Pass123')

# Create group
from apps.accounts.models import User
alice=User.objects.get(username='alice')
group = Group.objects.create(name='Friends', created_by=alice)

# Add members
for username in ['alice', 'bob', 'charlie']:
    user = User.objects.get(username=username)
    Membership.objects.create(group=group, user=user)
```

### Export Balances as CSV
```python
import csv
from apps.expenses.services import SettlementService
from apps.groups.models import Group

group = Group.objects.get(id=1)
balances = SettlementService.get_group_balances(group)

with open('balances.csv', 'w') as f:
    w = csv.writer(f)
    w.writerow(['User', 'Paid', 'Owes', 'Net'])
    for b in balances:
        w.writerow([b['user']['username'], b['total_paid'], 
                   b['total_owes'], b['net_balance']])
```

---

## 🎯 30-Second Debugging Workflow

1. **Check error in browser/curl response**
2. **Search code for error message** - find where it's raised
3. **Check inputs to that function** - likely invalid
4. **Use Django shell to test** - verify database state
5. **Add print() statements** temporarily for debugging
6. **Check database directly** with `python manage.py dbshell`

---

## 📞 When Stuck

```
1. Check documentation first (80% of answers there)
2. Search code for function/error
3. Try in Django shell interactively
4. Check Django/DRF official docs
5. Print models to inspect data
6. Use Django debug toolbar (advanced)
```

---

## ⚡ One-Liner Reference

```bash
# Quick server with logs
python manage.py runserver --verbosity 2

# Reset database
python manage.py flush --no-input && python manage.py migrate

# Interactive testing
python manage.py shell < test_script.py

# API root
curl http://localhost:8000/api/v1/root/

# Count expenses
python manage.py shell -c "from apps.expenses.models import Expense; print(Expense.objects.count())"
```

---

**Keep this card handy during development!** 📌

