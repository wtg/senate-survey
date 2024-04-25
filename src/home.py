from flask import Blueprint, render_template
from app import login_required

home = Blueprint('home', __name__, url_prefix='/home')

@home.route('/')
@login_required
def home_index():
    return render_template('home.html')