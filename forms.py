from flask_wtf import FlaskForm 
from wtforms import StringField, PasswordField, SelectField, IntegerField, DecimalField, TextAreaField, SubmitField 
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional 
 
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
