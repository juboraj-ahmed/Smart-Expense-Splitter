# Smart Expense Splitter - Database Schema

## 📋 Table Definitions

### 1. **User Table**
```sql
CREATE TABLE "user" (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,  -- bcrypt hash
    first_name VARCHAR(150),
    last_name VARCHAR(150),
    trust_score INT DEFAULT 100 CHECK (trust_score >= 0 AND trust_score <= 100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Indexes
CREATE INDEX idx_user_email ON user(email);
CREATE INDEX idx_user_username ON user(username);
```

**Explanation:**
- `username`: Unique identifier shown to users (can be email-like)
- `password_hash`: Never store plain text! Django uses PBKDF2 by default
- `trust_score`: Denormalized for performance, updated on payment events
- `is_active`: Soft delete support (user can deactivate account)

---

### 2. **Group Table**
```sql
CREATE TABLE "group" (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_by_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (created_by_id) REFERENCES user(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_group_created_by ON group(created_by_id);
```

**Explanation:**
- `created_by_id`: Tracks who created the group (useful for future admin features)
- No "owner" field: group members can have roles (managed via Membership)
- Soft delete not needed here (groups stay for audit trail)

---

### 3. **Membership Table**
```sql
CREATE TABLE membership (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    group_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    role VARCHAR(50) DEFAULT 'member',  -- 'admin', 'member'
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (group_id) REFERENCES "group"(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE,
    
    UNIQUE KEY unique_membership (group_id, user_id),
    CHECK (role IN ('admin', 'member'))
);

-- Indexes (CRITICAL for most queries)
CREATE INDEX idx_membership_group_user ON membership(group_id, user_id);
CREATE INDEX idx_membership_user ON membership(user_id);
CREATE INDEX idx_membership_group ON membership(group_id);
```

**Explanation:**
- `unique_membership`: Ensures a user isn't added twice to same group
- Composite index `(group_id, user_id)`: Essential for queries like "who are the members?"
- `LEFT JOIN` to membership to find user's groups

---

### 4. **Expense Table**
```sql
CREATE TABLE expense (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    group_id BIGINT NOT NULL,
    paid_by_id BIGINT NOT NULL,
    amount DECIMAL(12, 2) NOT NULL CHECK (amount > 0),
    description VARCHAR(500),
    category VARCHAR(100),  -- 'food', 'transport', 'accommodation', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (group_id) REFERENCES "group"(id) ON DELETE CASCADE,
    FOREIGN KEY (paid_by_id) REFERENCES "user"(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_expense_group ON expense(group_id);
CREATE INDEX idx_expense_paid_by ON expense(paid_by_id);
CREATE INDEX idx_expense_created_at ON expense(created_at);
CREATE INDEX idx_expense_group_date ON expense(group_id, created_at);
```

**Explanation:**
- `amount`: Must be positive, stored as DECIMAL (not float!) for financial accuracy
- `category`: Optional field for future analytics/insights
- `paid_by_id`: FK to user (who paid)
- No "settled" flag: Settlement is recorded in Payment table instead

---

### 5. **Split Table**
```sql
CREATE TABLE split (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    expense_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    amount DECIMAL(12, 2) NOT NULL CHECK (amount >= 0),
    
    FOREIGN KEY (expense_id) REFERENCES expense(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE,
    
    UNIQUE KEY unique_split (expense_id, user_id)
);

-- Indexes (Essential for balance queries)
CREATE INDEX idx_split_user ON split(user_id);
CREATE INDEX idx_split_expense ON split(expense_id);
CREATE INDEX idx_split_user_expense ON split(user_id, expense_id);
```

**Explanation:**
- `unique_split`: A user can't appear twice in same expense splits
- This is where "who owes what" is recorded
- To calculate balance: SELECT SUM(amount) FROM split WHERE user_id = X AND expense_id IN (...)

**Important Invariant (enforced in application):**
```
For each expense:
  SUM(split.amount WHERE expense_id = X) == expense.amount
```

---

### 6. **Payment Table**
```sql
CREATE TABLE payment (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    from_user_id BIGINT NOT NULL,
    to_user_id BIGINT NOT NULL,
    group_id BIGINT NOT NULL,
    amount DECIMAL(12, 2) NOT NULL CHECK (amount > 0),
    description VARCHAR(500),  -- e.g., "Settlement for pizza lunch"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (from_user_id) REFERENCES "user"(id) ON DELETE CASCADE,
    FOREIGN KEY (to_user_id) REFERENCES "user"(id) ON DELETE CASCADE,
    FOREIGN KEY (group_id) REFERENCES "group"(id) ON DELETE CASCADE,
    
    CHECK (from_user_id != to_user_id)  -- Can't pay yourself
);

-- Indexes
CREATE INDEX idx_payment_from ON payment(from_user_id);
CREATE INDEX idx_payment_to ON payment(to_user_id);
CREATE INDEX idx_payment_group ON payment(group_id);
CREATE INDEX idx_payment_created_at ON payment(created_at);
CREATE INDEX idx_payment_from_to_group ON payment(from_user_id, to_user_id, group_id);
```

**Explanation:**
- `from_user_id` → `to_user_id`: Directional settlement
- `CHECK (from_user_id != to_user_id)`: Prevents self-payment nonsense
- Maintaining audit trail: payments are **immutable** (never deleted/updated)
- Used to calculate "who settled what" for trust score

---

## 🔗 Relationships Explained

### Cascade Delete Strategy

```
Group deleted 
  → All Membership records deleted
  → All Expense records in group deleted
    → All Split records for those expenses deleted
  → All Payment records in group deleted

User deleted (CAREFUL!)
  → Keep Payment history (audit trail)
  → Soft-delete instead (is_active = FALSE)
```

**Rationale:** Financial records should be immutable for compliance.

---

## 📊 Key Queries & Optimization

### Query 1: Get user's groups
```sql
SELECT g.* FROM "group" g
JOIN membership m ON g.id = m.group_id
WHERE m.user_id = ?
-- Uses: idx_membership_user
```

### Query 2: Get group members
```sql
SELECT u.* FROM "user" u
JOIN membership m ON u.id = m.user_id
WHERE m.group_id = ?
-- Uses: idx_membership_group_user
```

### Query 3: Calculate user's balance in a group
```sql
-- Total paid by user
SELECT COALESCE(SUM(e.amount), 0) 
FROM expense e
WHERE e.group_id = ? AND e.paid_by_id = ?

-- Total user owes (from splits)
SELECT COALESCE(SUM(s.amount), 0)
FROM split s
JOIN expense e ON s.expense_id = e.id
WHERE e.group_id = ? AND s.user_id = ?

-- Minus settlements (payments received)
SELECT COALESCE(SUM(p.amount), 0)
FROM payment p
WHERE p.group_id = ? AND p.to_user_id = ? 
  AND p.from_user_id = <other_user>

-- Net balance = paid - owes + received
```

---

## ⚠️ Integrity Constraints

### 1. Financial Constraints
- ✅ `amount > 0` on Expense, Payment
- ✅ `amount >= 0` on Split (can be zero)
- ✅ `trust_score BETWEEN 0 AND 100`

### 2. Logical Constraints
- ✅ `from_user_id != to_user_id` on Payment
- ✅ Unique (group_id, user_id) on Membership
- ✅ Unique (expense_id, user_id) on Split

### 3. Application-Level Validation (Not in DB)
- Sum of splits equals expense amount
- User is member of group before creating expense
- Cannot settle amount greater than actual balance

---

## 🗂️ Django Models (ORM Mapping)

```python
# Models will implement:
- User (builtin Django User extended)
- Group
- Membership
- Expense
- Split
- Payment
```

See MODELS_AND_SERIALIZERS.md for full Django code.

---

## 📈 Analytics Queries (Future)

```sql
-- User spending by category (last 30 days)
SELECT e.category, SUM(s.amount)
FROM split s
JOIN expense e ON s.expense_id = e.id
WHERE s.user_id = ? AND e.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY e.category
ORDER BY SUM(s.amount) DESC;

-- Most frequent expense partners
SELECT p.to_user_id, COUNT(*) as transaction_count
FROM payment p
WHERE p.from_user_id = ? 
GROUP BY p.to_user_id
ORDER BY transaction_count DESC
LIMIT 5;
```

---

## 🚀 Migration Strategy

### Phase 1 (Initial)
- Create base tables: User, Group, Membership
- Add basic indexes

### Phase 2 (After testing)
- Create Expense, Split tables
- Add composite indexes

### Phase 3 (Settlement)
- Create Payment table
- Add trust_score field to User

**Why phases?** Easier to rollback if something breaks, and mirrors development workflow.

