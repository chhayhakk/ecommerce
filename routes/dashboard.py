from flask import jsonify, request
from app import app, render_template
import mysql.connector
import os
from werkzeug.utils import secure_filename
from io import BytesIO
from PIL import Image


UPLOAD_FOLDER = 'static/admin/assets/images/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CROPPED_FOLDER'] = 'static/admin/assets/cropped'
app.config['THUMBNAIL_FOLDER'] = 'static/admin/assets/thumbnails'

from flask_mysqldb import MySQL

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'flask_ecommerce'

mysql = MySQL(app)


@app.route('/')
@app.route('/admin')
def home():
    module = 'Dashboard'
    return render_template("admin/dashboard.html", module=module)


@app.route('/api/users', methods=['GET'])
def get_user():
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT user_id, profile, code, name, phone, address, gender, role, email, password, status FROM tbl_users;")
    users = cur.fetchall()

    users_list = [
        {"user_id": user_id, "profile": profile, "code": code, "name": name, "phone": phone, "address": address,
         "gender": gender, "role": role, "email": email, "password": password, "status": status, } for
        (user_id, profile, code, name, phone, address, gender, role, email, password, status) in users]
    return jsonify(users_list)


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

        mysql.connection.commit()  # Commit the changes
        cur.close()

        return jsonify({'message': 'User added successfully!'}), 201

    except Exception as e:
            print(f"Error: {e}")  # Print error for debugging
            return jsonify({'error': 'user to add product', 'details': str(e)}), 400


@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
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

        # Check if the email exists and belongs to another user
        cur.execute("SELECT * FROM tbl_users WHERE email = %s AND user_id != %s", (email, user_id))
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

            # Update the user information, including the new image if uploaded
            cur.execute("""
                UPDATE tbl_users 
                SET code = %s, name = %s, profile = %s, address = %s, role = %s, 
                    gender = %s, email = %s, phone = %s, password = %s, status = %s 
                WHERE user_id = %s
            """, (code, name, image_name, address, role, gender, email, phone, password, status, user_id))
        else:
            # Update user info without changing the image
            cur.execute("""
                UPDATE tbl_users 
                SET code = %s, name = %s, address = %s, role = %s, 
                    gender = %s, email = %s, phone = %s, password = %s, status = %s 
                WHERE user_id = %s
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
        cur.execute("DELETE FROM tbl_users WHERE user_id = %s", (user_id,))
        mysql.connection.commit()  # Commit the changes
        cur.close()

        return jsonify({'message': 'User deleted successfully!'}), 204
    except Exception as e:
        print(f"Error: {e}")  # Print error for debugging
        return jsonify({'error': 'user deletion failed', 'details': str(e)}), 400


@app.route('/api/products', methods=['GET'])
def get_data():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT p.*, c.cat_name 
        FROM tbl_products p
        LEFT JOIN tbl_categories c ON p.cat_id = c.cat_id;
    """)
    results = cur.fetchall()
    columns = [column[0] for column in cur.description]

    # Convert each row to a dictionary
    products = []
    for row in results:
        product = {columns[i]: row[i] for i in range(len(columns))}
        products.append(product)
    cur.close()
    return jsonify(products)


@app.route('/api/products', methods=['POST'])
def add_product_api():
    try:
        # Collect data from the form
        product_code = request.form['product_code']
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        current_stock = request.form['current_stock']
        cat_id = request.form['cat_id']


        image = request.files.get('image')
        cropped_image = request.files.get('cropped_image')

        image_name = None

        def compress_image(image_file, save_path):
            image_file.seek(0, os.SEEK_END)  # Move pointer to the end to check the size
            file_size = image_file.tell()  # Get the size of the file in bytes
            print(file_size/1024/1024)

            if file_size > 2 * 1024 * 1024:
                image_file.seek(0)  # Reset pointer back to the start before opening with Pillow
                img = Image.open(image_file)
                img = img.convert("RGB")  # Ensure it’s in RGB mode (needed for saving .jpeg)
                img.save(save_path, format='JPEG', quality=75)  # Save with reduced quality
                return True
            else:
                # If the file size is acceptable, save it directly
                image_file.seek(0)  # Reset pointer back to the start
                image_file.save(save_path)
                return False

        # Process the original image
        if image:
            # Secure the filename and define paths
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['THUMBNAIL_FOLDER'], filename)

            # Compress the image if necessary
            compress_image(image, image_path)
            image_name = filename

        # Process the cropped image (if available)
        if cropped_image:
            cropped_filename = secure_filename(cropped_image.filename)
            cropped_path = os.path.join(app.config['CROPPED_FOLDER'], cropped_filename)

            # Compress the cropped image if necessary
            compress_image(cropped_image, cropped_path)
            cropped_image_name = cropped_filename

        # SQL Insert query (store both the original and cropped image if they exist)
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO tbl_products (code, name, description, price, current_stock, cat_id, image)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (product_code, name, description, price, current_stock, int(cat_id), image_name))

        mysql.connection.commit()  # Commit the changes to the database
        cur.close()

        return jsonify({'message': 'Product added successfully!'}), 201

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Failed to add product', 'details': str(e)}), 400



def allowed_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product_api(product_id):
    try:
        # Collect data from the request
        product_code = request.form.get('product_code')
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        current_stock = request.form.get('current_stock')
        cat_id = request.form.get('cat_id')

        # Ensure cat_id is an integer
        if not cat_id.isdigit():
            raise ValueError("cat_id must be a valid integer")

        # Handle image upload
        image = request.files.get('image')
        cropped_image = request.files.get('cropped_image')  # Get the cropped image from the request

        image_name = None
        cropped_image_name = None

        # Fetch the current image from the database before attempting to update
        cur = mysql.connection.cursor()
        cur.execute("SELECT image FROM tbl_products WHERE id = %s", (product_id,))
        existing_product = cur.fetchone()
        current_image_name = existing_product[0] if existing_product else None

        # If a new image is uploaded, save it and update image_name
        if image:
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['THUMBNAIL_FOLDER'], filename)
            image.save(image_path)
            image_name = filename
        else:
            # If no new image is uploaded, keep the existing image name
            image_name = current_image_name

        # If a cropped image is uploaded, save it with the same name as the original image
        if cropped_image:
            # Use the original image name for the cropped image
            cropped_filename = secure_filename(cropped_image.filename)
            # You could add a suffix like '_cropped' if needed, for example:
            # cropped_filename = f"{os.path.splitext(current_image_name)[0]}_cropped{os.path.splitext(cropped_filename)[1]}"
            cropped_path = os.path.join(app.config['CROPPED_FOLDER'], cropped_filename)
            cropped_image.save(cropped_path)
            cropped_image_name = cropped_filename
        else:
            cropped_image_name = current_image_name  # If no cropped image, retain the existing image

        # Update the product in the database
        cur.execute("""
            UPDATE tbl_products
            SET code = %s, name = %s, description = %s, price = %s,
                current_stock = %s, cat_id = %s, image = %s
            WHERE id = %s
        """, (product_code, name, description, price, current_stock, int(cat_id), cropped_image_name, product_id))

        mysql.connection.commit()
        cur.close()

        return jsonify({'message': 'Product updated successfully!'}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Failed to update product', 'details': str(e)}), 400



@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    try:
        cur = mysql.connection.cursor()
        # SQL query to delete the category
        cur.execute("DELETE FROM tbl_products WHERE id = %s", (product_id,))

        # Commit the changes to the database
        mysql.connection.commit()

        # Check if any row was deleted
        if cur.rowcount == 0:
            return jsonify({"message": "Product not found."}), 404

        return jsonify({"message": "Product deleted successfully."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # Close the cursor
        cur.close()


@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    module = 'Product List'
    return render_template("admin/add_products.html", module=module)


@app.route('/product_list', methods=['GET'])
def product_list():
    module = "Product List"
    return render_template("admin/product_list.html", module=module)


@app.route('/api/categories', methods=['GET'])
def get_categories():
    cur = mysql.connection.cursor()
    cur.execute("SELECT cat_id, cat_name, cat_description FROM tbl_categories")
    categories = cur.fetchall()
    cur.close()

    category_list = [{"cat_id": cat_id, "cat_name": cat_name, "cat_description": cat_description} for
                     (cat_id, cat_name, cat_description) in categories]
    return jsonify(category_list)


@app.route('/api/categories', methods=['POST'])
def add_category():
    data = request.json
    cat_name = data.get('cat_name')
    cat_description = data.get('cat_description')

    if not cat_name or not cat_description:
        return jsonify({"error": "Category name and description are required"}), 400

    cur = mysql.connection.cursor()
    try:
        cur.execute("INSERT INTO tbl_categories (cat_name, cat_description) VALUES (%s, %s)",
                    (cat_name, cat_description))
        mysql.connection.commit()
        return jsonify({"message": "Category created successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()


@app.route('/api/categories/<int:cat_id>', methods=['PUT'])
def update_category(cat_id):
    data = request.get_json()
    cat_name = data.get('cat_name')
    cat_description = data.get('cat_description')

    if not cat_name or not cat_description:
        return jsonify({"error": "Category name and description are required"}), 400

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE tbl_categories 
        SET cat_name = %s, cat_description = %s
        WHERE cat_id = %s
    """, (cat_name, cat_description, cat_id))
    mysql.connection.commit()
    cur.close()

    return jsonify({"message": "Category updated successfully"}), 200


@app.route('/api/categories/<int:cat_id>', methods=['DELETE'])
def delete_category(cat_id):
    try:
        cur = mysql.connection.cursor()
        # SQL query to delete the category
        cur.execute("DELETE FROM tbl_categories WHERE cat_id = %s", (cat_id,))

        # Commit the changes to the database
        mysql.connection.commit()

        # Check if any row was deleted
        if cur.rowcount == 0:
            return jsonify({"message": "Category not found."}), 404

        return jsonify({"message": "Category deleted successfully."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # Close the cursor
        cur.close()


@app.route('/categories')
def categories():
    module = "Categories"
    return render_template("admin/product_categories.html", module=module)


@app.route('/user')
def user():
    module = "User"
    return render_template("admin/user.html", module=module)
