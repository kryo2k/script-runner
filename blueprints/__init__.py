import os
from flask import Blueprint, request, send_file, render_template
from . import index, kernel
from ..extensions import auth
bp = Blueprint("app", __name__)

@bp.route("/favicon.ico", methods=['GET'])
def favicon():
	return send_file('images/favicon.ico')

def init_app(app):
	app.register_blueprint(bp)
	app.register_blueprint(index.bp)
	app.register_blueprint(kernel.bp)

	@app.context_processor
	def globalvariables():
		blueprint, method = request.url_rule.endpoint.split(sep='.', maxsplit=2)

		return dict(
			__blueprint__=blueprint,
			__method__=method
		)
