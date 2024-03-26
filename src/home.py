from flask import Blueprint, render_template
from app import login_required

home = Blueprint('home', __name__, )

@home.route('/home')
@login_required
def home_index():
    return render_template('message.html', title="hi welcome to home", message='hi')