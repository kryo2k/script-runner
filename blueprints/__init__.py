"""Blueprint initializer module. Loads all active blueprint modules."""

from flask import Blueprint, request, send_file
from . import index, kernel
bp = Blueprint("app", __name__)

@bp.route("/favicon.ico", methods=['GET'])
def favicon():
	"""Endpoint to handle favicon.ico image"""
	return send_file('images/favicon.ico')

def init_app(app):
	"""Method to initialize all application modules."""
	app.register_blueprint(bp)
	app.register_blueprint(index.bp)
	app.register_blueprint(kernel.bp)

	@app.context_processor
	def globalvariables():
		blueprint, method = request.url_rule.endpoint.split(sep='.', maxsplit=2)
		return {
			'__blueprint__': blueprint,
			'__method__': method
		}
