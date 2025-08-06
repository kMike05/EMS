from app import db
from datetime import datetime, date, timedelta
from sqlalchemy import func

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    department = db.Column(db.String(50))
    hire_date = db.Column(db.Date, default=datetime.utcnow().date())
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to accounts
    accounts = db.relationship('Account', backref='employee', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Employee {self.name}>'
    
    def get_weekly_accounts(self, week_start=None):
        """Get accounts for a specific week"""
        if week_start is None:
            # Get current week
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
        
        week_end = week_start + timedelta(days=6)
        
        return Account.query.filter(
            Account.employee_id == self.id,
            Account.date_created >= week_start,
            Account.date_created <= week_end
        ).all()
    
    def get_total_payment(self, week_start=None):
        """Calculate total payment for employee (500 KSH per account)"""
        accounts = self.get_weekly_accounts(week_start)
        return len(accounts) * 500
    
    def get_good_accounts_count(self, week_start=None):
        """Get count of good accounts for the week"""
        accounts = self.get_weekly_accounts(week_start)
        return sum(1 for account in accounts if account.is_good)

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    account_number = db.Column(db.String(50), nullable=False)
    client_name = db.Column(db.String(100), nullable=False)
    client_email = db.Column(db.String(120))
    is_good = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    date_created = db.Column(db.Date, default=datetime.utcnow().date())
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Account {self.account_number}>'

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date_incurred = db.Column(db.Date, default=datetime.utcnow().date())
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Expense {self.description}: {self.amount} KSH>'

class WeeklyReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    week_start = db.Column(db.Date, nullable=False)
    week_end = db.Column(db.Date, nullable=False)
    total_accounts = db.Column(db.Integer, default=0)
    good_accounts = db.Column(db.Integer, default=0)
    total_revenue = db.Column(db.Float, default=0.0)  # 1400 KSH per good account
    total_employee_payments = db.Column(db.Float, default=0.0)  # 500 KSH per account
    total_expenses = db.Column(db.Float, default=0.0)
    net_profit = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<WeeklyReport {self.week_start} - {self.week_end}>'
