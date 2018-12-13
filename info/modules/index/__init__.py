from flask import Blueprint

views_blu = Blueprint("index", __name__)

from .views import *
