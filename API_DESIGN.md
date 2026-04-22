# Smart Expense Splitter - API Design Guide

## 🎯 API Overview

**Base URL:** `http://localhost:8000/api/v1/`

**Authentication:** JWT Bearer Token
```
Authorization: Bearer <access_token>
```

---

## 🔐 Authentication Endpoints

### 1. **Register User**

```http
POST /auth/register
Content-Type: application/json

{
  "username": "alice",
  "email": "alice@example.com",
  "password": "SecurePass123!",
  "first_name": "Alice",
  "last_name": "Smith"
}
```

**Response: 201 Created**
```json
{
  "user": {
    "id": 1,
    "username": "alice",
    "email": "alice@example.com",
    "first_name": "Alice",
    "trust_score": 100
  },
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response: 400 Bad Request**
```json
{
  "errors": {
    "email": ["This email is already registered."],
    "password": ["Password must be at least 8 characters."]
  }
}
```

**Validation Rules:**
- Username: 3-150 chars, alphanumeric + underscore
- Email: Valid email format, unique
- Password: Min 8 chars, at least 1 uppercase, 1 digit

---

### 2. **Login**

```http
POST /auth/login
Content-Type: application/json

{
  "email": "alice@example.com",
  "password": "SecurePass123!"
}
```

**Response: 200 OK**
```json
{
  "user": {
    "id": 1,
    "username": "alice",
    "email": "alice@example.com",
    "trust_score": 92
  },
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response: 401 Unauthorized**
```json
{
  "error": "Invalid credentials."
}
```

**Token Details:**
- Access token: 24 hours expiration
- Refresh token: 7 days expiration
- Use refresh token to get new access token

---

### 3. **Refresh Token**

```http
POST /auth/token/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response: 200 OK**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

---

## 👥 User Endpoints

### 4. **Get Current User**

```http
GET /users/me
Authorization: Bearer <access_token>
```

**Response: 200 OK**
```json
{
  "id": 1,
  "username": "alice",
  "email": "alice@example.com",
  "first_name": "Alice",
  "last_name": "Smith",
  "trust_score": 92,
  "created_at": "2025-01-15T10:30:00Z"
}
```

---

### 5. **Get User by ID**

```http
GET /users/{id}/
Authorization: Bearer <access_token>
```

**Response: 200 OK**
```json
{
  "id": 2,
  "username": "bob",
  "email": "bob@example.com",
  "first_name": "Bob",
  "trust_score": 85,
  "created_at": "2025-01-10T14:20:00Z"
}
```

**Note:** Users can see each other's trust scores (useful for deciding if trustworthy).

---

## 👫 Group Endpoints

### 6. **Create Group**

```http
POST /groups/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "Summer Vacation 2025",
  "description": "Trip to Bali with friends"
}
```

**Response: 201 Created**
```json
{
  "id": 5,
  "name": "Summer Vacation 2025",
  "description": "Trip to Bali with friends",
  "created_by": {
    "id": 1,
    "username": "alice"
  },
  "members_count": 1,
  "created_at": "2025-04-20T08:00:00Z"
}
```

---

### 7. **List User's Groups**

```http
GET /groups/?search=vacation
Authorization: Bearer <access_token>
```

**Response: 200 OK**
```json
{
  "count": 3,
  "next": "http://localhost:8000/api/v1/groups/?page=2",
  "previous": null,
  "results": [
    {
      "id": 5,
      "name": "Summer Vacation 2025",
      "members_count": 4,
      "your_balance": -150.50,
      "created_at": "2025-04-20T08:00:00Z"
    },
    {
      "id": 3,
      "name": "Roommates",
      "members_count": 2,
      "your_balance": 200.00,
      "created_at": "2025-03-01T10:00:00Z"
    }
  ]
}
```

**Query Parameters:**
- `search`: Filter by group name (optional)
- `page`: Pagination (default: 1)
- `limit`: Results per page (default: 20, max: 100)

**Note:** `your_balance` shows net balance (negative = you owe, positive = you're owed)

---

### 8. **Get Group Details**

```http
GET /groups/{id}/
Authorization: Bearer <access_token>
```

**Response: 200 OK**
```json
{
  "id": 5,
  "name": "Summer Vacation 2025",
  "description": "Trip to Bali with friends",
  "created_by": {
    "id": 1,
    "username": "alice"
  },
  "members": [
    {
      "id": 1,
      "username": "alice",
      "email": "alice@example.com",
      "role": "admin",
      "balance_in_group": -150.50
    },
    {
      "id": 2,
      "username": "bob",
      "role": "member",
      "balance_in_group": 75.00
    }
  ],
  "total_expenses": 850.00,
  "created_at": "2025-04-20T08:00:00Z"
}
```

---

### 9. **Add Member to Group**

```http
POST /groups/{id}/add_member/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "user_id": 3
}
```

**Response: 200 OK**
```json
{
  "message": "User added successfully",
  "member": {
    "id": 3,
    "username": "charlie",
    "role": "member"
  }
}
```

**Response: 400 Bad Request**
```json
{
  "error": "User is already a member of this group."
}
```

---

## 💰 Expense Endpoints

### 10. **Create Expense**

```http
POST /expenses/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "group_id": 5,
  "amount": 300.00,
  "description": "Hotel booking for 2 nights",
  "category": "accommodation",
  "splits": [
    {
      "user_id": 1,
      "amount": 100.00
    },
    {
      "user_id": 2,
      "amount": 100.00
    },
    {
      "user_id": 3,
      "amount": 100.00
    }
  ]
}
```

**Response: 201 Created**
```json
{
  "id": 42,
  "group_id": 5,
  "paid_by": {
    "id": 1,
    "username": "alice"
  },
  "amount": 300.00,
  "description": "Hotel booking for 2 nights",
  "category": "accommodation",
  "splits": [
    {
      "user_id": 1,
      "username": "alice",
      "amount": 100.00
    },
    {
      "user_id": 2,
      "username": "bob",
      "amount": 100.00
    },
    {
      "user_id": 3,
      "username": "charlie",
      "amount": 100.00
    }
  ],
  "created_at": "2025-04-20T10:15:00Z"
}
```

**Response: 400 Bad Request**
```json
{
  "errors": {
    "splits": ["Sum of splits (200.00) must equal expense amount (300.00)"],
    "group_id": ["You are not a member of this group"]
  }
}
```

**Business Rules:**
- User must be member of group
- User is automatically the payer
- Sum of split amounts MUST equal total
- All split users must be group members
- No negative amounts

---

### 11. **Split Expense Equally**

Convenience endpoint for equal splits:

```http
POST /expenses/create_equal_split/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "group_id": 5,
  "amount": 120.00,
  "description": "Pizza dinner",
  "category": "food",
  "participant_ids": [1, 2, 3, 4]
}
```

**Response: 201 Created**
```json
{
  "id": 43,
  "amount": 120.00,
  "splits": [
    {"user_id": 1, "amount": 30.00},
    {"user_id": 2, "amount": 30.00},
    {"user_id": 3, "amount": 30.00},
    {"user_id": 4, "amount": 30.00}
  ],
  "created_at": "2025-04-20T10:30:00Z"
}
```

---

### 12. **List Expenses in Group**

```http
GET /groups/{id}/expenses/?limit=10&offset=0&category=food
Authorization: Bearer <access_token>
```

**Response: 200 OK**
```json
{
  "count": 42,
  "next": "http://localhost:8000/api/v1/groups/5/expenses/?limit=10&offset=10",
  "results": [
    {
      "id": 43,
      "paid_by": {"id": 1, "username": "alice"},
      "amount": 120.00,
      "description": "Pizza dinner",
      "category": "food",
      "created_at": "2025-04-20T10:30:00Z"
    }
  ]
}
```

---

## 💸 Balance & Settlement Endpoints

### 13. **Get Balances in Group**

```http
GET /groups/{id}/balances/
Authorization: Bearer <access_token>
```

**Response: 200 OK**
```json
{
  "group_id": 5,
  "total_expenses": 850.00,
  "balances": [
    {
      "user": {
        "id": 1,
        "username": "alice",
        "trust_score": 92
      },
      "total_paid": 450.00,
      "total_owes": 300.00,
      "net_balance": 150.00  // Positive means owed to them
    },
    {
      "user": {
        "id": 2,
        "username": "bob",
        "trust_score": 85
      },
      "total_paid": 200.00,
      "total_owes": 350.00,
      "net_balance": -150.00  // Negative means they owe
    }
  ]
}
```

**Explanation:**
- `net_balance > 0`: User is owed money (others should pay them)
- `net_balance < 0`: User owes money (they should pay others)
- `net_balance = 0`: Settled up in this group

---

### 14. **Get Balances Between Two Users**

```http
GET /users/{id}/balance_with/{other_user_id}/?group_id=5
Authorization: Bearer <access_token>
```

**Response: 200 OK**
```json
{
  "from_user": {
    "id": 1,
    "username": "alice"
  },
  "to_user": {
    "id": 2,
    "username": "bob"
  },
  "group_id": 5,
  "net_balance": -75.50,  // Alice owes Bob 75.50
  "details": {
    "total_paid_by_alice": 450.00,
    "total_alice_owes": 525.50,
    "settlements_received": 0,
    "settlements_paid": 0
  }
}
```

---

### 15. **Record Settlement (Payment)**

```http
POST /settlements/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "group_id": 5,
  "to_user_id": 2,
  "amount": 75.50,
  "description": "Paying back for hotel"
}
```

**Response: 201 Created**
```json
{
  "id": 18,
  "from_user": {
    "id": 1,
    "username": "alice"
  },
  "to_user": {
    "id": 2,
    "username": "bob"
  },
  "group_id": 5,
  "amount": 75.50,
  "description": "Paying back for hotel",
  "created_at": "2025-04-20T15:45:00Z",
  "updated_balances": {
    "from_user_balance": -50.00,  // Updated
    "to_user_balance": 50.00       // Updated
  }
}
```

**Response: 400 Bad Request**
```json
{
  "errors": {
    "amount": ["You only owe 50.00 in this group, cannot settle 75.50"]
  }
}
```

**Business Rules:**
- Cannot settle more than actual amount owed
- Cannot settle with yourself
- Cannot settle with non-members
- Settlement is recorded atomically

---

### 16. **List Settlements in Group**

```http
GET /groups/{id}/settlements/?limit=10
Authorization: Bearer <access_token>
```

**Response: 200 OK**
```json
{
  "count": 8,
  "results": [
    {
      "id": 18,
      "from_user": {"id": 1, "username": "alice"},
      "to_user": {"id": 2, "username": "bob"},
      "amount": 75.50,
      "description": "Paying back for hotel",
      "created_at": "2025-04-20T15:45:00Z"
    }
  ]
}
```

---

## ⭐ Trust Score Endpoints

### 17. **Get Trust Score**

```http
GET /users/{id}/trust-score/
Authorization: Bearer <access_token>
```

**Response: 200 OK**
```json
{
  "user_id": 1,
  "username": "alice",
  "current_score": 92,
  "previous_score": 95,
  "score_breakdown": {
    "base_score": 100,
    "late_payment_penalty": -5,
    "pending_amount_penalty": 0,
    "on_time_bonus": +3,
    "final_score": 92
  },
  "metrics": {
    "total_payments": 12,
    "on_time_payments": 11,
    "late_payments": 1,
    "avg_days_late": 3,
    "total_pending_amount": 0,
    "pending_since_days": null
  },
  "last_updated": "2025-04-20T15:45:00Z"
}
```

**Interpretation:**
- Score 90+: Excellent payer
- Score 70-89: Good payer
- Score 50-69: Acceptable, but some issues
- Score <50: Unreliable payer (red flag)

---

## 🛡️ Error Handling

### 401 Unauthorized (Missing/Invalid Token)
```json
{
  "error": "Authentication credentials were not provided.",
  "code": "authentication_failed"
}
```

### 403 Forbidden (No Permission)
```json
{
  "error": "You don't have permission to access this group.",
  "code": "permission_denied"
}
```

### 404 Not Found
```json
{
  "error": "Group not found.",
  "code": "not_found"
}
```

### 422 Validation Error
```json
{
  "error": "Validation failed",
  "code": "validation_error",
  "details": {
    "amount": ["Must be greater than 0"],
    "email": ["This email is already registered"]
  }
}
```

### 500 Internal Server Error
```json
{
  "error": "An internal error occurred. Please try again later.",
  "code": "server_error"
}
```

---

## 📊 Pagination

All list endpoints support pagination:

```http
GET /groups/?page=2&limit=20
```

**Response includes:**
```json
{
  "count": 45,
  "next": "http://localhost:8000/api/v1/groups/?page=3&limit=20",
  "previous": "http://localhost:8000/api/v1/groups/?page=1&limit=20",
  "results": [...]
}
```

---

## 🔄 Rate Limiting

API implements rate limiting:
- **Auth endpoints**: 5 requests/minute per IP
- **Regular endpoints**: 100 requests/minute per user
- **Response headers:**
  ```
  X-RateLimit-Limit: 100
  X-RateLimit-Remaining: 87
  X-RateLimit-Reset: 1650462000
  ```

---

## 📝 Handy cURL Examples

**Register:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "email": "alice@example.com",
    "password": "SecurePass123!"
  }'
```

**Login:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "password": "SecurePass123!"
  }'
```

**Create Expense (with token):**
```bash
curl -X POST http://localhost:8000/api/v1/expenses/ \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": 5,
    "amount": 300.00,
    "description": "Hotel",
    "splits": [
      {"user_id": 1, "amount": 100},
      {"user_id": 2, "amount": 100},
      {"user_id": 3, "amount": 100}
    ]
  }'
```

