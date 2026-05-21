import os
import secrets
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from sqlalchemy import func, desc
from dotenv import load_dotenv

load_dotenv()

from models import db, User, Product, Service, AuditLog
from forms import LoginForm, ProductForm, ServiceForm, EmployeeForm, StockAdjustForm
from backup_utils import backup_database_to_drive

app = Flask(__name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            audit = AuditLog(user_id=user.id, action='Login', details=f'{user.email} logged in')
            db.session.add(audit)
            db.session.commit()
            return redirect(url_for('dashboard'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    audit = AuditLog(user_id=current_user.id, action='Logout', details=f'{current_user.email} logged out')
    db.session.add(audit)
    db.session.commit()
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    total_products = db.session.query(func.sum(Product.quantity)).scalar() or 0
    total_value = db.session.query(func.sum(Product.quantity * Product.unit_price)).scalar() or 0
    low_stock = Product.query.filter(Product.quantity <= Product.low_stock_threshold).count()
    total_services = Service.query.count()
    recent_logs = AuditLog.query.order_by(desc(AuditLog.timestamp)).limit(10).all()
    return render_template('dashboard.html',
                          total_products=total_products,
                          total_value=total_value,
                          low_stock=low_stock,
                          total_services=total_services,
                          recent_logs=recent_logs)

@app.route('/inventory')
@login_required
def inventory():
    products = Product.query.order_by(Product.name).all()
    return render_template('inventory.html', products=products)

@app.route('/inventory/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if current_user.role != 'admin':
        flash('Only admin can add new products.', 'warning')
        return redirect(url_for('inventory'))
    form = ProductForm()
    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            category=form.category.data,
            quantity=form.quantity.data,
            unit_price=form.unit_price.data,
            low_stock_threshold=form.low_stock_threshold.data
        )
        db.session.add(product)
        db.session.commit()
        audit = AuditLog(user_id=current_user.id, action='Add Product',
                         details=f'Added product: {product.name} (qty: {product.quantity})')
        db.session.add(audit)
        db.session.commit()
        flash('Product added successfully.', 'success')
        return redirect(url_for('inventory'))
    return render_template('product_form.html', form=form, title='Add Product')

@app.route('/inventory/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    if current_user.role != 'admin' and current_user.role != 'employee':
        flash('Permission denied.', 'danger')
        return redirect(url_for('inventory'))
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        product.name = form.name.data
        product.category = form.category.data
        product.unit_price = form.unit_price.data
        product.low_stock_threshold = form.low_stock_threshold.data
        db.session.commit()
        audit = AuditLog(user_id=current_user.id, action='Edit Product',
                         details=f'Edited product: {product.name}')
        db.session.add(audit)
        db.session.commit()
        flash('Product updated.', 'success')
        return redirect(url_for('inventory'))
    return render_template('product_form.html', form=form, title='Edit Product')

@app.route('/inventory/stock/<int:id>', methods=['GET', 'POST'])
@login_required
def adjust_stock(id):
    product = Product.query.get_or_404(id)
    form = StockAdjustForm()
    if form.validate_on_submit():
        old_qty = product.quantity
        if form.adjust_type.data == 'add':
            product.quantity += form.quantity.data
            details = f'Added {form.quantity.data} units to {product.name}'
        else:
            if product.quantity >= form.quantity.data:
                product.quantity -= form.quantity.data
                details = f'Removed {form.quantity.data} units from {product.name}'
            else:
                flash('Not enough stock!', 'danger')
                return redirect(url_for('inventory'))
        db.session.commit()
        audit = AuditLog(user_id=current_user.id, action='Stock Adjust',
                         details=f'{details} (old: {old_qty}, new: {product.quantity})')
        db.session.add(audit)
        db.session.commit()
        flash('Stock updated.', 'success')
        return redirect(url_for('inventory'))
    return render_template('stock_form.html', form=form, product=product)
class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

@app.route('/inventory/delete/<int:id>')
@admin_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    audit = AuditLog(user_id=current_user.id, action='Delete Product',
                     details=f'Deleted product: {product.name}')
    db.session.add(audit)
    db.session.commit()
    flash('Product deleted.', 'success')
    return redirect(url_for('inventory'))

@app.route('/services')
@login_required
def services():
    services = Service.query.order_by(Service.name).all()
    return render_template('services.html', services=services)

@app.route('/services/add', methods=['GET', 'POST'])
@admin_required
def add_service():
    form = ServiceForm()
    if form.validate_on_submit():
        service = Service(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            estimated_days=form.estimated_days.data
        )
        db.session.add(service)
        db.session.commit()
        audit = AuditLog(user_id=current_user.id, action='Add Service',
                         details=f'Added service: {service.name}')
        db.session.add(audit)
        db.session.commit()
        flash('Service added.', 'success')
        return redirect(url_for('services'))
    return render_template('service_form.html', form=form, title='Add Service')

@app.route('/services/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_service(id):
    service = Service.query.get_or_404(id)
    form = ServiceForm(obj=service)
    if form.validate_on_submit():
        service.name = form.name.data
        service.description = form.description.data
        service.price = form.price.data
        service.estimated_days = form.estimated_days.data
        db.session.commit()
        audit = AuditLog(user_id=current_user.id, action='Edit Service',
                         details=f'Edited service: {service.name}')
        db.session.add(audit)
        db.session.commit()
        flash('Service updated.', 'success')
        return redirect(url_for('services'))
    return render_template('service_form.html', form=form, title='Edit Service')

@app.route('/services/delete/<int:id>')
@admin_required
def delete_service(id):
    service = Service.query.get_or_404(id)
    db.session.delete(service)
    db.session.commit()
    audit = AuditLog(user_id=current_user.id, action='Delete Service',
                     details=f'Deleted service: {service.name}')
    db.session.add(audit)
    db.session.commit()
    flash('Service deleted.', 'success')
    return redirect(url_for('services'))

@app.route('/employees')
@admin_required
def employees():
    users = User.query.all()
    return render_template('employees.html', users=users)

@app.route('/employees/add', methods=['GET', 'POST'])
@admin_required
def add_employee():
    form = EmployeeForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('add_employee'))
        user = User(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            role='employee'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        audit = AuditLog(user_id=current_user.id, action='Add Employee',
                         details=f'Added employee: {user.name} ({user.email})')
        db.session.add(audit)
        db.session.commit()
        flash('Employee added.', 'success')
        return redirect(url_for('employees'))
    return render_template('employee_form.html', form=form, title='Add Employee')

@app.route('/employees/delete/<int:id>')
@admin_required
def delete_employee(id):
    if id == current_user.id:
        flash('You cannot delete yourself.', 'danger')
        return redirect(url_for('employees'))
    user = User.query.get_or_404(id)
    if user.role == 'admin':
        flash('Cannot delete admin.', 'danger')
        return redirect(url_for('employees'))
    db.session.delete(user)
    db.session.commit()
    audit = AuditLog(user_id=current_user.id, action='Delete Employee',
                     details=f'Deleted employee: {user.name}')
    db.session.add(audit)
    db.session.commit()
    flash('Employee deleted.', 'success')
    return redirect(url_for('employees'))

@app.route('/auditlog')
@admin_required
def auditlog():
    logs = AuditLog.query.order_by(desc(AuditLog.timestamp)).all()
    return render_template('auditlog.html', logs=logs)

@app.route('/admin/backup', methods=['POST'])
@login_required
def backup_trigger():
    token = request.args.get('token')
    if token != os.getenv('BACKUP_TOKEN'):
        abort(403)
    try:
        result = backup_database_to_drive()
        if result:
            return "Backup successful", 200
        else:
            return "Backup failed", 500
    except Exception as e:
        app.logger.error(f"Backup error: {e}")
        return "Internal error", 500

# Create database tables and admin user on startup
with app.app_context():
    # This line will create all the tables defined in models.py
    db.create_all()
    print("Tables created (or already exist).")

    # Now, check for and create the admin user
    if not User.query.filter_by(role='admin').first():
        admin = User(
            name='Admin',
            email='admin@coreelectronics.com',
            phone='+256756104402',
            role='admin'
        )
        admin.set_password('Admin123!')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created: admin@coreelectronics.com / Admin123!")
    else:
        print("Admin user already exists.")
if __name__ == '__main__':
@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    from forms import ChangePasswordForm
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('change_password'))
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Password updated. Please log in again.', 'success')
        logout_user()
        return redirect(url_for('login'))
    return render_template('change_password.html', form=form)

# Create tables and admin user inside app context
with app.app_context():
    db.create_all()
    if not User.query.filter_by(role='admin').first():
        admin = User(
            name='Admin',
            email='admin@coreelectronics.com',
            phone='+256756104402',
            role='admin'
        )
        admin.set_password('Admin123!')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created.")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)