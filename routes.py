from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
from app import app, db
from models import Employee, Account, Expense, WeeklyReport
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract
import os
import zipfile
import tempfile
import shutil

@app.route('/')
def index():
    """Dashboard with key metrics"""
    # Get current week data
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    # Calculate metrics
    total_employees = Employee.query.filter_by(is_active=True).count()
    
    # This week's accounts
    weekly_accounts = Account.query.filter(
        Account.date_created >= week_start,
        Account.date_created <= week_end
    ).all()
    
    total_accounts_this_week = len(weekly_accounts)
    good_accounts_this_week = sum(1 for acc in weekly_accounts if acc.is_good)
    
    # Revenue and payments
    weekly_revenue = good_accounts_this_week * 1400  # 1400 KSH per good account
    weekly_employee_payments = total_accounts_this_week * 500  # 500 KSH per account
    
    # Weekly expenses
    weekly_expenses = db.session.query(func.sum(Expense.amount)).filter(
        Expense.date_incurred >= week_start,
        Expense.date_incurred <= week_end
    ).scalar() or 0
    
    # Net profit
    net_profit = weekly_revenue - weekly_employee_payments - weekly_expenses
    
    # Recent activities
    recent_accounts = Account.query.order_by(Account.created_at.desc()).limit(5).all()
    recent_expenses = Expense.query.order_by(Expense.created_at.desc()).limit(5).all()
    
    return render_template('index.html',
                         total_employees=total_employees,
                         total_accounts_this_week=total_accounts_this_week,
                         good_accounts_this_week=good_accounts_this_week,
                         weekly_revenue=weekly_revenue,
                         weekly_employee_payments=weekly_employee_payments,
                         weekly_expenses=weekly_expenses,
                         net_profit=net_profit,
                         recent_accounts=recent_accounts,
                         recent_expenses=recent_expenses)

@app.route('/employees')
def employees():
    """List all employees"""
    employees = Employee.query.filter_by(is_active=True).all()
    return render_template('employees.html', employees=employees)

@app.route('/employees/add', methods=['GET', 'POST'])
def add_employee():
    """Add new employee"""
    if request.method == 'POST':
        employee = Employee(
            name=request.form['name'],
            email=request.form['email'],
            phone=request.form.get('phone', ''),
            department=request.form.get('department', ''),
            hire_date=datetime.strptime(request.form['hire_date'], '%Y-%m-%d').date() if request.form.get('hire_date') else date.today()
        )
        
        try:
            db.session.add(employee)
            db.session.commit()
            flash('Employee added successfully!', 'success')
            return redirect(url_for('employees'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding employee. Email might already exist.', 'error')
    
    return render_template('add_employee.html')

@app.route('/employees/<int:employee_id>/edit', methods=['GET', 'POST'])
def edit_employee(employee_id):
    """Edit employee details"""
    employee = Employee.query.get_or_404(employee_id)
    
    if request.method == 'POST':
        employee.name = request.form['name']
        employee.email = request.form['email']
        employee.phone = request.form.get('phone', '')
        employee.department = request.form.get('department', '')
        if request.form.get('hire_date'):
            employee.hire_date = datetime.strptime(request.form['hire_date'], '%Y-%m-%d').date()
        
        try:
            db.session.commit()
            flash('Employee updated successfully!', 'success')
            return redirect(url_for('employees'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating employee.', 'error')
    
    return render_template('edit_employee.html', employee=employee)

@app.route('/employees/<int:employee_id>/deactivate', methods=['POST'])
def deactivate_employee(employee_id):
    """Deactivate an employee"""
    employee = Employee.query.get_or_404(employee_id)
    employee.is_active = False
    
    try:
        db.session.commit()
        flash('Employee deactivated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deactivating employee.', 'error')
    
    return redirect(url_for('employees'))

@app.route('/accounts')
def accounts():
    """List all accounts with filtering"""
    page = request.args.get('page', 1, type=int)
    employee_id = request.args.get('employee_id', type=int)
    week_start = request.args.get('week_start')
    
    query = Account.query
    
    # Filter by employee
    if employee_id:
        query = query.filter_by(employee_id=employee_id)
    
    # Filter by week
    if week_start:
        start_date = datetime.strptime(week_start, '%Y-%m-%d').date()
        end_date = start_date + timedelta(days=6)
        query = query.filter(Account.date_created >= start_date, Account.date_created <= end_date)
    
    accounts = query.order_by(Account.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    employees = Employee.query.filter_by(is_active=True).all()
    
    return render_template('accounts.html', accounts=accounts, employees=employees,
                         selected_employee_id=employee_id, selected_week=week_start)

@app.route('/accounts/add', methods=['GET', 'POST'])
def add_accounts():
    """Add accounts for employees"""
    if request.method == 'POST':
        employee_id = request.form['employee_id']
        account_names = request.form.getlist('account_names')
        account_emails = request.form.getlist('account_emails')
        account_numbers = request.form.getlist('account_numbers')
        account_notes = request.form.getlist('account_notes')
        
        # Get status for each account
        account_statuses = []
        for i in range(len(account_names)):
            status_key = f'account_status_{i}'
            status = request.form.get(status_key, 'pending')
            account_statuses.append(status)
        
        success_count = 0
        for i, account_name in enumerate(account_names):
            if account_name.strip():
                # Get corresponding data for this account
                email = account_emails[i] if i < len(account_emails) else ''
                number = account_numbers[i] if i < len(account_numbers) else f'ACC{i+1:03d}'
                notes = account_notes[i] if i < len(account_notes) else ''
                status = account_statuses[i] if i < len(account_statuses) else 'pending'
                
                # Determine if account is good (only 'good' status counts as revenue)
                is_good = (status == 'good')
                
                account = Account(
                    employee_id=employee_id,
                    account_number=number or f'ACC{success_count+1:03d}',
                    client_name=account_name.strip(),
                    client_email=email.strip() if email else None,
                    is_good=is_good,
                    notes=notes,
                    date_created=datetime.strptime(request.form['date_created'], '%Y-%m-%d').date() if request.form.get('date_created') else date.today()
                )
                
                try:
                    db.session.add(account)
                    success_count += 1
                except Exception as e:
                    app.logger.error(f"Error adding account: {e}")
        
        try:
            db.session.commit()
            flash(f'{success_count} accounts added successfully!', 'success')
            return redirect(url_for('accounts'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding accounts.', 'error')
    
    employees = Employee.query.filter_by(is_active=True).all()
    return render_template('add_accounts.html', employees=employees)

@app.route('/expenses')
def expenses():
    """List all expenses"""
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category')
    
    query = Expense.query
    
    if category:
        query = query.filter_by(category=category)
    
    expenses = query.order_by(Expense.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get unique categories
    categories = db.session.query(Expense.category).distinct().all()
    categories = [cat[0] for cat in categories]
    
    return render_template('expenses.html', expenses=expenses, categories=categories,
                         selected_category=category)

@app.route('/expenses/add', methods=['GET', 'POST'])
def add_expense():
    """Add new expense"""
    if request.method == 'POST':
        expense = Expense(
            description=request.form['description'],
            amount=float(request.form['amount']),
            category=request.form['category'],
            date_incurred=datetime.strptime(request.form['date_incurred'], '%Y-%m-%d').date() if request.form.get('date_incurred') else date.today()
        )
        
        try:
            db.session.add(expense)
            db.session.commit()
            flash('Expense added successfully!', 'success')
            return redirect(url_for('expenses'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding expense.', 'error')
    
    return render_template('add_expense.html')

@app.route('/reports')
def reports():
    """Financial reports and analytics"""
    # Get date range from query params
    weeks_back = request.args.get('weeks', 4, type=int)
    
    # Calculate weekly data for the past N weeks
    today = date.today()
    weekly_data = []
    
    for i in range(weeks_back):
        week_start = today - timedelta(days=today.weekday() + (i * 7))
        week_end = week_start + timedelta(days=6)
        
        # Get accounts for this week
        weekly_accounts = Account.query.filter(
            Account.date_created >= week_start,
            Account.date_created <= week_end
        ).all()
        
        total_accounts = len(weekly_accounts)
        good_accounts = sum(1 for acc in weekly_accounts if acc.is_good)
        
        # Calculate financials
        revenue = good_accounts * 1400
        employee_payments = total_accounts * 500
        
        # Get expenses for this week
        weekly_expenses = db.session.query(func.sum(Expense.amount)).filter(
            Expense.date_incurred >= week_start,
            Expense.date_incurred <= week_end
        ).scalar() or 0
        
        net_profit = revenue - employee_payments - weekly_expenses
        
        weekly_data.append({
            'week_start': week_start,
            'week_end': week_end,
            'total_accounts': total_accounts,
            'good_accounts': good_accounts,
            'revenue': revenue,
            'employee_payments': employee_payments,
            'expenses': weekly_expenses,
            'net_profit': net_profit
        })
    
    # Reverse to show oldest first
    weekly_data.reverse()
    
    # Employee performance data
    employees = Employee.query.filter_by(is_active=True).all()
    employee_performance = []
    
    current_week_start = today - timedelta(days=today.weekday())
    
    for employee in employees:
        accounts = employee.get_weekly_accounts(current_week_start)
        good_accounts = employee.get_good_accounts_count(current_week_start)
        payment = employee.get_total_payment(current_week_start)
        
        employee_performance.append({
            'employee': employee,
            'total_accounts': len(accounts),
            'good_accounts': good_accounts,
            'payment': payment
        })
    
    return render_template('reports.html', 
                         weekly_data=weekly_data,
                         employee_performance=employee_performance,
                         weeks_back=weeks_back)

@app.route('/api/dashboard-data')
def dashboard_data():
    """API endpoint for dashboard charts"""
    # Get last 4 weeks of data
    today = date.today()
    weeks_data = []
    
    for i in range(4):
        week_start = today - timedelta(days=today.weekday() + (i * 7))
        week_end = week_start + timedelta(days=6)
        
        weekly_accounts = Account.query.filter(
            Account.date_created >= week_start,
            Account.date_created <= week_end
        ).all()
        
        total_accounts = len(weekly_accounts)
        good_accounts = sum(1 for acc in weekly_accounts if acc.is_good)
        revenue = good_accounts * 1400
        payments = total_accounts * 500
        
        weekly_expenses = db.session.query(func.sum(Expense.amount)).filter(
            Expense.date_incurred >= week_start,
            Expense.date_incurred <= week_end
        ).scalar() or 0
        
        weeks_data.append({
            'week': week_start.strftime('%b %d'),
            'revenue': revenue,
            'payments': payments,
            'expenses': weekly_expenses,
            'profit': revenue - payments - weekly_expenses
        })
    
    weeks_data.reverse()
    return jsonify(weeks_data)

@app.route('/download-project')
def download_project():
    """Download the entire project as a ZIP file"""
    try:
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, 'company-management-system.zip')
        
        # Get current working directory (project root)
        project_root = os.getcwd()
        
        # Files and directories to exclude from the ZIP
        exclude_patterns = {
            '.git', '__pycache__', '.pytest_cache', 'node_modules', 
            '.env', 'venv', '.venv', '.pythonlibs', '.upm', '.cache',
            '*.pyc', '*.pyo', '*.pyd', '.DS_Store', '.replit.nix'
        }
        
        # Create ZIP file
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(project_root):
                # Remove excluded directories from dirs list
                dirs[:] = [d for d in dirs if not any(d == pattern or d.startswith('.') for pattern in exclude_patterns)]
                
                for file in files:
                    # Skip excluded files
                    if any(file.endswith(pattern.replace('*', '')) or file == pattern for pattern in exclude_patterns):
                        continue
                    
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, project_root)
                    
                    # Skip if file is in excluded directory
                    if any(part.startswith('.') and part not in {'.replit'} for part in arc_path.split(os.sep)):
                        continue
                    
                    zipf.write(file_path, arc_path)
            
            # Add the comprehensive setup guide
            with open('LOCAL_SETUP_GUIDE.md', 'r') as f:
                setup_guide = f.read()
            
            zipf.writestr('LOCAL_SETUP_GUIDE.md', setup_guide)
            
            # Add a quick install script for Windows
            install_script_win = """@echo off
echo Setting up Company Management System...
echo.
echo Creating virtual environment...
python -m venv venv
echo.
echo Activating virtual environment...
call venv\\Scripts\\activate
echo.
echo Installing dependencies...
pip install flask flask-sqlalchemy psycopg2-binary gunicorn werkzeug email-validator sqlalchemy
echo.
echo Setup complete! 
echo.
echo To run the application:
echo 1. Run: venv\\Scripts\\activate
echo 2. Run: python main.py
echo 3. Open browser to http://localhost:5000
echo.
pause
"""
            
            # Add a quick install script for Mac/Linux  
            install_script_unix = """#!/bin/bash
echo "Setting up Company Management System..."
echo
echo "Creating virtual environment..."
python3 -m venv venv
echo
echo "Activating virtual environment..."
source venv/bin/activate
echo
echo "Installing dependencies..."
pip install flask flask-sqlalchemy psycopg2-binary gunicorn werkzeug email-validator sqlalchemy
echo
echo "Setup complete!"
echo
echo "To run the application:"
echo "1. Run: source venv/bin/activate"
echo "2. Run: python main.py"  
echo "3. Open browser to http://localhost:5000"
echo
"""
            
            zipf.writestr('setup_windows.bat', install_script_win)
            zipf.writestr('setup_unix.sh', install_script_unix)
        
        # Send the file
        return send_file(
            zip_path,
            as_attachment=True,
            download_name='company-management-system.zip',
            mimetype='application/zip'
        )
        
    except Exception as e:
        app.logger.error(f"Error creating project download: {e}")
        flash('Error creating download. Please try again.', 'error')
        return redirect(url_for('index'))
