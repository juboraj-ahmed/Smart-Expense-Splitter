# 💰 Smart Expense Splitter - Production-Ready Fintech Application

![Status](https://img.shields.io/badge/status-production%20ready-brightgreen)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Django](https://img.shields.io/badge/django-4.2-darkgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

A sophisticated, production-level expense management system with automated settlement calculations and trust scoring based on payment behavior.

---

## 🎯 Project Overview

**Smart Expense Splitter** is a group-based expense management web application that enables transparent, fair cost-sharing among friends, roommates, or travelers. It goes beyond simple splitting by introducing behavioral trust scoring to predict payment reliability.

### Core Features

✅ **User System** - JWT authentication, secure password hashing  
✅ **Group Management** - Create and manage expense-sharing groups  
✅ **Expense Splitting** - Equal or manual split allocation  
✅ **Automatic Settlement** - Calculate who owes whom instantly  
✅ **Trust Scoring** - Behavioral metric based on payment history  
✅ **Balance Calculation** - Transparent ledger of all transactions  
✅ **RESTful API** - Production-ready endpoints with DRF  
✅ **Transaction Safety** - ACID compliance for financial consistency

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────┐
│            REST API Layer (DRF)             │
│      /auth/register, /expenses, etc         │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│         Service Layer (Business Logic)      │
│  ExpenseService, SettlementService, etc     │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│         Django ORM Models Layer             │
│   User, Group, Expense, Split, Payment      │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│      PostgreSQL / SQLite (Database)         │
│      Atomic transactions, constraints       │
└─────────────────────────────────────────────┘
```

**Key Design Principles:**
- Clean separation of concerns (models, services, views)
- Business logic centralized in services (not views or models)
- Atomic transactions for data consistency
- No "balance" field - calculated on-demand from transactions
- Immutable payment records (audit trail)

---

## 📁 Project Structure

```
Fintech Project/
├── config/                      # Django configuration
│   ├── settings.py             # All settings (DB, JWT, DRF config)
│   ├── urls.py                 # API routing
│   ├── wsgi.py                 # WSGI application
│   └── celery.py               # Celery configuration
│
├── apps/                        # Django applications
│   ├── accounts/               # User authentication & profiles
│   │   ├── models.py           # User model with trust_score
│   │   ├── serializers.py      # Register, Login serializers
│   │   ├── views.py            # Auth views
│   │   └── admin.py            # Django admin
│   ├── groups/                 # Group management
│   │   ├── models.py           # Group, Membership models
│   │   ├── serializers.py      # Group serializers
│   │   ├── views.py            # Group views
│   │   └── admin.py
│   ├── expenses/               # Expense management
│   │   ├── models.py           # Expense, Split, Payment models
│   │   ├── serializers.py      # Expense serializers
│   │   ├── services.py         # Business logic (core!)
│   │   ├── views.py            # Expense/settlement views
│   │   ├── signals.py          # Auto trust score updates
│   │   ├── admin.py
│   │   └── tasks.py            # Celery tasks (optional)
│   └── core/                   # Shared utilities
│       ├── exceptions.py       # Custom exception handler
│       └── models.py
│
├── manage.py                    # Django management script
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
├── README.md                    # This file
├── BUILD_GUIDE.md              # Step-by-step implementation guide
├── ARCHITECTURE.md             # System design & decisions
├── DATABASE_SCHEMA.md          # Database structure
├── API_DESIGN.md               # API endpoint specifications
└── TRUST_SCORE_ALGORITHM.md    # Trust scoring logic

```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Git

### Installation

1. **Clone repository**
   ```bash
   cd "Fintech Project"
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start development server**
   ```bash
   python manage.py runserver
   ```

8. **Access application**
   - API: http://localhost:8000/api/v1/
   - Admin: http://localhost:8000/admin/

---

## 📚 Documentation

### Full Documentation Files

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design, entity relationships, scalability
- **[DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)** - Table definitions and relationships
- **[API_DESIGN.md](API_DESIGN.md)** - Complete REST API endpoints with examples
- **[TRUST_SCORE_ALGORITHM.md](TRUST_SCORE_ALGORITHM.md)** - Trust scoring formula and logic
- **[BUILD_GUIDE.md](BUILD_GUIDE.md)** - Step-by-step implementation walkthrough

### Key Features Explained

#### 1. **User System**
```python
# Registration
POST /api/v1/auth/register/
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "SecurePass123!"
}

# Login
POST /api/v1/auth/login/
{
  "email": "alice@example.com",
  "password": "SecurePass123!"
}
# Returns JWT tokens
```

#### 2. **Group Management**
```python
# Create group
POST /api/v1/groups/
{
  "name": "Summer Trip 2025",
  "description": "Bali vacation"
}

# Add member
POST /api/v1/groups/{id}/add_member/
{
  "user_id": 2,
  "role": "member"
}
```

#### 3. **Expense Splitting**
```python
# Create expense with manual splits
POST /api/v1/expenses/
{
  "group_id": 5,
  "amount": "300.00",
  "description": "Hotel",
  "splits": [
    {"user_id": 1, "amount": "100.00"},
    {"user_id": 2, "amount": "100.00"},
    {"user_id": 3, "amount": "100.00"}
  ]
}

# Or create equal splits
POST /api/v1/expenses/create_equal_split/
{
  "group_id": 5,
  "amount": "120.00",
  "description": "Pizza",
  "participant_ids": [1, 2, 3, 4]
}
```

#### 4. **Settlement & Balances**
```python
# Get group balances
GET /api/v1/groups/{id}/balances/
# Shows who paid what, who owes what

# Get balance between two users
GET /api/v1/users/{id}/balance_with/{other_id}/?group_id=5

# Record payment
POST /api/v1/settlements/
{
  "group_id": 5,
  "to_user_id": 2,
  "amount": "75.50",
  "description": "Payment for hotel"
}
```

#### 5. **Trust Scoring**
```python
# Get trust score
GET /api/v1/users/{id}/trust-score/
# Returns:
# {
#   "current_score": 92,
#   "score_breakdown": {...},
#   "metrics": {...}
# }
```

---

## 🔒 Security Features

### Authentication & Authorization
- ✅ JWT tokens with 24-hour expiration
- ✅ Refresh token rotation
- ✅ bcrypt password hashing
- ✅ Permission checks on all endpoints

### Data Integrity
- ✅ Database-level constraints (CHECK, FOREIGN KEY, UNIQUE)
- ✅ Atomic transactions for multi-step operations
- ✅ Immutable payment records
- ✅ User cannot view groups they're not member of

### Validation
- ✅ Input sanitization at serializer level
- ✅ Amount validation (no negatives, proper decimals)
- ✅ Business logic validation in services
- ✅ CSRF protection

### Scalability Safeguards
- ✅ Indexed queries for fast lookups
- ✅ Pagination on list endpoints
- ✅ Rate limiting on auth endpoints
- ✅ Query optimization with select_related/prefetch_related

---

## 💡 Business Logic Highlights

### Balance Calculation (No Stored Balance Field)
```
User's Balance = Total Paid - Total Owes - Payments Made + Payments Received

Why no stored field?
- Single source of truth (transactions)
- Automatic audit trail
- Can recalculate history anytime
```

### Trust Score Algorithm
```
Base: 100
- Late Payment Penalty: -5 per occurrence
- Pending Overdue Penalty: -2 per 7 days
- Consistency Bonus: +3 if 100% on-time last 5 payments

Score reflects payment reliability (0-100)
Used in:  
- User profile visibility
- Payment verification
- Future ML models for default prediction
```

### Transaction Safety
```python
@transaction.atomic
def record_settlement(from_user, to_user, group, amount):
    # Atomic: all succeed or all fail
    verify_balance()
    Payment.objects.create(...)
    update_trust_score()
    # Either everything saves or nothing does
```

---

## 🧪 Testing

### Unit Tests

```bash
# Run all tests
python manage.py test

# Run specific app
python manage.py test apps.expenses

# With verbose output
python manage.py test --verbosity=2
```

### Manual API Testing

**Using curl:**
```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPass123!"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!"
  }'

# Create group (with token)
curl -X POST http://localhost:8000/api/v1/groups/ \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Trip", "description": "Summer vacation"}'
```

**Using Postman:**
- Import API endpoints from [API_DESIGN.md](API_DESIGN.md)
- Set up environment variables for BASE_URL, TOKEN
- Test full workflow: Register → Create Group → Add Members → Create Expense → Settle

---

## 📊 Database Schema Summary

**Key Tables:**
- `user` - Users with trust scores
- `group` - Expense-sharing groups
- `membership` - User-to-group associations with roles
- `expense` - Shared costs
- `split` - Individual shares in expenses
- `payment` - Settlement transactions between users
- `trust_score_audit` - Historical score changes

**Critical Indexes:**
- `(group_id, user_id)` on membership (most common joins)
- `user_id` on splits (balance queries)
- `from_user_id, to_user_id` on payments (settlement queries)

---

## 🚀 Deployment

### Production Checklist

- [ ] Change DEBUG=False in settings.py
- [ ] Use strong SECRET_KEY (generate with `python -c 'import secrets; print(secrets.token_urlsafe(50))'`)
- [ ] Configure PostgreSQL database
- [ ] Set allowed hosts properly
- [ ] Enable HTTPS/SSL
- [ ] Use Gunicorn instead of `runserver`
- [ ] Configure Nginx as reverse proxy
- [ ] Set up logging and monitoring
- [ ] Enable error tracking (Sentry)
- [ ] Configure email for notifications

### Docker Deployment

```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

---

## 📈 Future Enhancements

### Phase 2
- [ ] Frontend dashboard (React)
- [ ] Email notifications
- [ ] Push notifications (mobile)
- [ ] Expense categories & analytics

### Phase 3
- [ ] Mobile app (React Native)
- [ ] Multiple currencies
- [ ] Recurring expenses
- [ ] Budget tracking

### Phase 4
- [ ] Machine learning for fraud detection
- [ ] Credit score integration
- [ ] P2P payment integration
- [ ] Multitenancy support

---

## 🛠️ Troubleshooting

### Common Issues

**Issue:** Migrations fail
```bash
# Solution
python manage.py makemigrations
python manage.py migrate --fake-initial
```

**Issue:** JWT token expired
```bash
# Use refresh token endpoint
POST /api/v1/auth/token/refresh/
{"refresh_token": "..."}
```

**Issue:** CORS errors
```bash
# Add origin to CORS_ALLOWED_ORIGINS in .env
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

**Issue:** 404 on API endpoints
```bash
# Verify URL matches urls.py patterns
# Check /api/v1/root/ returns available endpoints
```

---

## 📚 Learning Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [JWT Authentication](https://django-rest-framework-simplejwt.readthedocs.io/)
- [Django Signals](https://docs.djangoproject.com/en/stable/topics/signals/)
- [Database Transactions](https://docs.djangoproject.com/en/stable/topics/db/transactions/)

---

## 👨‍💻 Development Guidelines

### Code Style
- Follow PEP 8
- Use 4 spaces for indentation
- Max line length: 88 characters
- Use meaningful variable names

### Git Workflow
```bash
# Feature branch
git checkout -b feature/add-notifications

# Commit with clear messages
git commit -m "Add email notifications for due payments"

# Push and create PR
git push origin feature/add-notifications
```

### Documentation
- Document complex functions with docstrings
- Update API_DESIGN.md for new endpoints
- Keep README.md current

---

## 💼 Use Cases

### Personal Projects
- Roommate expense sharing
- Family expense tracking
- Travel group expense splitting

### Collaborative Teams
- Project team expenses
- Work trip cost allocation
- Client entertainment tracking

### Communities
- Club/society expenses
- Event cost sharing
- Community fund management

---

## 📝 License

MIT License - See LICENSE file for details

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch
3. Add tests for new features
4. Submit pull request

---

## 📧 Support & Contact

For questions, issues, or suggestions:
- Create an issue in the repository
- Check existing documentation
- Review the troubleshooting guide

---

## 🎓 Learning Outcomes

This project demonstrates:
- ✅ Clean architecture (separation of concerns)
- ✅ Production-level Django development
- ✅ RESTful API design
- ✅ Financial transaction handling
- ✅ Database design & optimization
- ✅ Security best practices
- ✅ Testing strategies
- ✅ Documentation practices

**Perfect for building a portfolio for fintech internships! 🚀**

---

**Built with ❤️ for aspiring engineers**

