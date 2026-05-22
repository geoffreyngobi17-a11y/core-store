from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, IntegerField, DecimalField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, EqualTo

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(max=200)])
    category = SelectField('Category', choices=[('Laptop','Laptop'),('Desktop','Desktop'),('Component','Component'),('Repair Part','Repair Part'),('Accessory','Accessory')], validators=[DataRequired()])
    quantity = IntegerField('Current Quantity', validators=[DataRequired(), NumberRange(min=0)])
    unit_price = DecimalField('Unit Price (UGX)', validators=[DataRequired()], places=2)
    low_stock_threshold = IntegerField('Low Stock Alert at', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Save Product')

class StockAdjustForm(FlaskForm):
    adjust_type = SelectField('Type', choices=[('add','Add Stock'),('remove','Remove Stock')])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Update Stock')

class ServiceForm(FlaskForm):
    name = StringField('Service Name', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    price = DecimalField('Price (UGX)', validators=[DataRequired()], places=2)
    estimated_days = IntegerField('Est. Days', validators=[Optional()])
    submit = SubmitField('Save Service')

class EmployeeForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    password = PasswordField('Temporary Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Add Employee')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

class CustomerForm(FlaskForm):
    name = StringField('Customer Name', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email()])
    address = StringField('Address', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Save Customer')

class RepairJobForm(FlaskForm):
    customer_id = SelectField('Customer', coerce=int, validators=[DataRequired()])
    device_type = SelectField('Device Type', choices=[('Phone','Phone'),('Laptop','Laptop'),('Desktop','Desktop'),('Tablet','Tablet'),('Other','Other')], validators=[DataRequired()])
    device_model = StringField('Device Model', validators=[Optional(), Length(max=100)])
    issue_description = TextAreaField('Issue Description', validators=[DataRequired()])
    service_id = SelectField('Service Type (optional)', coerce=int, validators=[Optional()])
    assigned_to = SelectField('Assign to Technician', coerce=int, validators=[Optional()])
    estimated_cost = DecimalField('Estimated Cost (UGX)', validators=[Optional()], places=2)
    notes = TextAreaField('Internal Notes', validators=[Optional()])
    submit = SubmitField('Create Repair Job')

class RepairJobUpdateForm(FlaskForm):
    status = SelectField('Status', choices=[('pending','Pending'),('in_progress','In Progress'),('completed','Completed'),('cancelled','Cancelled')], validators=[DataRequired()])
    final_cost = DecimalField('Final Cost (UGX)', validators=[Optional()], places=2)
    completion_date = StringField('Completion Date (YYYY-MM-DD)', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Update Job')
class SaleForm(FlaskForm):
    item_type = SelectField('Item Type', choices=[('product','Product'),('service','Service')], validators=[DataRequired()])
    product_id = SelectField('Product', coerce=int, choices=[], validators=[Optional()])
    service_id = SelectField('Service', coerce=int, choices=[], validators=[Optional()])
    quantity = IntegerField('Quantity', default=1, validators=[NumberRange(min=1)])
    customer_name = StringField('Customer Name (optional)', validators=[Optional(), Length(max=100)])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Record Sale')
class SaleForm(FlaskForm):
    item_type = SelectField('Item Type', choices=[('product','Product'),('service','Service')], validators=[DataRequired()])
    product_id = SelectField('Product', coerce=int, choices=[], validators=[Optional()])
    service_id = SelectField('Service', coerce=int, choices=[], validators=[Optional()])
    quantity = IntegerField('Quantity', default=1, validators=[NumberRange(min=1)])
    customer_name = StringField('Customer Name (optional)', validators=[Optional(), Length(max=100)])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Record Sale')
