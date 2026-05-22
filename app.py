import os, secrets
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from sqlalchemy import func, desc
from dotenv import load_dotenv

load_dotenv()
from models import db, User, Product, Service, AuditLog, Customer, RepairJob, Invoice, Sale
from forms import (LoginForm, ProductForm, ServiceForm, EmployeeForm, StockAdjustForm,
                   ChangePasswordForm, CustomerForm, RepairJobForm, RepairJobUpdateForm)
from backup_utils import backup_database_to_drive

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

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

def generate_invoice_number(job_id):
    return f"INV-{job_id}-{datetime.utcnow().strftime('%Y%m%d%H%M')}"

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            db.session.add(AuditLog(user_id=user.id, action='Login', details=f'{user.email} logged in'))
            db.session.commit()
            return redirect(url_for('dashboard'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    db.session.add(AuditLog(user_id=current_user.id, action='Logout', details=f'{current_user.email} logged out'))
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
    pending_jobs = RepairJob.query.filter_by(status='pending').count()
    in_progress_jobs = RepairJob.query.filter_by(status='in_progress').count()
    completed_today = RepairJob.query.filter(RepairJob.status=='completed', func.date(RepairJob.completion_date)==func.current_date()).count()
    recent_logs = AuditLog.query.order_by(desc(AuditLog.timestamp)).limit(10).all()
    return render_template('dashboard.html',
                          total_products=total_products, total_value=total_value,
                          low_stock=low_stock, total_services=total_services,
                          pending_jobs=pending_jobs, in_progress_jobs=in_progress_jobs,
                          completed_today=completed_today, recent_logs=recent_logs)

@app.route('/change_password', methods=['GET','POST'])
@login_required
def change_password():
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

@app.route('/inventory')
@login_required
def inventory():
    products = Product.query.order_by(Product.name).all()
    return render_template('inventory.html', products=products)

@app.route('/inventory/add', methods=['GET','POST'])
@login_required
def add_product():
    if current_user.role != 'admin':
        flash('Only admin can add new products.', 'warning')
        return redirect(url_for('inventory'))
    form = ProductForm()
    if form.validate_on_submit():
        product = Product(name=form.name.data, category=form.category.data,
                          quantity=form.quantity.data, unit_price=form.unit_price.data,
                          low_stock_threshold=form.low_stock_threshold.data)
        db.session.add(product)
        db.session.commit()
        db.session.add(AuditLog(user_id=current_user.id, action='Add Product', details=f'Added product: {product.name}'))
        db.session.commit()
        flash('Product added successfully.', 'success')
        return redirect(url_for('inventory'))
    return render_template('product_form.html', form=form, title='Add Product')

@app.route('/inventory/edit/<int:id>', methods=['GET','POST'])
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    if current_user.role not in ['admin','employee']:
        flash('Permission denied.', 'danger')
        return redirect(url_for('inventory'))
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        product.name = form.name.data
        product.category = form.category.data
        product.unit_price = form.unit_price.data
        product.low_stock_threshold = form.low_stock_threshold.data
        db.session.commit()
        db.session.add(AuditLog(user_id=current_user.id, action='Edit Product', details=f'Edited product: {product.name}'))
        db.session.commit()
        flash('Product updated.', 'success')
        return redirect(url_for('inventory'))
    return render_template('product_form.html', form=form, title='Edit Product')

@app.route('/inventory/stock/<int:id>', methods=['GET','POST'])
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
        db.session.add(AuditLog(user_id=current_user.id, action='Stock Adjust', details=f'{details} (old: {old_qty}, new: {product.quantity})'))
        db.session.commit()
        flash('Stock updated.', 'success')
        return redirect(url_for('inventory'))
    return render_template('stock_form.html', form=form, product=product)

@app.route('/inventory/delete/<int:id>')
@admin_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    db.session.add(AuditLog(user_id=current_user.id, action='Delete Product', details=f'Deleted product: {product.name}'))
    db.session.commit()
    flash('Product deleted.', 'success')
    return redirect(url_for('inventory'))

@app.route('/services')
@login_required
def services():
    services = Service.query.order_by(Service.name).all()
    return render_template('services.html', services=services)

@app.route('/services/add', methods=['GET','POST'])
@admin_required
def add_service():
    form = ServiceForm()
    if form.validate_on_submit():
        service = Service(name=form.name.data, description=form.description.data,
                          price=form.price.data, estimated_days=form.estimated_days.data)
        db.session.add(service)
        db.session.commit()
        db.session.add(AuditLog(user_id=current_user.id, action='Add Service', details=f'Added service: {service.name}'))
        db.session.commit()
        flash('Service added.', 'success')
        return redirect(url_for('services'))
    return render_template('service_form.html', form=form, title='Add Service')

@app.route('/services/edit/<int:id>', methods=['GET','POST'])
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
        db.session.add(AuditLog(user_id=current_user.id, action='Edit Service', details=f'Edited service: {service.name}'))
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
    db.session.add(AuditLog(user_id=current_user.id, action='Delete Service', details=f'Deleted service: {service.name}'))
    db.session.commit()
    flash('Service deleted.', 'success')
    return redirect(url_for('services'))

@app.route('/employees')
@admin_required
def employees():
    users = User.query.all()
    return render_template('employees.html', users=users)

@app.route('/employees/add', methods=['GET','POST'])
@admin_required
def add_employee():
    form = EmployeeForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('add_employee'))
        user = User(name=form.name.data, email=form.email.data, phone=form.phone.data, role='employee')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        db.session.add(AuditLog(user_id=current_user.id, action='Add Employee', details=f'Added employee: {user.name}'))
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
    db.session.add(AuditLog(user_id=current_user.id, action='Delete Employee', details=f'Deleted employee: {user.name}'))
    db.session.commit()
    flash('Employee deleted.', 'success')
    return redirect(url_for('employees'))

@app.route('/customers')
@login_required
def customers():
    all_customers = Customer.query.order_by(Customer.name).all()
    return render_template('customers.html', customers=all_customers)

@app.route('/customers/add', methods=['GET','POST'])
@login_required
def add_customer():
    form = CustomerForm()
    if form.validate_on_submit():
        customer = Customer(name=form.name.data, phone=form.phone.data, email=form.email.data, address=form.address.data)
        db.session.add(customer)
        db.session.commit()
        flash('Customer added.', 'success')
        return redirect(url_for('customers'))
    return render_template('customer_form.html', form=form, title='Add Customer')

@app.route('/repair_jobs')
@login_required
def repair_jobs():
    if current_user.role == 'technician':
        jobs = RepairJob.query.filter_by(assigned_to=current_user.id).order_by(RepairJob.received_date.desc()).all()
    else:
        jobs = RepairJob.query.order_by(RepairJob.received_date.desc()).all()
    return render_template('repair_jobs.html', jobs=jobs)

@app.route('/repair_jobs/add', methods=['GET','POST'])
@login_required
def add_repair_job():
    if current_user.role not in ['admin','employee']:
        flash('Permission denied.', 'danger')
        return redirect(url_for('repair_jobs'))
    form = RepairJobForm()
    form.customer_id.choices = [(c.id, f"{c.name} - {c.phone}") for c in Customer.query.all()]
    form.customer_id.choices.insert(0, (0, '-- Select Customer --'))
    form.service_id.choices = [(0, '-- None --')] + [(s.id, s.name) for s in Service.query.all()]
    techs = User.query.filter(User.role.in_(['admin','technician'])).all()
    form.assigned_to.choices = [(0, '-- Unassigned --')] + [(t.id, t.name) for t in techs]
    if form.validate_on_submit():
        job = RepairJob(
            customer_id=form.customer_id.data,
            device_type=form.device_type.data,
            device_model=form.device_model.data,
            issue_description=form.issue_description.data,
            service_id=form.service_id.data if form.service_id.data != 0 else None,
            assigned_to=form.assigned_to.data if form.assigned_to.data != 0 else None,
            estimated_cost=form.estimated_cost.data,
            notes=form.notes.data
        )
        db.session.add(job)
        db.session.commit()
        db.session.add(AuditLog(user_id=current_user.id, action='Create Repair Job', details=f'Job for customer {job.customer.name}'))
        db.session.commit()
        flash('Repair job created.', 'success')
        return redirect(url_for('repair_jobs'))
    return render_template('repair_job_form.html', form=form, title='New Repair Job')

@app.route('/repair_jobs/<int:id>', methods=['GET','POST'])
@login_required
def repair_job_detail(id):
    job = RepairJob.query.get_or_404(id)
    if current_user.role not in ['admin','employee'] and job.assigned_to != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('repair_jobs'))
    form = RepairJobUpdateForm()
    if form.validate_on_submit():
        old_status = job.status
        job.status = form.status.data
        if form.final_cost.data:
            job.final_cost = form.final_cost.data
        if form.completion_date.data:
            try:
                job.completion_date = datetime.strptime(form.completion_date.data, '%Y-%m-%d')
            except:
                pass
        job.notes = form.notes.data
        db.session.commit()
        if job.status == 'completed' and old_status != 'completed':
            if not hasattr(job, 'invoice') or job.invoice is None:
                total = job.final_cost if job.final_cost else (job.estimated_cost if job.estimated_cost else 0)
                invoice = Invoice(repair_job_id=job.id, invoice_number=generate_invoice_number(job.id),
                                  subtotal=total, total=total, paid=False)
                db.session.add(invoice)
                db.session.commit()
                flash('Invoice created for this repair.', 'success')
        db.session.add(AuditLog(user_id=current_user.id, action='Update Repair Job', details=f'Job #{job.id} status: {job.status}'))
        db.session.commit()
        flash('Job updated.', 'success')
        return redirect(url_for('repair_jobs'))
    else:
        form.status.data = job.status
        form.final_cost.data = job.final_cost
        form.notes.data = job.notes
        if job.completion_date:
            form.completion_date.data = job.completion_date.strftime('%Y-%m-%d')
    return render_template('repair_job_detail.html', job=job, form=form)

@app.route('/invoices')
@admin_required
def invoices():
    all_invoices = Invoice.query.order_by(Invoice.issue_date.desc()).all()
    return render_template('invoices.html', invoices=all_invoices)

@app.route('/invoices/<int:invoice_id>/pay', methods=['POST'])
@login_required
def mark_invoice_paid(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    if current_user.role not in ['admin','employee']:
        abort(403)
    invoice.paid = True
    invoice.payment_date = datetime.utcnow()
    db.session.commit()
    db.session.add(AuditLog(user_id=current_user.id, action='Mark Invoice Paid', details=f'Invoice {invoice.invoice_number}'))
    db.session.commit()
    flash(f'Invoice {invoice.invoice_number} marked as paid.', 'success')
    return redirect(url_for('repair_job_detail', id=invoice.repair_job_id))

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

with app.app_context():
    db.create_all()
    if not User.query.filter_by(role='admin').first():
        admin = User(name='Admin', email='admin@coreelectronics.com', phone='+256756104402', role='admin')
        admin.set_password('Admin123!')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created: admin@coreelectronics.com / Admin123!")
# TEMPORARY ROUTE – Create missing tables (remove after use)
@app.route('/create-tables')
def create_tables():
    from sqlalchemy import inspect
    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        db.create_all()  # This creates any missing tables
        new_tables = inspector.get_table_names()
        created = set(new_tables) - set(existing_tables)
        return f"Tables created: {created}<br>All tables now: {new_tables}"
@app.route('/sales')
@login_required
def sales_list():
    all_sales = Sale.query.order_by(Sale.sale_date.desc()).all()
    return render_template('sales_list.html', sales=all_sales)

@app.route('/sales/add', methods=['GET','POST'])
@login_required
def add_sale():
    form = SaleForm()
    # Populate product choices
    form.product_id.choices = [(p.id, f"{p.name} (UGX {p.unit_price}) - Stock: {p.quantity}") for p in Product.query.all()]
    form.product_id.choices.insert(0, (0, '-- Select Product --'))
    # Populate service choices
    form.service_id.choices = [(s.id, f"{s.name} (UGX {s.price})") for s in Service.query.all()]
    form.service_id.choices.insert(0, (0, '-- Select Service --'))
    
    if form.validate_on_submit():
        if form.item_type.data == 'product':
            product = Product.query.get(form.product_id.data)
            if not product:
                flash('Product not found.', 'danger')
                return redirect(url_for('add_sale'))
            if product.quantity < form.quantity.data:
                flash(f'Not enough stock. Only {product.quantity} available.', 'danger')
                return redirect(url_for('add_sale'))
            # Reduce stock
            product.quantity -= form.quantity.data
            db.session.commit()
            total = product.unit_price * form.quantity.data
            sale = Sale(
                item_type='product',
                item_id=product.id,
                item_name=product.name,
                quantity=form.quantity.data,
                unit_price=product.unit_price,
                total_price=total,
                customer_name=form.customer_name.data,
                sold_by=current_user.id,
                notes=form.notes.data
            )
        else:  # service
            service = Service.query.get(form.service_id.data)
            if not service:
                flash('Service not found.', 'danger')
                return redirect(url_for('add_sale'))
            total = service.price * form.quantity.data
            sale = Sale(
                item_type='service',
                item_id=service.id,
                item_name=service.name,
                quantity=form.quantity.data,
                unit_price=service.price,
                total_price=total,
                customer_name=form.customer_name.data,
                sold_by=current_user.id,
                notes=form.notes.data
            )
        db.session.add(sale)
        db.session.commit()
        flash('Sale recorded successfully.', 'success')
        return redirect(url_for('sales_list'))
    return render_template('sale_form.html', form=form)
@app.route('/fix-tables')
def fix_tables():
    from sqlalchemy import inspect, text
    with app.app_context():
        inspector = inspect(db.engine)
        existing = set(inspector.get_table_names())
        required = {'users', 'products', 'services', 'customers', 'repair_jobs', 'invoices', 'sales', 'audit_logs'}
        missing = required - existing
        db.create_all()  # creates all missing tables
        # Also ensure foreign keys are correct (optional)
        db.session.execute(text('ALTER TABLE repair_jobs DROP CONSTRAINT IF EXISTS repair_jobs_assigned_to_fkey;'))
        db.session.execute(text('ALTER TABLE repair_jobs ADD FOREIGN KEY (assigned_to) REFERENCES users(id);'))
        db.session.commit()
        return f"Missing tables created: {missing}<br>All tables now: {inspector.get_table_names()}"
@app.route('/fix-invoices')
def fix_invoices():
    with app.app_context():
        # Drop the invoices table if it exists
        from models import Invoice
        db.session.execute("DROP TABLE IF EXISTS invoices CASCADE")
        db.session.commit()
        # Recreate all tables (or just invoices)
        db.create_all()
        return "Invoices table recreated. Go back and try again."
@app.route('/rebuild-tables')
def rebuild_tables():
    from sqlalchemy import inspect
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
        print("Admin user created: admin@coreelectronics.com / Admin123!")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)