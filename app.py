from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from forms import ProductForm, LocationForm, MovementForm
from models import db, Product, Location, ProductMovement
from sqlalchemy import func, and_
from datetime import datetime


from dotenv import load_dotenv
import os

load_dotenv() 

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/products', methods=['GET', 'POST'])
def products():
    form = ProductForm()
    if form.validate_on_submit():
        product = Product(product_id=form.product_id.data)
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('products'))
    
    products = Product.query.all()
    return render_template('products.html', form=form, products=products)

@app.route('/products/<product_id>/edit', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        product.product_id = form.product_id.data
        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('products'))
    return render_template('edit_product.html', form=form, product=product)

@app.route('/locations', methods=['GET', 'POST'])
def locations():
    form = LocationForm()
    if form.validate_on_submit():
        location = Location(location_id=form.location_id.data)
        db.session.add(location)
        db.session.commit()
        flash('Location added successfully!', 'success')
        return redirect(url_for('locations'))
    
    locations = Location.query.all()
    return render_template('locations.html', form=form, locations=locations)

@app.route('/locations/<location_id>/edit', methods=['GET', 'POST'])
def edit_location(location_id):
    location = Location.query.get_or_404(location_id)
    form = LocationForm(obj=location)
    if form.validate_on_submit():
        location.location_id = form.location_id.data
        db.session.commit()
        flash('Location updated successfully!', 'success')
        return redirect(url_for('locations'))
    return render_template('edit_location.html', form=form, location=location)


@app.route('/movements', methods=['GET', 'POST'])
def movements():
    form = MovementForm()
    # Update form choices with current products and locations
    form.product_id.choices = [(p.product_id, p.product_id) for p in Product.query.all()]
    form.from_location.choices = [('', '')] + [(l.location_id, l.location_id) for l in Location.query.all()]
    form.to_location.choices = [('', '')] + [(l.location_id, l.location_id) for l in Location.query.all()]
    
    if form.validate_on_submit():
        product_id = form.product_id.data
        from_loc = form.from_location.data if form.from_location.data != '' else None
        to_loc = form.to_location.data if form.to_location.data != '' else None
        qty = form.qty.data

        # Validate stock availability when moving from a location
        if from_loc:
            # Calculate current stock in source location
            incoming = db.session.query(func.coalesce(func.sum(ProductMovement.qty), 0)) \
                .filter(ProductMovement.product_id == product_id) \
                .filter(ProductMovement.to_location == from_loc) \
                .scalar() or 0

            outgoing = db.session.query(func.coalesce(func.sum(ProductMovement.qty), 0)) \
                .filter(ProductMovement.product_id == product_id) \
                .filter(ProductMovement.from_location == from_loc) \
                .scalar() or 0

            available_stock = incoming - outgoing

            if available_stock < qty:
                flash(f'Error: Only {available_stock} units available in {from_loc}. Cannot move {qty} units.', 'danger')
                return redirect(url_for('movements'))

 
        movement = ProductMovement(
            from_location=from_loc,
            to_location=to_loc,
            product_id=product_id,
            qty=qty,
            timestamp=datetime.utcnow()
        )
        db.session.add(movement)
        db.session.commit()
        flash('Movement recorded successfully!', 'success')
        return redirect(url_for('movements'))
    
    movements = ProductMovement.query.order_by(ProductMovement.timestamp.desc()).all()
    return render_template('movements.html', form=form, movements=movements)

@app.route('/movements/<movement_id>/edit', methods=['GET', 'POST'])
def edit_movement(movement_id):
    movement = ProductMovement.query.get_or_404(movement_id)
    form = MovementForm(obj=movement)
    # Update form choices with current products and locations
    form.product_id.choices = [(p.product_id, p.product_id) for p in Product.query.all()]
    form.from_location.choices = [('', '')] + [(l.location_id, l.location_id) for l in Location.query.all()]
    form.to_location.choices = [('', '')] + [(l.location_id, l.location_id) for l in Location.query.all()]
    
    if form.validate_on_submit():
        # Check stock availability for edits that reduce available quantity
        if movement.from_location and form.qty.data > movement.qty:
            # Calculate how much additional stock would be needed
            additional_needed = form.qty.data - movement.qty
            incoming = db.session.query(func.coalesce(func.sum(ProductMovement.qty), 0)) \
                .filter(ProductMovement.product_id == movement.product_id) \
                .filter(ProductMovement.to_location == movement.from_location) \
                .scalar() or 0

            outgoing = db.session.query(func.coalesce(func.sum(ProductMovement.qty), 0)) \
                .filter(ProductMovement.product_id == movement.product_id) \
                .filter(ProductMovement.from_location == movement.from_location) \
                .scalar() or 0

            available_stock = incoming - outgoing

            if available_stock < additional_needed:
                flash(f'Error: Only {available_stock} additional units available in {movement.from_location}.', 'danger')
                return redirect(url_for('edit_movement', movement_id=movement_id))

        movement.from_location = form.from_location.data if form.from_location.data != '' else None
        movement.to_location = form.to_location.data if form.to_location.data != '' else None
        movement.product_id = form.product_id.data
        movement.qty = form.qty.data
        db.session.commit()
        flash('Movement updated successfully!', 'success')
        return redirect(url_for('movements'))
    return render_template('edit_movement.html', form=form, movement=movement)


@app.route('/report')
def report():
    
    products = Product.query.all()
    locations = Location.query.all()
    
    balances = []
    
    for product in products:
        for location in locations:
         
            incoming = db.session.query(func.coalesce(func.sum(ProductMovement.qty), 0)) \
                .filter(ProductMovement.product_id == product.product_id) \
                .filter(ProductMovement.to_location == location.location_id) \
                .scalar() or 0
            
          
            outgoing = db.session.query(func.coalesce(func.sum(ProductMovement.qty), 0)) \
                .filter(ProductMovement.product_id == product.product_id) \
                .filter(ProductMovement.from_location == location.location_id) \
                .scalar() or 0
            
            balance = incoming - outgoing
            if balance > 0:
                balances.append((product.product_id, location.location_id, balance))
    
    return render_template('report.html', balances=balances)

if __name__ == '__main__':
    app.run(debug=True)
