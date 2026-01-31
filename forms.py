
# Simple form for CSRF only (for approve action)
from flask_wtf import FlaskForm
class ApproveExpenseForm(FlaskForm):
    pass

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email
from datetime import date

# Form for admin clear data action
class ClearDataForm(FlaskForm):
    delete_attendance = BooleanField('Attendance')
    delete_giving = BooleanField('Giving')
    delete_expenses = BooleanField('Expenses')
    filter_date = StringField('Date (YYYY-MM-DD)')
    filter_service_type = StringField('Service Type')
    submit = SubmitField('Delete Selected Data')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class AttendanceForm(FlaskForm):
    date = StringField('Date', validators=[DataRequired()])
    service_type = StringField('Service Type', validators=[DataRequired()])
    male = StringField('Male', validators=[])  # will parse to int in route
    female = StringField('Female', validators=[])
    children = StringField('Children', validators=[])
    submit = SubmitField('Save Attendance')



class GivingForm(FlaskForm):
    date = StringField('Date', default=date.today().strftime('%Y-%m-%d'), validators=[DataRequired()])
    service_type = StringField('Service Type', validators=[DataRequired()])
    tithe = StringField('Tithe', validators=[])
    offering = StringField('Offering', validators=[])
    special = StringField('Special', validators=[])
    submit = SubmitField('Save Giving')

# Expense form for finance
from wtforms import FloatField, SelectField, TextAreaField

class ExpenseForm(FlaskForm):
    date = StringField('Date', default=date.today().strftime('%Y-%m-%d'), validators=[DataRequired()])
    service_type = StringField('Service Type', validators=[DataRequired()])
    category = StringField('Category', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    payment_method = SelectField('Payment Method', choices=[('cash','Cash'),('transfer','Transfer'),('cheque','Cheque')], validators=[DataRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Add Expense')
