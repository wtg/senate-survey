from flask import Blueprint, render_template
from app import login_required

surveys = Blueprint('surveys', __name__, url_prefix='/surveys')

@surveys.route('/')
@login_required
def home_index():
    return render_template('message.html', title="Home Page", message='hi')