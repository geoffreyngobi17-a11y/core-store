 from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, IntegerField, DecimalField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, EqualTo
class ExpenseForm(FlaskForm):
    date = StringField('Date (YYYY-MM-DD)', validators=[DataRequired()])
    amount = DecimalField('Amount (UGX)', validators=[DataRequired()], places=2)
    category = SelectField('Category', choices=[
        ('Rent', 'Rent'), ('Utilities', 'Utilities'), ('Transport', 'Transport'),
        ('Supplies', 'Supplies'), ('Salary', 'Salary'), ('Repair Parts', 'Repair Parts'),
        ('Marketing', 'Marketing'), ('Other', 'Other')
    ], validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Record Expense')