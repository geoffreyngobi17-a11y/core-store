class Expense(db.Model):
    __tablename__ = 'expenses'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    amount = db.Column(db.Numeric(10,2), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='expenses')
__table_args__ = {'extend_existing': True} right after __tablename__):