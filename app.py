import os
from flask import Flask, render_template
from flask_mysqldb import MySQL
app = Flask(__name__)
import routes
# @app.route('/')
# def hello_world():  # put application's code here
#     return 'Hello World!'


if __name__ == '__main__':
    app.run()
