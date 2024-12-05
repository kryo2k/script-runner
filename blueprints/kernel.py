"""Informational blueprint for displaying kernel internals."""

from flask import Blueprint, render_template
from ..extensions import auth

bp = Blueprint("app_kernel", __name__, url_prefix="/kernel")

@bp.route("/")
@auth.login_required
def index():
	"""Kernel UI index."""
	return render_template('kernel/index.html')
