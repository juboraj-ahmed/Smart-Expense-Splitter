# Smart Expense Splitter - Trust Score Algorithm

## 🎯 Overview

The Trust Score is a **behavioral metric** that predicts financial reliability based on payment patterns. It's shown in user profiles and helps group members assess risk when splitting expenses.

**Range:** 0-100 (higher is better)

---

## 📐 Core Formula

```
Base Score = 100

Penalties (applied)
- Late Payment Penalty: -5 per late payment
- Pending Overdue Penalty: -2 per 7 days overdue
- High Debt Ratio Penalty: -15 if pending > 75% of monthly income
- Absence of Activity Bonus: +5 if no pending (never defaults)

Bonuses (applied)
- Consistent Payer Bonus: +3 if 100% on-time for last 5 payments
- Early Payment Bonus: +2 if paid early/settled early (5+ times)
- Settling Risk Bonus: +1 per 10 settlements in total history

Final Score = CLAMP(Base Score - Penalties + Bonuses, 0, 100)
```

---

## 🔍 Detailed Scoring Breakdown

### 1. **Late Payment Penalty**

**Definition:** A payment is late if settled > 7 days after expense created.

**Calculation:**
```python
def calculate_late_payment_penalty():
    late_payments = Payment.objects.filter(
        user=current_user,
        created_at - Expense.created_at > timedelta(days=7)
    ).count()
    
    return late_payments * 5  # Each late payment costs 5 points
```

**Examples:**
- 0 late payments → 0 penalty
- 1 late payment → -5 points
- 2 late payments → -10 points (but max total penalty is capped)

**Why this metric?**
- Direct indicator of reliability
- Observable and verifiable
- Recent behavior weighted more (see time decay below)

---

### 2. **Pending Overdue Penalty**

**Definition:** Expenses that haven't been settled beyond their natural due date.

**Calculation:**
```python
def calculate_pending_overdue_penalty():
    pending_expenses = Split.objects.filter(
        user=current_user,
        expense__created_at__lt=now() - timedelta(days=14)
    ).exclude(
        payment__exists=True  # Already settled
    )
    
    total_overdue_days = 0
    for split in pending_expenses:
        days_overdue = (now() - split.expense.created_at).days
        total_overdue_days += days_overdue
    
    # Penalty for every 7 days overdue
    penalty = (total_overdue_days // 7) * 2
    return min(penalty, 30)  # Cap at -30
```

**Examples:**
- $100 pending for 8 days → -2 points
- $100 pending for 30 days → -8 points
- $500 pending for 60 days → -30 points (capped)

**Why this metric?**
- Shows current financial health
- Measures unresolved obligations
- More recent issues have higher impact

---

### 3. **High Debt Ratio Penalty**

**Definition:** If user has excessive pending amount relative to their paying history.

**Calculation:**
```python
def calculate_high_debt_ratio_penalty():
    # Calculate user's monthly spending average
    last_30_days_expenses = Expense.objects.filter(
        created_at__gte=now() - timedelta(days=30),
        paid_by=current_user
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    monthly_avg = last_30_days_expenses / 4
    
    # Total pending amount
    pending_amount = Split.objects.filter(
        user=current_user
    ).exclude(payment__exists=True).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    debt_ratio = pending_amount / monthly_avg if monthly_avg > 0 else 0
    
    if debt_ratio > 0.75:  # If pending > 75% of monthly average
        return -15  # Significant penalty
    elif debt_ratio > 0.50:
        return -10
    elif debt_ratio > 0.25:
        return -5
    else:
        return 0
```

**Examples:**
- Pending $100, monthly avg $400 → ratio 0.25 → no penalty
- Pending $250, monthly avg $400 → ratio 0.625 → -10 points
- Pending $400, monthly avg $400 → ratio 1.0 → -15 points

**Why this metric?**
- Prevents false positives (new users will have temporary pending)
- Compares to user's spending capacity
- Detects financial distress early

---

### 4. **Bonuses**

#### 4a) Absence of Activity Bonus
```python
def calculate_absence_bonus():
    # User who never defaults gets credit
    total_pending = Split.objects.filter(
        user=current_user
    ).exclude(payment__exists=True).count()
    
    if total_pending == 0 and user_has_activity:
        return +5
    return 0
```

#### 4b) Consistent Payer Bonus
```python
def calculate_consistent_payer_bonus():
    # Last 5 payments - were they all on time?
    recent_payments = Payment.objects.filter(
        from_user=current_user
    ).order_by('-created_at')[:5]
    
    on_time_count = sum(1 for p in recent_payments if is_on_time(p))
    
    if on_time_count == 5:
        return +3
    elif on_time_count >= 3:
        return +1
    return 0
```

#### 4c) Early Payment Bonus
```python
def calculate_early_payment_bonus():
    # Settled before expected completion date?
    early_payments = 0
    for payment in Payment.objects.filter(from_user=current_user):
        days_to_settle = (payment.created_at - payment.expense.created_at).days
        if days_to_settle < 7:  # Settled within a week
            early_payments += 1
    
    # 1 point per 10 early payments (max 5 points)
    return min(early_payments // 10, 5)
```

---

## ⏰ Time Decay (Recency Weighting)

Older behavior should matter less. Apply exponential decay:

```python
def apply_time_decay(payment_date, metric_value):
    """
    Recent actions worth more than old actions.
    Decay factor: 0.99^(days_old)
    """
    days_old = (now() - payment_date).days
    decay_factor = 0.99 ** days_old
    return metric_value * decay_factor
```

**Example:**
- Payment made today: 100% weight
- Payment made 30 days ago: 74% weight
- Payment made 90 days ago: 41% weight
- Payment made 180 days ago: 16% weight

**Why?** Recent behavior is more predictive of future behavior.

---

## 🔄 Update Frequency

### Real-Time Updates (Immediate)
- When user settles a payment
- When they create an expense they pay for

### Batch Updates (Nightly, ~2 AM)
- Recalculate all users' scores
- Reason: Catches drifting overdue amounts
- Catches users hitting thresholds

**Django Implementation:**
```python
# In Celery beat config or cron job
from celery.schedules import crontab

app.conf.beat_schedule = {
    'update-trust-scores': {
        'task': 'expenses.tasks.recalculate_all_trust_scores',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
}
```

---

## 📊 Score Interpretation

| Score | Status | Meaning |
|-------|--------|---------|
| 95-100 | ⭐⭐⭐⭐⭐ Excellent | Reliable payer, always on-time, no issues |
| 80-94 | ⭐⭐⭐⭐ Good | Generally reliable, occasional delays |
| 60-79 | ⭐⭐⭐ Fair | Some payment issues, unpredictable |
| 40-59 | ⭐⭐ Poor | Frequent delays, managing debt poorly |
| 0-39 | ⭐ Very Poor | Unreliable, multiple defaults, high risk |

---

## 🛡️ Edge Cases & Safeguards

### Case 1: Brand New User (No History)
```python
if user.created_at > now() - timedelta(days=30):
    return 100 - 20  # Start with 80 to prevent gaming
```
**Reasoning:** Give benefit of doubt but assume less history.

### Case 2: User With No Expenses
```python
if user.total_expenses_count == 0:
    return 100
```
**Reasoning:** Can't penalize someone with no history.

### Case 3: Settling Exact Amount
```python
if settled_amount == expected_amount:
    bonus += 1  # Accurate settlement
```
**Reasoning:** Precise payers are more trustworthy.

### Case 4: Settling More Than Owed
```python
# THIS IS IMPOSSIBLE - API prevents oversettlement
if settled_amount > expected_amount:
    raise ValidationError("Cannot settle more than owed")
```

### Case 5: Multiple Groups
```python
# Score is GLOBAL, not per-group
# User's reliability should be consistent across all groups
def get_trust_score(user):
    # Consider ALL their payments across ALL groups
    all_payments = Payment.objects.filter(from_user=user)
    all_splits = Split.objects.filter(user=user)
    # Calculate unified score
```
**Reasoning:** An unreliable person in one group is unreliable everywhere.

---

## 💾 Database Schema for Trust Score

### Add to User Model
```sql
ALTER TABLE "user" ADD COLUMN (
    trust_score INT DEFAULT 100,
    trust_score_updated_at TIMESTAMP,
    total_payments INT DEFAULT 0,
    on_time_payments INT DEFAULT 0,
    total_settled_amount DECIMAL(12, 2) DEFAULT 0
);

CREATE INDEX idx_user_trust_score ON user(trust_score DESC);
```

### Audit Log (Optional but recommended)
```sql
CREATE TABLE trust_score_audit (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT,
    old_score INT,
    new_score INT,
    reason VARCHAR(255),
    computed_at TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES user(id)
);

CREATE INDEX idx_audit_user_date ON trust_score_audit(user_id, computed_at DESC);
```

**Purpose:** Debugging and transparency. Users can see why their score changed.

---

## 🚀 Implementation Strategy

### Phase 1 (MVP)
- Base score: 100
- Late payment penalty: -5 per occurrence
- Pending overdue penalty: -2 per 7 days
- Update on payment settlement (real-time)

### Phase 2 (Enhancement)
- Add debt ratio penalty
- Add consistency bonuses
- Add time decay
- Implement nightly batch updates

### Phase 3 (Advanced)
- Machine learning model to predict default risk
- Integration with credit bureaus (future)
- Per-group trust adjustments

---

## 📈 Example: Calculating Alice's Score

**Alice's History:**
- Created 3/1: Group dinner $30 (Alice paid)
- Alice's split: $15 (paid 3/10 - 9 days late)
- Created 3/5: Rent $600 (split 4 ways)
- Alice's split: $150 (paid 3/12 - 7 days, on time)
- Created 3/10: Movie $20
- Alice's split: $10 (NOT YET PAID - 15 days overdue)

**Calculation (as of 3/26):**

```
Base Score: 100

Late Payment Penalty:
- Payment 1 (3/10): 9 days late → -5

Pending Overdue Penalty:
- Payment, 3: 15 days overdue → (15/7) * 2 = -4

Bonuses:
- Consistent Payer: Last 1 payment on time → not enough for bonus
- Early Payment Bonus: 0

High Debt Ratio:
- Monthly avg (last 30 days): $90 (avg of 150+30+20)
- Pending: $10
- Ratio: 0.11 → no penalty

Time decay: 
- Most recent lateness was 16 days ago, decay = 0.99^16 = 0.85
- Apply to late penalty: -5 * 0.85 = -4.25

Final Score:
100 - 4.25 - 4 = 91.75 ≈ 92 (rounded)
```

**Interpretation:** Alice is a good payer but has one overdue amount and was late once recently. Score reflects caution.

---

## 🔐 Security Considerations

### 1. Score Manipulation Prevention
```python
# User cannot directly modify score
# Score is read-only, computed from transactions
# Transactions are immutable (cannot be deleted)
```

### 2. Fake Settlements Prevention
```python
# Require both users to verify large settlements?
# Option: SMS verification for settlements > $100
# Track settlement patterns for fraud
```

### 3. Privacy
```python
# Users see their own detailed breakdown
# Other users see only: name, score, trust_level
# Not shown: individual payment history
```

---

## 📝 API Response Example

```json
GET /users/1/trust-score/

{
  "user_id": 1,
  "current_score": 92,
  "breakdown": {
    "base": 100,
    "late_payment_penalty": -5,
    "pending_overdue_penalty": -4,
    "high_debt_penalty": 0,
    "absence_bonus": 0,
    "consistency_bonus": 0,
    "early_payment_bonus": 0
  },
  "metrics": {
    "total_payments_made": 12,
    "on_time_payments": 11,
    "late_payments": 1,
    "avg_days_late": 3.5,
    "current_pending_amount": 10.00,
    "current_pending_days": 15,
    "total_settled": 1250.00
  },
  "history": [
    {
      "date": "2025-03-26",
      "score": 92,
      "reason": "Overdue payment detected"
    },
    {
      "date": "2025-03-12",
      "score": 95,
      "reason": "On-time payment recorded"
    }
  ]
}
```

---

## 🎓 Key Takeaways

1. **Trust Score is behavioral** - reflects actual payment patterns
2. **Transparent calculation** - users understand why their score is what it is
3. **Incentivizes good behavior** - bonuses reward consistency
4. **Prevents gaming** - multiple safeguards against manipulation
5. **Scalable computation** - can be calculated efficiently at scale
6. **Actionable insights** - group members can make informed decisions

