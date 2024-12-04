import os
from flask import Blueprint, send_file, render_template
from ..extensions import auth

bp = Blueprint("app_kernel", __name__, url_prefix="/kernel")

@bp.route("/")
@auth.login_required
def index():
	return render_template('kernel/index.html')