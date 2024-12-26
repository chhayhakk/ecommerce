import email

from app import app, render_template
from flask import jsonify, request
from routes.dashboard import mysql
from werkzeug.utils import secure_filename
import os
@app.route('/user')
def user():
    return render_template("admin/user.html")


# @app.route('/api/users', methods=['POST'])
# def add_user():
#     try:
#         # Collect JSON data from the request body
#         data = request.get_json()
#
#         # Extract fields from the received JSON
#         code = data.get('code')
#         name = data.get('name')
#         address = data.get('address')
#         role = data.get('role')
#         gender = data.get('gender')
#         password = data.get('password')
#         phone = data.get('phone')
#         email = data.get('email')
#         status = data.get('status')
#
#         # Check if the email already exists
#         cur = mysql.connection.cursor()
#         cur.execute("SELECT * FROM tbl_users WHERE email = %s", (email,))
#         existing_user = cur.fetchone()
#         if existing_user:
#             return jsonify({'error': 'email_exists', 'message': 'Email already exists!'}), 400
#
#         # Handle image upload (if exists)
#         image = request.files.get('image')
#         image_name = None
#         if image:
#             filename = secure_filename(image.filename)
#             image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#             image.save(image_path)
#             image_name = filename
#
#         # Insert new user into the database
#         cur.execute("""
#                     INSERT INTO tbl_users (code, name, profile, address, role, gender, email, phone, password, status)
#                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
#                 """, (code, name, image_name, address, role, gender, email, phone, password, status))
#
#         mysql.connection.commit()
#         new_user_id = cur.lastrowid
#         # Commit the changes
#         cur.close()
#
#         return jsonify({'message': 'User added successfully!', 'id': new_user_id}), 201
#
#     except Exception as e:
#         print(f"Error: {e}")  # Print error for debugging
#         return jsonify({'error': 'Failed to add user', 'details': str(e)}), 400
@app.get('/api/get_user/<int:id>')
def get_user(id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM tbl_users where id = %s", (id,))
        user = cur.fetchone()
        if user:
            return jsonify({'id':user[0],
                            'name':user[3],
                            'email':user[6],
                            'gender': user[4],
                            'phone':user[7],
                            'address':user[8],
                            'profile':user[2],
                            'status': user[10],
                            })
        else:
            return jsonify({'message': 'User not found'}), 404
    except Exception as e:
        print(f"Error: {e}")  # Print error for debugging
        return jsonify({'error': 'user to add product', 'details': str(e)}), 400
def get_user_by_email(email):

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM tbl_users WHERE email = %s", (email,))
    user = cur.fetchone()
    cur.close()
    return user
@app.route('/api/login', methods=['POST'])
def signin():
    data = request.get_json()

    # Get email and password from the request body
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    # Fetch user data from the database based on email
    user = get_user_by_email(email)

    if user:
        # Assuming `user` returns a tuple (id, username, password, etc.)
        user_id = user[0]
        stored_email = user[6]  # Adjust based on your database schema
        stored_password = user[9]  # Assuming the password is stored in column index 2

        # Compare the entered password with the stored password
        if stored_password == password:
            # Return success with user data (excluding password)
            return jsonify({
                "status": "success",
                "user": {
                    "id": user_id,
                    "email": stored_email,
                    # Add other fields as needed
                }
            }), 200
        else:
            return jsonify({'error': 'Invalid password'}), 401
    else:
        return jsonify({'error': 'User not found'}), 404


@app.route('/api/complete_profile/<int:user_id>', methods=['PUT'])
def complete_profile(user_id):
    try:
        # Get the JSON data from the request body
        data = request.get_json()

        # Check if the required fields are present in the data
        if not all(k in data for k in ('name', 'gender', 'phone', 'profile')):
            return jsonify({'error': 'missing_fields', 'message': 'Missing one or more required fields.'}), 400

        name = data['name']
        gender = data['gender']
        phone = data['phone']
        profile = data['profile']

        # Log the data for debugging (check what data is being received)
        print(f"Received data: {data}")

        # Update user data in the database (replace this with your actual DB update logic)
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE tbl_users 
            SET name = %s, gender = %s, phone = %s, profile = %s
            WHERE id = %s
        """, (name, gender, phone, profile, user_id))

        mysql.connection.commit()  # Commit changes to the database
        cur.close()

        return jsonify({'message': 'User updated successfully!'}), 200
    except Exception as e:
        print(f"Error: {e}")  # Log the error for debugging
        return jsonify({'error': 'user_update_failed', 'details': str(e)}), 400




@app.route('/api/users', methods=['POST'])
def add_user():
    try:
        # Collect data
        code = request.form['code']
        name = request.form['name']
        address = request.form['address']
        role = request.form['role']
        gender = request.form['gender']
        password = request.form['password']
        phone = request.form['phone']
        email = request.form['email']
        status = request.form['status']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM tbl_users WHERE email = %s", (email,))
        existing_user = cur.fetchone()
        if existing_user:
            return jsonify({'error': 'email_exists', 'message': 'Email already exists!'}), 400
        # Handle image upload
        image = request.files.get('image')
        image_name = None
        if image:
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
            image_name = filename
        # cur = mysql.connection.cursor()
        cur.execute("""
                    INSERT INTO tbl_users (code, name,profile ,address, role, gender, email ,phone, password, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s,%s, %s, %s)
                """, (code, name, image_name, address, role, gender, email ,phone, password, status))

        mysql.connection.commit()
        new_id = cur.lastrowid
        cur.close()

        return jsonify({'message': 'User added successfully!', 'id':new_id}), 201

    except Exception as e:
            print(f"Error: {e}")  # Print error for debugging
            return jsonify({'error': 'user to add product', 'details': str(e)}), 400





@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    try:
        # Collect JSON data from the request body
        data = request.get_json()
        print("Received data:", data)
        code = data['code']
        name = data['name']
        address = data['address']
        role = data['role']
        gender = data['gender']
        password = data['password']
        phone = data['phone']
        email = data['email']
        status = data['status']

        cur = mysql.connection.cursor()

        # Check if the email exists and belongs to another user
        cur.execute("SELECT * FROM tbl_users WHERE email = %s AND id != %s", (email, user_id))
        existing_user = cur.fetchone()
        if existing_user:
            return jsonify({'error': 'email_exists', 'message': 'Email already exists!'}), 400

        # Handle image upload - make sure the image is sent as part of multipart form data
        image_name = None
        if 'image' in request.files:
            image = request.files['image']
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
            image_name = filename

            # Update the user information, including the new image if uploaded
            cur.execute("""
                UPDATE tbl_users 
                SET code = %s, name = %s, profile = %s, address = %s, role = %s, 
                    gender = %s, email = %s, phone = %s, password = %s, status = %s 
                WHERE id = %s
            """, (code, name, image_name, address, role, gender, email, phone, password, status, user_id))
        else:
            # Update user info without changing the image
            cur.execute("""
                UPDATE tbl_users 
                SET code = %s, name = %s, address = %s, role = %s, 
                    gender = %s, email = %s, phone = %s, password = %s, status = %s 
                WHERE id = %s
            """, (code, name, address, role, gender, email, phone, password, status, user_id))

        mysql.connection.commit()  # Commit the changes
        cur.close()

        return jsonify({'message': 'User updated successfully!'}), 200

    except Exception as e:
        print(f"Error: {e}")  # Print error for debugging
        return jsonify({'error': 'user_update_failed', 'details': str(e)}), 400



@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM tbl_users WHERE id = %s", (user_id,))
        mysql.connection.commit()  # Commit the changes
        cur.close()

        return jsonify({'message': 'User deleted successfully!'}), 204
    except Exception as e:
        print(f"Error: {e}")  # Print error for debugging
        return jsonify({'error': 'user deletion failed', 'details': str(e)}), 400