from app import app, render_template

@app.route('/user')
def user():
    return render_template("admin/user.html")