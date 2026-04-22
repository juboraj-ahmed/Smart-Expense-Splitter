# Smart Expense Splitter with Trust Score

A fintech-inspired group expense management system that enables users to split costs, track balances, and evaluate financial reliability through a dynamic trust scoring mechanism.

---

## Problem Statement

Managing shared expenses in groups (friends, roommates, trips) often leads to:

* Lack of transparency in who owes whom
* Delayed or missed payments
* No accountability for financial behavior

This project solves these issues by combining **expense tracking** with a **behavior-based trust scoring system**, introducing a layer of financial reliability analysis.

---

## Key Features

* 🔐 JWT-based user authentication
* 👥 Group creation and member management
* 💸 Expense splitting (equal distribution)
* 📊 Real-time balance calculation (who owes whom)
* 🔁 Settlement system with confirmation flow
* 📜 Chronological transaction timeline
* 🧠 **Trust Score System** based on repayment behavior
* 💱 Multi-currency support (USD, BDT)

---

## Trust Score System (Core Innovation)

Each user is assigned a dynamic trust score that reflects their financial behavior.

### Factors considered:

* Payment delays
* Pending dues
* Frequency of settlements

### Example logic:

Trust Score = 100 - (late_payments × 5) - (pending_dues × 2)

This introduces a **behavioral fintech layer**, allowing the system to identify:

* Reliable users
* High-risk defaulters
* Group-level financial patterns

---

## System Architecture

Client → REST API (Django DRF) → Business Logic Layer → Database

### Core Components:

* **Authentication Service** (JWT-based)
* **Group & Membership Module**
* **Expense & Split Engine**
* **Settlement & Transaction Handler**
* **Trust Score Engine**

---

## Technology Stack

* **Backend:** Django 4.2, Django REST Framework
* **Database:** SQLite (Development), PostgreSQL (Production-ready)
* **Frontend:** Vanilla HTML, JavaScript, CSS
* **Tools:** Git, Postman

---

## Data Integrity & Reliability

To simulate real-world financial systems, the application ensures:

* ✅ Atomic transaction handling for settlements
* ✅ Prevention of invalid states (e.g., negative balances)
* ✅ Consistent balance updates across users
* ✅ Input validation and error handling

---

## API Overview

### Authentication

* `POST /api/v1/auth/register/`
* `POST /api/v1/auth/login/`

### Groups

* `POST /api/v1/groups/`
* `GET /api/v1/groups/`

### Expenses

* `POST /api/v1/expenses/`
* `GET /api/v1/expenses/`

### Settlements

* `POST /api/v1/settlements/`
* `GET /api/v1/settlements/`

---

## Setup Instructions

1. Clone the repository:

   ```bash
   git clone <your-repo-link>
   cd Smart-Splitter
   ```

2. Create and activate virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run migrations:

   ```bash
   python manage.py migrate
   ```

5. Create superuser:

   ```bash
   python manage.py createsuperuser
   ```

6. Run backend:

   ```bash
   python manage.py runserver
   ```

7. Run frontend:

   ```bash
   cd frontend
   python -m http.server 3000
   ```

App runs at: http://localhost:3000

---

## Future Improvements

* AI-based payment delay prediction (risk scoring)
* Advanced analytics dashboard
* Notification system for pending dues
* Mobile-friendly frontend

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Submit a pull request

---

## Project Positioning

This project demonstrates:

* Backend system design for financial applications
* Transaction consistency and data integrity
* Behavioral analysis through trust scoring
* Practical understanding of fintech workflows

---