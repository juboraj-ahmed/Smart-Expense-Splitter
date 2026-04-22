# Smart Expense Splitter

Smart Expense Splitter is a Django-based group expense management application that allows users to share costs, calculate balances, and settle debts with a built-in trust scoring system.

## Features

- User authentication using JWT
- Create and manage expense-sharing groups
- Add expenses and split them equally among members
- View chronological timelines of expenses and settlements
- Record settlement payments and confirm them via notifications
- Automated trust scoring based on payment history and reliability
- Support for multiple currencies (USD, BDT)

## Technology Stack

- **Backend**: Django 4.2, Django REST Framework
- **Database**: SQLite (Development) / PostgreSQL (Production)
- **Frontend**: Vanilla HTML/JS with a modern CSS architecture

## Setup Instructions

1. Clone the repository and navigate to the project directory:
   ```bash
   cd "Smart Splitter"
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the database migrations:
   ```bash
   python manage.py migrate
   ```

5. Create a superuser account for administration:
   ```bash
   python manage.py createsuperuser
   ```

6. Start the backend development server:
   ```bash
   python manage.py runserver
   ```

7. Start the frontend:
   You can serve the frontend directory using any static file server, such as Python's built-in HTTP server:
   ```bash
   cd frontend
   python -m http.server 3000
   ```

The application will be accessible at `http://localhost:3000`.

## API Endpoints

- Authentication: `/api/v1/auth/login/`, `/api/v1/auth/register/`
- Groups: `/api/v1/groups/`
- Expenses: `/api/v1/expenses/`
- Settlements: `/api/v1/settlements/`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request
