from flask import Blueprint, render_template, redirect, url_for, flash, request
from forms import ClearDataForm
from flask_login import login_required, current_user
from models import get_db
from routes.dashboard import role_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/clear-data', methods=['POST'])
@role_required(['admin'])
def clear_data():
    form = ClearDataForm()
    if form.validate_on_submit():
        db = get_db()
        deleted = []
        try:
            date_filter = form.filter_date.data.strip() if form.filter_date.data else None
            service_type_filter = form.filter_service_type.data.strip().lower() if form.filter_service_type.data else None

            if form.delete_attendance.data:
                query = 'DELETE FROM attendance_summary'
                params = []
                if date_filter or service_type_filter:
                    query += ' WHERE 1=1'
                    if date_filter:
                        query += ' AND date=?'
                        params.append(date_filter)
                    if service_type_filter:
                        query += ' AND LOWER(service_type)=?'
                        params.append(service_type_filter)
                db.execute(query, params)
                deleted.append('attendance')

            if form.delete_giving.data:
                query = 'DELETE FROM giving_summary'
                params = []
                if date_filter or service_type_filter:
                    query += ' WHERE 1=1'
                    if date_filter:
                        query += ' AND date=?'
                        params.append(date_filter)
                    if service_type_filter:
                        query += ' AND LOWER(service_type)=?'
                        params.append(service_type_filter)
                db.execute(query, params)
                deleted.append('giving')

            if form.delete_expenses.data:
                query = 'DELETE FROM expenses'
                params = []
                if date_filter or service_type_filter:
                    query += ' WHERE 1=1'
                    if date_filter:
                        query += ' AND date=?'
                        params.append(date_filter)
                    if service_type_filter:
                        query += ' AND LOWER(service_type)=?'
                        params.append(service_type_filter)
                db.execute(query, params)
                deleted.append('expenses')

            db.commit()
            if deleted:
                flash(f"Deleted: {', '.join(deleted).title()}.", 'success')
            else:
                flash('No data type selected for deletion.', 'warning')
        except Exception as e:
            flash('Error clearing data: ' + str(e), 'danger')
    else:
        flash('Invalid form submission.', 'danger')
    return redirect(url_for('dashboard.view_dashboard'))
