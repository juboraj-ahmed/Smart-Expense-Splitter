# Smart Expense Splitter - Testing Guide & Example Requests

## 📋 Testing Approach

This guide provides real-world test scenarios and example requests to validate all functionality.

---

## 🚀 Setup Before Testing

### 1. Start Django Server
```bash
python manage.py runserver
# Server running at http://127.0.0.1:8000
```

### 2. Create Test Users (in Django Shell)
```bash
python manage.py shell

from apps.accounts.models import User

# Create 4 test users
alice = User.objects.create_user('alice', 'alice@test.com', 'Pass123')
bob = User.objects.create_user('bob', 'bob@test.com', 'Pass123')
charlie = User.objects.create_user('charlie', 'charlie@test.com', 'Pass123')
david = User.objects.create_user('david', 'david@test.com', 'Pass123')

exit()
```

---

## ✅ Test Scenario: Summer Trip Expense Splitting

This End-to-End test follows a realistic scenario: 4 friends plan a trip, share expenses, and settle payments.

### Test 1: User Registration & Authentication

#### 1.1 Register Alice

```bash
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice_trip",
    "email": "alice.trip@example.com",
    "password": "SuperSecure123!",
    "password_confirm": "SuperSecure123!",
    "first_name": "Alice",
    "last_name": "Smith"
  }'
```

**Expected Response: 201 Created**
```json
{
  "user": {
    "id": 1,
    "username": "alice_trip",
    "email": "alice.trip@example.com",
    "first_name": "Alice",
    "trust_score": 100,
    "created_at": "2025-04-20T10:00:00Z"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### 1.2 Login Alice

```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice.trip@example.com",
    "password": "SuperSecure123!"
  }'
```

**Expected Response: 200 OK**
```json
{
  "user": {
    "id": 1,
    "username": "alice_trip",
    "email": "alice.trip@example.com",
    "trust_score": 100
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Extract and save access token:**
```bash
ACCESS_TOKEN=<your_token_from_response>
```

#### 1.3 Register other users
Register bob, charlie, david similarly (or use the Django shell users created earlier)

---

### Test 2: Group Creation & Member Management

#### 2.1 Create Group

```bash
curl -X POST http://localhost:8000/api/v1/groups/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Bali Summer Trip 2025",
    "description": "Vacation with the squad"
  }'
```

**Expected Response: 201 Created**
```json
{
  "id": 5,
  "name": "Bali Summer Trip 2025",
  "description": "Vacation with the squad",
  "created_by": {
    "id": 1,
    "username": "alice_trip"
  },
  "members": [{
    "id": 1,
    "username": "alice_trip",
    "role": "admin"
  }],
  "members_count": 1,
  "created_at": "2025-04-20T10:15:00Z"
}
```

**Save group_id: 5**

#### 2.2 Add Members to Group

```bash
# Add Bob
curl -X POST http://localhost:8000/api/v1/groups/5/add_member/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 2, "role": "member"}'

# Add Charlie
curl -X POST http://localhost:8000/api/v1/groups/5/add_member/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 3, "role": "member"}'

# Add David
curl -X POST http://localhost:8000/api/v1/groups/5/add_member/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 4, "role": "member"}'
```

**Expected: 201 Created for each**

#### 2.3 Get Group Details

```bash
curl -X GET http://localhost:8000/api/v1/groups/5/ \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Response:**
```json
{
  "id": 5,
  "name": "Bali Summer Trip 2025",
  "members": [
    {
      "id": 1,
      "username": "alice_trip",
      "role": "admin",
      "trust_score": 100
    },
    {
      "id": 2,
      "username": "bob_trip",
      "role": "member",
      "trust_score": 100
    },
    {
      "id": 3,
      "username": "charlie_trip",
      "role": "member",
      "trust_score": 100
    },
    {
      "id": 4,
      "username": "david_trip",
      "role": "member",
      "trust_score": 100
    }
  ],
  "members_count": 4,
  "your_balance": 0.00,
  "total_expenses": 0.00,
  "created_at": "2025-04-20T10:15:00Z"
}
```

---

### Test 3: Expense Creation & Splitting

#### 3.1 Alice Pays for Hotel ($300)

Split equally among 4 people:

```bash
curl -X POST http://localhost:8000/api/v1/expenses/create_equal_split/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": 5,
    "amount": "300.00",
    "description": "Hotel Bali - 2 nights",
    "category": "accommodation",
    "participant_ids": [1, 2, 3, 4]
  }'
```

**Expected Response: 201 Created**
```json
{
  "id": 101,
  "group": 5,
  "paid_by": {"id": 1, "username": "alice_trip"},
  "amount": "300.00",
  "description": "Hotel Bali - 2 nights",
  "category": "accommodation",
  "splits": [
    {"user_id": 1, "username": "alice_trip", "amount": "75.00"},
    {"user_id": 2, "username": "bob_trip", "amount": "75.00"},
    {"user_id": 3, "username": "charlie_trip", "amount": "75.00"},
    {"user_id": 4, "username": "david_trip", "amount": "75.00"}
  ],
  "created_at": "2025-04-20T10:30:00Z"
}
```

#### 3.2 Bob Pays for Meals ($120)

```bash
# Login as Bob (get his token)
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "bob@test.com",
    "password": "Pass123"
  }'

# Save BOB_TOKEN from response

# Bob creates expense (3-way split)
curl -X POST http://localhost:8000/api/v1/expenses/create_equal_split/ \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": 5,
    "amount": "120.00",
    "description": "Group dinner",
    "category": "food",
    "participant_ids": [2, 3, 4]
  }'
```

**Expected: 201 Created**
Each of Bob, Charlie, David owes $40

#### 3.3 Charlie Pays for Activities ($500)

```bash
# Get Charlie token
# Charlie pays for activities (everyone participates)
curl -X POST http://localhost:8000/api/v1/expenses/create_equal_split/ \
  -H "Authorization: Bearer $CHARLIE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": 5,
    "amount": "500.00",
    "description": "Activities - diving lessons",
    "category": "entertainment",
    "participant_ids": [1, 2, 3, 4]
  }'
```

**Expected: 201 Created**
Everyone owes $125 to Charlie

---

### Test 4: Balance Verification

#### 4.1 Get Group Balances

```bash
curl -X GET http://localhost:8000/api/v1/groups/5/balances/ \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Response:**
```json
{
  "group_id": 5,
  "group_name": "Bali Summer Trip 2025",
  "total_expenses": "920.00",
  "balances": [
    {
      "user": {
        "id": 1,
        "username": "alice_trip",
        "trust_score": 100
      },
      "total_paid": "300.00",
      "total_owes": "240.00",
      "net_balance": "60.00"  # Alice is owed $60
    },
    {
      "user": {
        "id": 2,
        "username": "bob_trip",
        "trust_score": 100
      },
      "total_paid": "120.00",
      "total_owes": "240.00",
      "net_balance": "-120.00"  # Bob owes $120
    },
    {
      "user": {
        "id": 3,
        "username": "charlie_trip",
        "trust_score": 100
      },
      "total_paid": "500.00",
      "total_owes": "240.00",
      "net_balance": "260.00"  # Charlie is owed $260
    },
    {
      "user": {
        "id": 4,
        "username": "david_trip",
        "trust_score": 100
      },
      "total_paid": "0.00",
      "total_owes": "240.00",
      "net_balance": "-240.00"  # David owes $240
    }
  ]
}
```

#### 4.2 Check Balance Between Two Users

```bash
# Alice's balance with Bob
curl -X GET "http://localhost:8000/api/v1/users/1/balance_with/2/?group_id=5" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Response:**
```json
{
  "from_user": {"id": 1, "username": "alice_trip"},
  "to_user": {"id": 2, "username": "bob_trip"},
  "group_id": 5,
  "net_balance": "75.00",  # Alice is owed $75 by Bob
  "details": {
    "total_paid_by_from_user": "75.00",
    "total_paid_by_to_user": "0.00",
    "interpretation": "bob_trip owes alice_trip",
    "amount": "75.00"
  }
}
```

---

### Test 5: Settlement & Payments

#### 5.1 Bob Settles with Charlie

Bob owes Charlie $40 (from meal) + $125 (from activities) = $165 total

```bash
curl -X POST http://localhost:8000/api/v1/settlements/ \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": 5,
    "to_user_id": 3,
    "amount": "165.00",
    "description": "Settlement for activities and meals"
  }'
```

**Expected Response: 201 Created**
```json
{
  "id": 201,
  "from_user": {"id": 2, "username": "bob_trip"},
  "to_user": {"id": 3, "username": "charlie_trip"},
  "group_id": 5,
  "amount": "165.00",
  "description": "Settlement for activities and meals",
  "created_at": "2025-04-20T11:00:00Z",
  "updated_balances": {
    "from_user_balance": "-120.00",  # Bob still owes others
    "to_user_balance": "95.00"       # Charlie updated
  }
}
```

#### 5.2 David Settles with Charlie

David owes Charlie: $125 (activities) + $40 (meals) = $165
Plus owes Alice: $75 (hotel)

```bash
# Get David token
curl -X POST http://localhost:8000/api/v1/settlements/ \
  -H "Authorization: Bearer $DAVID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": 5,
    "to_user_id": 3,
    "amount": "165.00",
    "description": "Settlement"
  }'

# Then settle with Alice
curl -X POST http://localhost:8000/api/v1/settlements/ \
  -H "Authorization: Bearer $DAVID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": 5,
    "to_user_id": 1,
    "amount": "75.00",
    "description": "Settlement for hotel"
  }'
```

---

### Test 6: Trust Score Updates

#### 6.1 Check Alice's Trust Score

After all settlements are complete:

```bash
curl -X GET http://localhost:8000/api/v1/users/1/trust-score/ \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Response:**
```json
{
  "user_id": 1,
  "username": "alice_trip",
  "current_score": 100,
  "previous_score": 100,
  "score_breakdown": {
    "base_score": 100,
    "late_payment_penalty": 0,
    "pending_amount_penalty": 0,
    "consistency_bonus": 0,
    "final_score": 100
  },
  "metrics": {
    "total_payments": 0,
    "on_time_payments": 0,
    "late_payments": 0,
    "avg_days_late": 0.0,
    "pending_amount": "0.00",
    "pending_since_days": 0
  },
  "last_updated": "2025-04-20T11:10:00Z"
}
```

#### 6.2 Intentionally Create Late Payment

```bash
# Have Alice pay late (manually edit in DB or use admin)
# Then check score again - should show penalties
```

---

## 🧪 Test Case: Error Handling

#### Test 7.1: Invalid Registration

```bash
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "al",  # Too short
    "email": "invalid",  # Invalid format
    "password": "short"  # Too short
  }'
```

**Expected Response: 400 Bad Request**
```json
{
  "error": "Validation failed",
  "details": {
    "username": ["Username must be at least 3 characters."],
    "email": ["Enter a valid email address."],
    "password": ["Password must be at least 8 characters with..."]
  }
}
```

#### Test 7.2: Cannot Settle More Than Owed

```bash
curl -X POST http://localhost:8000/api/v1/settlements/ \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": 5,
    "to_user_id": 1,
    "amount": "999.00",  # Bob doesn't owe this much
    "description": "Invalid settlement"
  }'
```

**Expected Response: 400 Bad Request**
```json
{
  "error": "bob_trip only owes 75.00 to alice_trip, cannot settle 999.00"
}
```

#### Test 7.3: Cannot Pay Yourself

```bash
curl -X POST http://localhost:8000/api/v1/settlements/ \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": 5,
    "to_user_id": 2,  # Same as from_user (Bob)
    "amount": "50.00"
  }'
```

**Expected Response: 400 Bad Request**
```json
{
  "error": "You cannot settle payment with yourself."
}
```

#### Test 7.4: Splits Must Sum to Amount

```bash
curl -X POST http://localhost:8000/api/v1/expenses/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": 5,
    "amount": "100.00",
    "description": "Test",
    "splits": [
      {"user_id": 1, "amount": "30.00"},
      {"user_id": 2, "amount": "30.00"}  # Only $60, not $100
    ]
  }'
```

**Expected Response: 400 Bad Request**
```json
{
  "error": "Validation failed",
  "details": {
    "splits": ["Splits total (60.00) must equal expense amount (100.00)."]
  }
}
```

---

## 📊 Performance Testing

### Test 8: Large Group Balances Query

```bash
# Create group with many members and expenses
# Measure query time

time curl -X GET http://localhost:8000/api/v1/groups/5/balances/ \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Target: <200ms response time
```

### Test 9: List Expenses with Pagination

```bash
# Should efficiently paginate through 1000+ expenses
curl -X GET "http://localhost:8000/api/v1/groups/5/expenses/?page=1&limit=20" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Try: page=50 (1000+ expenses total)
curl -X GET "http://localhost:8000/api/v1/groups/5/expenses/?page=50&limit=20" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

## ✅ Complete Test Checklist

- [ ] Register new user
- [ ] Login with credentials
- [ ] Get user profile
- [ ] Create group
- [ ] Add member to group
- [ ] Get group details with members
- [ ] Create expense with equal splits
- [ ] Create expense with manual splits
- [ ] Get group balances (correct calculation)
- [ ] Get balance between two users
- [ ] Record payment/settlement
- [ ] Verify balance updates after settlement
- [ ] Check trust score increases with on-time payment
- [ ] Verify cannot settle more than owed
- [ ] Verify cannot pay yourself
- [ ] Verify splits must sum to amount
- [ ] Test invalid email registration
- [ ] Test invalid password
- [ ] Test access to groups you're not member of
- [ ] Test pagination on list endpoints

---

## 🔧 Debug Techniques

### Check What Happened in Database

```bash
python manage.py shell

from apps.expenses.models import Payment
from apps.accounts.models import User

user = User.objects.get(username='alice_trip')
payments = Payment.objects.filter(from_user=user)
print(f"Payments made: {payments.count()}")

# Check balances calculated correctly
from apps.expenses.services import SettlementService
from apps.groups.models import Group
group = Group.objects.get(id=5)
balance = SettlementService.calculate_user_balance(user, group)
print(f"Alice's balance: {balance}")
```

### Enable SQL Logging

```python
# Add to settings.py
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'django.db.backends': {'handlers': ['console'], 'level': 'DEBUG'},
    },
}
```

---

## 📈 Success Criteria

✅ All CRUD operations work at full REST compliance
✅ Balance calculations are mathematically correct
✅ Transactions are atomic (no partial updates)
✅ Trust scores respond to payment events
✅ 100% of E2E scenarios pass
✅ Error handling provides helpful messages
✅ Response times < 500ms for complex queries
✅ No unauthorized access between groups

---

**When all tests pass, your fintech application is production-ready! 🚀**

