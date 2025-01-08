import shutil

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
flutter_products_path = 'D:\\flutter\\finalflutter\\assets\\products'
from flask_mysqldb import MySQL

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'flask_ecommerce'

mysql = MySQL(app)

from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')  # Get user data from session
        print(f"User session: {user}")  # Print session for debugging

        if not user:
            flash('You must be logged in to access this page.', 'warning')
            return redirect(url_for('login'))  # Redirect to the login page if not logged in

        return f(*args, **kwargs)

    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')  # Get user data from session
        print(f"User session: {user}")  # Print session for debugging

        if not user:
            flash('You must be logged in to access this page.', 'warning')
            return redirect(url_for('login'))  # Redirect to the login page if not logged in

        if user.get('role') != 'admin':  # Check if the user is an admin
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('pos'))  # Redirect to home page if not an admin

        return f(*args, **kwargs)

    return decorated_function
@app.route('/')
@app.route('/admin')
@login_required
@admin_required
def home():
    user = session.get('user')
    print(f"Home page user session: {user}")
    module = 'Dashboard'
    return render_template("admin/dashboard.html", module=module)

@app.route('/sale')
@login_required
@admin_required
def sale():
    module = 'Sale'
    return render_template("admin/sales.html", module=module)

@app.route('/sale_detail')
@login_required
@admin_required
def sale_detail():
    return render_template("admin/sale_detail.html")


@app.get('/pos/sale/<int:sale_id>')
def get_sale_details(sale_id):
    try:
        # Initialize cursor
        cur = mysql.connection.cursor()

        # Query to get the sale summary
        cur.execute("""
            SELECT
                s.id,
                s.ref_code,
                s.total_amount,
                s.received_amount,
                s.received_amount - s.total_amount AS change_amount,
                (s.received_amount - s.total_amount) * 4000 AS change_in_riel,
                u.name AS user_name,
                s.transaction_date
            FROM
                tbl_sales s
            INNER JOIN
                tbl_users u ON s.user_id = u.id
            WHERE
                s.id = %s
        """, (sale_id,))

        sale_summary = cur.fetchone()

        # Query to get the sale details
        cur.execute("""
            SELECT
                sd.sale_id,
                sd.product_id,
                p.name AS product_name,
                sd.qty,
                sd.price,
                sd.total,
                p.image
            FROM
                tbl_sale_detail sd
            INNER JOIN
                tbl_products p ON sd.product_id = p.id
            WHERE
                sd.sale_id = %s
        """, (sale_id,))

        sale_details = cur.fetchall()

        if sale_summary and sale_details:
            # Prepare sale summary
            sale_summary_dict = {
                'sale_id': sale_summary[0],
                'ref_code': sale_summary[1],
                'total_amount': str(sale_summary[2]),
                'received_amount': str(sale_summary[3]),
                'change_amount': str(sale_summary[4]),
                'change_in_riel': str(sale_summary[5]),
                'user_name': sale_summary[6],
                'transaction_date': sale_summary[7]
            }

            # Prepare sale details
            sale_detail_list = [
                {
                    'price': str(sale[4]),
                    'product_id': sale[1],
                    'product_name': sale[2],
                    'qty': sale[3],
                    'sale_id': sale[0],
                    'total': sale[4] * sale[3],
                    'product_image': sale[6],
                }
                for sale in sale_details
            ]

            # Return the combined response
            return jsonify({
                'sale': sale_summary_dict,
                'details': sale_detail_list
            }), 200
        else:
            return jsonify({'message': 'Sale details not found'}), 404

    except Exception as e:
        # Handle error
        return jsonify({'error': str(e)}), 500
    finally:
        # Close cursor
        cur.close()



@app.get('/api/sales')
@login_required
def get_sales():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM tbl_sales LEFT JOIN tbl_users on tbl_sales.user_id = tbl_users.id")
        sales = cur.fetchall()

        if sales:
            # Map each user to a dictionary
            sale_list = [
                {
                    'id': sale[0],
                    'ref_code': sale[1],
                    'transaction_code': sale[2],
                    'user_id': sale[3],
                    'total_amount': sale[4],
                    'received_amount': sale[5],
                    'user_name': sale[9]
                }
                for sale in sales
            ]

            return jsonify(sale_list)  # Return all users as JSON
        else:
            return jsonify({'message': 'No users found'}), 404
    except Exception as e:
        print(f"Error: {e}")  # Print error for debugging
        return jsonify({'error': 'Failed to fetch users', 'details': str(e)}), 400
@app.route('/api/products', methods=['GET'])
def get_data():
    user_id = request.args.get('user_id')

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT 
            p.*, 
            c.cat_name,
            CASE 
                WHEN f.id IS NOT NULL THEN TRUE 
                ELSE FALSE 
            END AS is_favorite
        FROM 
            tbl_products p
        LEFT JOIN 
            tbl_categories c ON p.cat_id = c.cat_id
        LEFT JOIN 
            tbl_favorites f ON p.id = f.product_id AND f.user_id = %s
    """, (user_id,))

    results = cur.fetchall()
    columns = [column[0] for column in cur.description]

    products = []
    for row in results:
        product = {columns[i]: row[i] for i in range(len(columns))}
        products.append(product)

    cur.close()

    return products


@app.route('/api/products-data/<int:id>', methods=['GET'])
def get_data_byID(id):
    # Retrieve the user_id from the query parameters
    user_id = request.args.get('user_id')  # Example: /api/products-data/<id>?user_id=<user_id>

    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400

    cur = mysql.connection.cursor()

    # Modify the SQL query to include is_favorite, which checks if the product is in the user's favorites list
    cur.execute("""
        SELECT p.*, 
               c.cat_name, 
               IF(f.product_id IS NOT NULL, TRUE, FALSE) AS is_favorite
        FROM tbl_products p
        LEFT JOIN tbl_categories c ON p.cat_id = c.cat_id
        LEFT JOIN tbl_favorites f ON p.id = f.product_id AND f.user_id = %s
        WHERE p.id = %s;
    """, (user_id, id))

    row = cur.fetchone()
    columns = [column[0] for column in cur.description]

    product = {columns[i]: row[i] for i in range(len(columns))} if row else None

    cur.close()

    if product is None:
        return jsonify({'error': 'Product not found'}), 404

    return product


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
        #Insert into products_folder in flutter
            final_image_path = os.path.join(flutter_products_path, filename)
            shutil.copy(image_path, final_image_path)

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

            cropped_filename = secure_filename(cropped_image.filename)
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
@login_required
@admin_required
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

    return category_list  # Return as list of dictionaries, not as Response object



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
@login_required
@admin_required
def categories():
    module = "Categories"
    return render_template("admin/product_categories.html", module=module)


# @app.route('/user')
# def user():
#     module = "User"
#     return render_template("admin/user.html", module=module)
