# Smart Expense Splitter

**Divide costs, not friendships.**

Smart Expense Splitter is a modern web application designed to take the stress out of group finances. Whether you're traveling with friends, sharing an apartment with roommates, or organizing a group dinner, our platform ensures everyone pays their fair share—on time and without the awkward math.

---

## 🚀 The Problem & Our Solution

**The Problem:** We’ve all been there—trying to remember who paid for the taxi, who covered the Airbnb, and who still owes whom $15. Manual tracking leads to errors, forgotten debts, and uncomfortable conversations.

**Our Solution:** A smart, automated ledger that calculates exactly who needs to pay whom. But we go a step further than other apps: we introduce a **Trust Score** system that rewards reliable payers and helps groups manage financial risks.

---

## 🛠️ How It Works (Step-by-Step)

1.  **Create a Group:** Set up a group for your trip, house, or event (e.g., "Europe 2024" or "The Greenhouse Apartment").
2.  **Invite Members:** Add your friends by their username.
3.  **Log Expenses:** Whenever someone pays for something, log it in the app. You can split it equally or specify exactly who owes what.
4.  **Real-Time Balances:** See an instant summary of your financial standing. The app tells you: *"You are owed $50.00"* or *"You owe $20.00"*.
5.  **Smart Settlement:** When you're ready to pay someone back, record a settlement. The recipient confirms they received the money, and your debt is cleared!
6.  **Build Your Reputation:** Every on-time payment boosts your **Trust Score**, proving you're a reliable member of the group.

---

## ✨ Key Features for Users

### 💡 Smart Debt Simplification
We hate unnecessary transactions. If Alice owes Bob $10, and Bob owes Charlie $10, our system tells Alice to pay Charlie $10 directly. This minimizes the number of transfers your group has to make.

### 🛡️ Trust Analytics
Your **Trust Score** is your financial "credit score" within the app. 
*   **100 Score:** You're a rockstar! You pay back quickly.
*   **Lower Score:** Indicates you might have pending dues or a history of late payments.
*   **Why it matters:** It encourages accountability and helps groups identify who needs a friendly reminder.

### 🔔 Real-Time Notifications
Never miss a beat. You'll get notified when:
*   A new expense is added to your group.
*   Someone sends you a payment.
*   Your Trust Score increases (or decreases).

### 📈 Personal Dashboard
A clean, visual overview of your financial health. Track your net position across all your groups and see your most recent activity at a glance.

---

## 🏗️ The Engineering (For the Geeks)

This isn't just a simple calculator; it's a robust fintech system built with:

*   **Standardized Financial Ledger:** Uses unique `transaction_id` (UUID) for every action to ensure records are never lost or duplicated.
*   **Min-Cash Flow Algorithm:** A greedy matching algorithm that optimizes group settlements.
*   **Time-Decay Trust Logic:** Recent behavior impacts your score more than old data, providing a fair and accurate representation of your current reliability.
*   **Fraud Prevention:** Built-in safeguards against duplicate payments and invalid split amounts.

---

## 🛠️ Technology Stack

*   **Backend:** Django 4.2 & Django REST Framework (Python)
*   **Database:** SQLite / PostgreSQL
*   **Frontend:** Modern Vanilla JavaScript & CSS (No heavy frameworks, just speed)
*   **Authentication:** Secure JWT (JSON Web Tokens)

---

## 🚀 Setup & Installation

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd "Fintech Project"
    ```

2.  **Environment Setup:**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate  # Windows
    source venv/bin/activate # Mac/Linux
    ```

3.  **Install & Run:**
    ```bash
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py runserver
    ```

4.  **Frontend:**
    Open a second terminal:
    ```bash
    cd frontend
    python -m http.server 3000
    ```

Visit: `http://localhost:3000`

---

## 🤝 Contributing
Contributions are welcome! Feel free to fork the repo and submit a pull request.