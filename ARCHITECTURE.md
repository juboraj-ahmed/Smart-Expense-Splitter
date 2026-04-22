# Smart Expense Splitter - System Architecture

## 🏗️ System Overview

This is a **distributed ledger-inspired** expense management system designed with **financial transaction principles**:
- Atomic operations for consistency
- Clear audit trails
- No floating balances (computed on-demand)
- Trust scoring based on behavioral patterns

---

## 📐 Architecture Layers

### 1. **API Layer** (Django REST Framework)
- HTTP endpoints following REST conventions
- Request/response serialization and validation
- Authentication & authorization middleware
- Error handling with appropriate HTTP status codes

### 2. **Service Layer** (Business Logic)
- `GroupService`: Group membership and management
- `ExpenseService`: Expense creation, splitting logic
- `SettlementService`: Payment recording and balance updates
- `TrustScoreService`: Score calculation and caching
- Keeps models thin, logic centralized

### 3. **Model Layer** (Django ORM)
- Domain objects representing real-world entities
- Field-level validation
- Query optimization through proper indexing

### 4. **Data Layer** (PostgreSQL)
- Relational schema with ACID compliance
- Foreign key constraints
- Transaction support for consistency

---

## 🗂️ Entity Relationship Diagram

```
┌─────────────┐
│    User     │
├─────────────┤
│ id (PK)     │
│ username    │
│ password    │
│ email       │
│ trust_score │
│ created_at  │
└────┬────────┘
     │
     ├─────────────────────────────────┐
     │                                 │
     ▼                                 ▼
┌──────────────────┐        ┌──────────────────┐
│   Membership     │        │   Expense        │
├──────────────────┤        ├──────────────────┤
│ id (PK)          │        │ id (PK)          │
│ group_id (FK)    │        │ group_id (FK)    │
│ user_id (FK)     │        │ paid_by_id (FK)  │
│ joined_at        │        │ amount           │
│ role             │        │ description      │
└──────────────────┘        │ created_at       │
                            └────┬─────────────┘
┌─────────────┐                  │
│    Group    │                  ▼
├─────────────┤             ┌─────────────┐
│ id (PK)     │             │   Split     │
│ name        │             ├─────────────┤
│ description │             │ id (PK)     │
│ created_by  │             │ expense_id  │
│ created_at  │             │ user_id     │
└─────────────┘             │ amount      │
                            └─────────────┘

┌──────────────┐
│   Payment    │
├──────────────┤
│ id (PK)      │
│ from_user_id │
│ to_user_id   │
│ group_id     │
│ amount       │
│ description  │
│ created_at   │
└──────────────┘
```

---

## 💡 Key Design Decisions

### 1. **No "Balance" Field in Database**

**Why?** Balances are derived from transactions, not stored.

**How it works:**
```
User A's balance with User B = 
  (All expenses where B paid and A benefited)
  - (All expenses where A paid and B benefited)
  - (All settlements from A to B)
  + (All settlements from B to A)
```

**Benefits:**
- No data inconsistency (single source of truth)
- Automatic audit trail through transactions
- Can recalculate history anytime

**Trade-off:** 
- More computation on queries (mitigated by caching and indexing)

---

### 2. **Trust Score as Denormalized Field**

**Why store it?**
- Frequently accessed (shown on every API response)
- Computed from many historical transactions
- Updated asynchronously is acceptable

**How it works:**
```python
Trust Score Formula:
  Base Score = 100
  
  Penalties:
  - For each payment > 7 days late: -5 points
  - For pending amount > 50% of user's total: -10 points
  - For 3+ consecutive on-time payments: +3 points
  
  Final Score = MAX(0, Base Score - Penalties + Bonuses)
```

**Update Strategy:**
- Recalculated when user settles payment
- Background job updates scores nightly
- Cache for 1 hour

---

### 3. **Transaction Safety for Settlements**

**Problem:** Prevent race conditions where user settles same amount twice.

**Solution:** Database-level locking
```python
with transaction.atomic():
    # Lock the user's record during update
    user = User.objects.select_for_update().get(id=user_id)
    
    # Verify they actually owe this amount
    actual_balance = calculate_balance(user_id, other_user_id)
    if settle_amount <= actual_balance:
        Payment.objects.create(...)
        user.trust_score = recalculate_trust_score(user)
        user.save()
```

---

### 4. **Expense Splits as Separate Model**

**Why not store split data in Expense?**
- Keeps concerns separated
- Easier to query individual user's expenses
- Supports arbitrary split amounts (not just equal)

**Example:**
```
Expense #1: Pizza ($30)
  Splits:
  - Alice: $15
  - Bob: $10
  - Charlie: $5

Query: "What does Alice owe?" -> Look at all Split records for Alice
```

---

## 🔒 Security Architecture

### Authentication
- **JWT tokens** with 24h expiration + refresh tokens
- Password hashed with bcrypt (Django default)
- Token issued on login, validated on each request

### Authorization
- Users can only see groups they're members of
- Users can only settle their own balances
- Admin can view all (future feature)

### Data Validation
- Input validation at serializer level
- Amount validation (non-negative, proper decimals)
- Business logic validation in services

### Rate Limiting (Optional but recommended)
- 5 login attempts per minute
- 100 API calls per minute per user
- Prevents brute force and abuse

---

## 📈 Scalability Considerations

### Current Capacity
- Handles ~1,000 active users
- ~10,000 expenses
- Complex queries still sub-100ms with proper indexing

### To Scale to 100,000+ Users

1. **Database**
   - Add read replicas for GET queries
   - Use connection pooling (pgBouncer)
   - Partition data by group_id for very large groups

2. **Caching**
   - Redis for trust scores
   - Cache user balances (invalidate on settlement)
   - Cache group membership lists

3. **Asynchronous Tasks**
   - Celery for trust score recalculation
   - Background job for nightly analytics

4. **Query Optimization**
   - Composite index: (group_id, user_id) on Membership
   - Composite index: (group_id, paid_by_id) on Expense
   - Index on Payment.created_at for time-based queries

### Example Indexing Strategy
```sql
-- User lookups
CREATE INDEX idx_user_email ON user(email);

-- Membership queries (most common)
CREATE INDEX idx_membership_group_user ON membership(group_id, user_id);

-- Expense queries
CREATE INDEX idx_expense_group ON expense(group_id);
CREATE INDEX idx_expense_paid_by ON expense(paid_by_id);

-- Split queries  
CREATE INDEX idx_split_user ON split(user_id);
CREATE INDEX idx_split_expense ON split(expense_id);

-- Payment queries
CREATE INDEX idx_payment_from_to ON payment(from_user_id, to_user_id);
```

---

## ⚠️ Edge Cases Handled

### 1. Self-Settlement
```
Q: Can a user settle with themselves?
A: No. Model validates: from_user_id != to_user_id
```

### 2. Negative Amounts
```
Q: What if someone tries to add a negative expense?
A: Rejected at serializer level (amount > 0 validation)
```

### 3. Split Amount Mismatch
```
Q: User adds expense of $100 but splits don't sum to $100?
A: Service validates: sum(splits) == expense.amount
   If not, raises ValidationError
```

### 4. Settling Unmortgaged Debt
```
Q: User tries to settle $500 when they only owe $300?
A: Service calculates actual balance, raises error if mismatch
```

### 5. Concurrent Expense Creation
```
Q: Two users add expense simultaneously?
A: Each creates separate Expense record (no race condition)
   Groups can have multiple expenses
```

---

## 📊 Performance Targets

| Operation | Target | Strategy |
|-----------|--------|----------|
| Get user balance | <100ms | Indexed queries + caching |
| Create expense | <300ms | Atomic transaction |
| List groups | <200ms | Pagination + index |
| Calculate trust score | <50ms | Cached value |

---

## 🚀 Deployment Considerations

### Development
- SQLite (local development)
- Django runserver

### Production
- PostgreSQL (with backups)
- Gunicorn WSGI server
- Nginx reverse proxy
- Docker for consistency

### Monitoring
- Log all settlement operations (audit trail)
- Alert on trust score anomalies
- Monitor API response times

---

## 🎯 Phase-Based Implementation

**Phase 1 (Days 1-2):** Core models, auth, basic expense tracking
**Phase 2 (Days 3-4):** Settlement system, balance calculation  
**Phase 3 (Days 5-6):** Trust scoring, testing, documentation

