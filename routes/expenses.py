
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import get_db
from forms import ExpenseForm, ApproveExpenseForm
from datetime import datetime

expenses_bp = Blueprint('expenses', __name__)

# Only finance can add expenses
def role_required(allowed_roles):
	from functools import wraps
	def wrapper(fn):
		@wraps(fn)
		def decorated(*args, **kwargs):
			if not current_user.is_authenticated or current_user.role not in allowed_roles:
				flash("Access denied!", "danger")
				return redirect(url_for("auth.login"))
			return fn(*args, **kwargs)
		return decorated
	return wrapper

# Approve expenses (for pastor)
@expenses_bp.route('/expenses/approve', methods=['GET', 'POST'])
@login_required
@role_required(['pastor'])
def approve_expenses():
	db = get_db()
	form = ApproveExpenseForm()
	if request.method == 'POST' and form.validate_on_submit():
		expense_id = request.form.get('expense_id')
		if expense_id:
			db.execute('UPDATE expenses SET approved=1, approved_by=? WHERE id=?', (current_user.name, expense_id))
			db.commit()
			flash(f'Expense approved by {current_user.name}.', 'success')
		return redirect(url_for('expenses.approve_expenses'))
	expenses = db.execute('SELECT id, date, service_type, category, amount, payment_method, description, paid_by, approved_by FROM expenses WHERE approved=0').fetchall()
	return render_template('expenses.html', expenses=expenses, form=form)

@expenses_bp.route('/expenses/add', methods=['GET', 'POST'])
@login_required
@role_required(['finance'])
def add_expense():
	form = ExpenseForm()
	if form.validate_on_submit():
		db = get_db()
		# Ensure service_type is always set (required for per-service balance)
		service_type = form.service_type.data.strip().lower() if form.service_type.data else ''
		if not service_type:
			flash("Service Type is required for expense entry.", "danger")
			return render_template('add_expense.html', form=form)
		db.execute(
			"INSERT INTO expenses (date, service_type, category, amount, payment_method, description, paid_by, approved) VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
			(
				form.date.data,
				service_type,
				form.category.data,
				form.amount.data,
				form.payment_method.data,
				form.description.data,
				current_user.name
			)
		)
		db.commit()
		flash("Expense added and pending approval.", "success")
		return redirect(url_for('dashboard.view_dashboard'))
	return render_template('add_expense.html', form=form)
