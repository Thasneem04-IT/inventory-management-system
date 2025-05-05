from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField
from wtforms.validators import DataRequired, NumberRange

class ProductForm(FlaskForm):
    product_id = StringField('Enter Product', validators=[DataRequired()])

class LocationForm(FlaskForm):
    location_id = StringField('Enter Location', validators=[DataRequired()])

class MovementForm(FlaskForm):
    product_id = SelectField('Product', coerce=str, validators=[DataRequired()])
    from_location = SelectField('From Location', coerce=str)
    to_location = SelectField('To Location', coerce=str)
    qty = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])