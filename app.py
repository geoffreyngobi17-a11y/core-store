# TEMPORARY ROUTE – creates invoices table directly
@app.route('/init-invoices')
def init_invoices():
    import sqlalchemy as sa
    with app.app_context():
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if 'invoices' not in inspector.get_table_names():
            with db.engine.connect() as conn:
                # Create the table
                conn.execute(text("""
                    CREATE TABLE invoices (
                        id SERIAL PRIMARY KEY,
                        repair_job_id INTEGER NOT NULL UNIQUE,
                        invoice_number VARCHAR(50) NOT NULL UNIQUE,
                        issue_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        due_date TIMESTAMP,
                        subtotal NUMERIC(10,2) NOT NULL,
                        tax NUMERIC(10,2) DEFAULT 0,
                        total NUMERIC(10,2) NOT NULL,
                        paid BOOLEAN DEFAULT FALSE,
                        payment_date TIMESTAMP
                    )
                """))
                # Add foreign key (if repair_jobs table exists)
                conn.execute(text("""
                    ALTER TABLE invoices ADD CONSTRAINT fk_invoices_repair_job
                    FOREIGN KEY (repair_job_id) REFERENCES repair_jobs(id)
                """))
                conn.commit()
            return "✅ Invoices table created. <a href='/invoices'>Go to Invoices</a>"
        else:
            return "✅ Invoices table already exists. <a href='/invoices'>Go to Invoices</a>"

# ROUTE TO CHECK AND FIX THE DATABASE
@app.route('/check-db')
def check_database():
    from sqlalchemy import inspect, text
    from models import Invoice

    messages = []
    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        messages.append(f"✅ **Tables found:** {existing_tables}")

        if 'invoices' not in existing_tables:
            messages.append("⚠️ **'invoices' table not found. Attempting to create it...**")
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("""
                        CREATE TABLE invoices (
                            id SERIAL PRIMARY KEY,
                            repair_job_id INTEGER NOT NULL UNIQUE,
                            invoice_number VARCHAR(50) NOT NULL UNIQUE,
                            issue_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            due_date TIMESTAMP,
                            subtotal NUMERIC(10,2) NOT NULL,
                            tax NUMERIC(10,2) DEFAULT 0,
                            total NUMERIC(10,2) NOT NULL,
                            paid BOOLEAN DEFAULT FALSE,
                            payment_date TIMESTAMP
                        )
                    """))
                    conn.execute(text("""
                        ALTER TABLE invoices ADD CONSTRAINT fk_invoices_repair_job
                        FOREIGN KEY (repair_job_id) REFERENCES repair_jobs(id)
                    """))
                    conn.commit()
                messages.append("✅ **Success! The 'invoices' table has been created.**")
            except Exception as e:
                messages.append(f"❌ **An error occurred:** {e}")
        else:
            messages.append("✅ **The 'invoices' table already exists.**")

        final_tables = inspector.get_table_names()
        messages.append(f"\n**Tables in the database now:** {final_tables}")
        messages.append(f"\n**Go to the [Invoices page](/invoices) to see if it works.**")
        return "<br>".join(messages)

# ---------- Manual invoice generation for completed jobs ----------
@app.route('/repair_jobs/<int:id>/generate-invoice')
@login_required
def generate_invoice(id):
    job = RepairJob.query.get_or_404(id)
    if job.status != 'completed':
        flash('Can only generate invoice for completed jobs.', 'warning')
        return redirect(url_for('repair_job_detail', id=id))
    if hasattr(job, 'invoice') and job.invoice:
        flash('Invoice already exists for this job.', 'info')
        return redirect(url_for('repair_job_detail', id=id))
    total = job.final_cost if job.final_cost else (job.estimated_cost if job.estimated_cost else 0)
    if total == 0:
        flash('Cannot generate invoice: no cost (estimated or final) set.', 'danger')
        return redirect(url_for('repair_job_detail', id=id))
    from models import Invoice
    invoice = Invoice(
        repair_job_id=job.id,
        invoice_number=f"INV-{job.id}-{datetime.utcnow().strftime('%Y%m%d%H%M')}",
        subtotal=total,
        total=total,
        paid=False
    )
    db.session.add(invoice)
    db.session.commit()
    flash('Invoice generated successfully.', 'success')
    return redirect(url_for('repair_job_detail', id=id))

# ---------- Run the app ----------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)