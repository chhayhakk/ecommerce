import os
from flask import Flask, render_template
from flask_mysqldb import MySQL
from PIL import Image
app = Flask(__name__)
import routes

if __name__ == '__main__':
    app.run()
