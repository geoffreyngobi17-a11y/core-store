class SaleForm(FlaskForm):
    item_type = SelectField('Item Type', choices=[('product','Product'),('service','Service')], validators=[DataRequired()])
    product_id = SelectField('Product', coerce=int, choices=[], validators=[Optional()])
    service_id = SelectField('Service', coerce=int, choices=[], validators=[Optional()])
    quantity = IntegerField('Quantity', default=1, validators=[NumberRange(min=1)])
    customer_name = StringField('Customer Name (optional)', validators=[Optional(), Length(max=100)])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Record Sale')