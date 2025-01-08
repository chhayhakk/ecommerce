from datetime import datetime, date
import uuid
import requests
from flask import jsonify, request, session
from app import app, render_template
from routes.dashboard import get_data
from routes.dashboard import get_categories, mysql
from routes.dashboard import login_required


channel_id= "@chhayhak_notify_channel"
bot_token = "7143396464:AAEtiHgXPxWQiR8n9QRwkrhIWYyuYQWz4ro"
bot_username ="chhayhakk_bot"
@app.route('/pos')
@login_required
def pos():
    return render_template("index.html")


@app.route('/pos/get-categories')
def fetchCategories():
    category_list = get_categories()
    return jsonify({'category_list': category_list})


@app.route('/pos/get-products')
def fetchProducts():
    product_list = get_data()
    return jsonify({'product_list': product_list})



@app.post('/pos/payment')
def payment():
    current_user = session.get('user')
    form = request.get_json()
    selected_product = form['selected_product']
    total_amount = form['total_amount']
    received_amount = form['received_amount']
    transaction_date = datetime.now()
    ref_code = f"ref_code_{int(uuid.uuid4().int % 1e8)}"
    user_id = current_user['id']
    cur = mysql.connection.cursor()
    try:
        # Insert the sale record
        cur.execute(
            "INSERT INTO tbl_sales (ref_code, transaction_date, received_amount, total_amount, user_id) VALUES (%s, %s, %s, %s, %s)",
            (ref_code, transaction_date, received_amount, total_amount, user_id)
        )
        # Get the last inserted ID
        last_sale_id = cur.lastrowid
        print(last_sale_id)
        for item in selected_product:
            total = item['qty'] * item['price']
            sale_item = cur.execute(
                "INSERT INTO tbl_sale_detail (sale_id, product_id, qty, price ,total) VALUES (%s, %s, %s, %s,%s)",
                (last_sale_id, item['id'], item['qty'], item['price'], total )
            )
        mysql.connection.commit()
        html = (
            "<strong>🧾 INV0001</strong>\n"
            "<code>📆 {date}</code>\n"
            "<code>====================================</code>\n"
            "<code>Product       Qty   Price   Total</code>\n"
            "<code>------------------------------------</code>\n"
        )
        for item in selected_product:
            price = float(item['price'])
            total = item['qty'] * price
            html += "<code>{:<12} {:<7} ${:<7.2f} ${:<7.2f}</code>\n".format(
                item['name'], item['qty'], price, total
            )
        html += (
            "<code>------------------------------------</code>\n"
            "<code>Total:         ${:.2f}</code>\n"
            "<code>Received:      ${:.2f}</code>\n"
            "<code>Change:        ${:.2f}</code>\n"
            "<code>Change:         {:.2f}</code>Riel\n"
            "<code>------------------------------------</code>\n"
            "<strong>Grand Total: ${:.2f}</strong>\n"
        ).format(total_amount, received_amount, received_amount - total_amount,(received_amount - total_amount) * 4000 ,total_amount)

        # Format with the date
        html = html.format(date=transaction_date.strftime('%Y-%m-%d %H:%M:%S'))

        # Send to Telegram
        res = requests.get(
            f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={channel_id}&text={html}&parse_mode=HTML"
        )

        return jsonify({"message": "Sale created successfully", "sale_id": last_sale_id}), 201

    except Exception as e:
        # Return the error message
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()

    return selected_product, total_amount, received_amount, transaction_date


@app.route('/api/add_to_cart', methods=['POST'])
def add_to_cart():
    data = request.get_json()
    product_id = data['product_id']
    user_id = data['user_id']
    size = data['size']
    quantity = data['quantity']

    if not product_id or not user_id or not size:
        return jsonify({"error": "Product ID, User ID, or Size is missing"}), 400

    try:
        cur = mysql.connection.cursor()

        query_check = "SELECT qty FROM tbl_cart WHERE product_id = %s AND user_id = %s AND size = %s"
        cur.execute(query_check, (product_id, user_id, size))
        existing_item = cur.fetchone()

        if existing_item:

            new_quantity = existing_item[0] + quantity
            query_update = "UPDATE tbl_cart SET qty = %s WHERE product_id = %s AND user_id = %s AND size = %s"
            cur.execute(query_update, (new_quantity, product_id, user_id, size))
        else:
            query_insert = "INSERT INTO tbl_cart (product_id, user_id, qty, size) VALUES (%s, %s, %s, %s)"
            cur.execute(query_insert, (product_id, user_id, quantity, size))

        mysql.connection.commit()
        cur.close()
        return jsonify({"message": "Product added to cart"}), 201

    except Exception as e:
        # Log the error for debugging purposes
        print(f"Error: {e}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500


@app.route('/api/get_cart/<int:id>', methods=['GET'])
def get_cart(id):
    try:
        cur = mysql.connection.cursor()

        # Fetch cart items as usual
        cur.execute("""
            SELECT tbl_cart.user_id, tbl_products.id, tbl_products.name, tbl_cart.qty, tbl_products.price, tbl_products.image, tbl_cart.size
            FROM tbl_cart
            INNER JOIN tbl_products ON tbl_cart.product_id = tbl_products.id
            WHERE tbl_cart.user_id = %s
        """, (id,))

        cart_items = cur.fetchall()

        if cart_items:
            cart_list = []
            for item in cart_items:
                cart_list.append({
                    'user_id': item[0],
                    'product_id': item[1],
                    'product_name': item[2],
                    'quantity': item[3],
                    'price': item[4],
                    'image': item[5],
                    'size': item[6],
                })

            updated_cart_list = []
            total_price = 0
            product_map = {}
            for product in cart_list:
                key = (product['product_id'], product['size'])
                if key in product_map:
                    product_map[key]['quantity'] += product['quantity']
                else:
                    product_map[key] = product
                total_price += product['quantity'] * product['price']
            updated_cart_list = list(product_map.values())
            response = {
                'cart': updated_cart_list,
                'total_price': round(total_price, 2)  # Round to 2 decimal places for currency
            }
            return jsonify(response)
        else:
            return jsonify({'message': 'Cart is empty'}), 404
    except Exception as e:
        print(f"Error fetching cart: {e}")
        return jsonify({'message': 'An error occurred'}), 500
    finally:
        cur.close()


@app.route('/api/update_cart', methods=['POST'])
def update_cart():
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        user_id = data.get('user_id')
        size = data.get('size')
        quantity = data.get('quantity')


        cur = mysql.connection.cursor()


        cur.execute("""
            UPDATE tbl_cart
            SET qty = %s
            WHERE user_id = %s AND product_id = %s AND size = %s
        """, (quantity, user_id, product_id, size))

        mysql.connection.commit()
        cur.close()

        return jsonify({'message': 'Cart updated successfully'}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'message': 'An error occurred'}), 500


@app.route('/api/delete_from_cart', methods=['POST'])
def delete_from_cart():
    data = request.get_json()
    product_id = data.get('product_id')
    user_id = data.get('user_id')
    size = data.get('size')

    # Validate input data
    if not product_id or not user_id or not size:
        return jsonify({"error": "Product ID, User ID, or Size is missing"}), 400

    try:
        cur = mysql.connection.cursor()

        # Check if the item exists in the cart
        query_check = "SELECT qty FROM tbl_cart WHERE product_id = %s AND user_id = %s AND size = %s"
        cur.execute(query_check, (product_id, user_id, size))
        existing_item = cur.fetchone()

        if not existing_item:
            return jsonify({"error": "Item not found in the cart"}), 404

        # Delete the item from the cart
        query_delete = "DELETE FROM tbl_cart WHERE product_id = %s AND user_id = %s AND size = %s"
        cur.execute(query_delete, (product_id, user_id, size))

        mysql.connection.commit()
        cur.close()

        return jsonify({"message": "Product removed from cart"}), 200

    except Exception as e:
        # Log the error for debugging purposes
        print(f"Error: {e}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@app.route('/api/add_to_favorite', methods=['POST'])
def add_to_favorite():
    data = request.get_json()
    product_id = data['product_id']
    user_id = data['user_id']

    if not product_id or not user_id:
        return jsonify({"error": "Product ID, User ID is missing"}), 400

    try:
        cur = mysql.connection.cursor()

        # Check if the product is already in the user's favorites
        query_check = "SELECT id FROM tbl_favorites WHERE product_id = %s AND user_id = %s"
        cur.execute(query_check, (product_id, user_id))
        existing_item = cur.fetchone()

        if existing_item:
            return jsonify({"message": "Product is already in the favorites"}), 400

        # Insert the product into favorites table
        query_insert = "INSERT INTO tbl_favorites (product_id, user_id) VALUES (%s, %s)"
        cur.execute(query_insert, (product_id, user_id))

        mysql.connection.commit()
        cur.close()

        return jsonify({"message": "Product added to favorites"}), 201

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500


@app.route('/api/remove_from_favorite', methods=['POST'])
def remove_from_favorite():
    data = request.get_json()
    product_id = data.get('product_id')
    user_id = data.get('user_id')

    if not product_id or not user_id:
        return jsonify({'error': 'Missing product_id or user_id'}), 400

    cur = mysql.connection.cursor()

    try:
        cur.execute("""
            DELETE FROM tbl_favorites 
            WHERE product_id = %s AND user_id = %s;
        """, (product_id, user_id))


        mysql.connection.commit()

        if cur.rowcount > 0:
            return jsonify({'message': 'Product removed from favorites'}), 200
        else:
            return jsonify({'error': 'Product not found in favorites'}), 404

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()

@app.route('/api/create_order', methods=['POST'])
def create_order():
    data = request.get_json()

    user_id = data.get('user_id')
    total_price = data.get('total_price')
    items = data.get('cart_items')
    payment_method = data.get('payment_method')
    shipping_address = data.get('shipping_address')  # New field for address

    # Validate the incoming data
    if not user_id or not total_price or not items or not payment_method or not shipping_address:
        return jsonify({"error": "User ID, Total Price, Items, Payment Method, or Shipping Address missing"}), 400

    try:
        cur = mysql.connection.cursor()

        # Insert into tbl_orders
        query_insert_order = """
            INSERT INTO tbl_orders (user_id, total_price, status, payment_method, 
            shipping_address_line1, shipping_address_line2, shipping_city, shipping_state, shipping_country, shipping_postal_code, shipping_phone)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(query_insert_order, (
            user_id, total_price, 'Pending', payment_method,
            shipping_address['line1'], shipping_address.get('line2', ''), shipping_address['city'],
            shipping_address['state'], shipping_address['country_code'], shipping_address['postal_code'], shipping_address['phone']
        ))

        order_id = cur.lastrowid  # Get the generated order ID

        # Insert into tbl_order_details
        for item in items:
            query_insert_order_detail = """
                INSERT INTO tbl_order_details (order_id, product_id, qty, price, size)
                VALUES (%s, %s, %s, %s, %s)
            """
            cur.execute(query_insert_order_detail, (order_id, item['product_id'], item['quantity'], item['price'], item['size']))

        # Remove items from the cart
        for item in items:
            query_delete_from_cart = """
                DELETE FROM tbl_cart WHERE product_id = %s AND user_id = %s AND size = %s
            """
            cur.execute(query_delete_from_cart, (item['product_id'], user_id, item['size']))

        mysql.connection.commit()
        cur.close()

        return jsonify({"message": "Order created successfully", "order_id": order_id}), 201

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@app.route('/api/orders/<int:user_id>', methods=['GET'])
def get_orders_by_user(user_id):
    try:
        cur = mysql.connection.cursor()

        query_get_orders = """
            SELECT o.id, o.total_price, o.status, o.created_at, oi.product_id, oi.qty, oi.price, oi.size, p.name, p.image
            FROM tbl_orders o
            JOIN tbl_order_details oi ON o.id = oi.order_id
            JOIN tbl_products p ON oi.product_id = p.id
            WHERE o.user_id = %s
            ORDER BY o.created_at DESC
        """
        cur.execute(query_get_orders, (user_id,))
        result = cur.fetchall()

        if not result:
            return jsonify({"error": "No orders found for this user"}), 404

        orders = []
        current_order = None
        for row in result:
            order_id = row[0]
            if current_order is None or current_order['order_id'] != order_id:
                if current_order:
                    orders.append(current_order)

                current_order = {
                    'order_id': order_id,
                    'total_price': row[1],
                    'status': row[2],
                    'created_at': row[3],
                    'items': []
                }

            current_order['items'].append({
                'product_id': row[4],
                'quantity': row[5],
                'price': row[6],
                'size': row[7],
                'product_name': row[8],
                'image': row[9],
            })

        if current_order:
            orders.append(current_order)

        cur.close()
        return jsonify(orders), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500


@app.route('/api/order/<int:order_id>', methods=['GET'])
def get_order_details(order_id):
    try:
        # User ID validation (Optional: Add based on requirements)
        user_id = request.args.get('user_id')  # Fetch user_id from query params if required
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400

        cur = mysql.connection.cursor()

        # Query to fetch order details with user validation
        query_get_order = """
            SELECT o.id, o.total_price, o.status, o.created_at, o.payment_method, 
                   o.shipping_address_line1, o.shipping_address_line2, o.shipping_city, 
                   o.shipping_state, o.shipping_country, o.shipping_postal_code, o.shipping_phone,
                   oi.product_id, oi.qty, oi.price, oi.size, p.name, p.image
            FROM tbl_orders o
            JOIN tbl_order_details oi ON o.id = oi.order_id
            JOIN tbl_products p ON oi.product_id = p.id
            WHERE o.id = %s AND o.user_id = %s
        """
        cur.execute(query_get_order, (order_id, user_id))
        result = cur.fetchall()

        # Check if the order exists
        if not result:
            return jsonify({"error": "Order not found"}), 404

        # Prepare the order details response
        order_details = {
            "order_id": result[0][0],
            "total_price": float(result[0][1]),
            "status": result[0][2],
            "created_at": result[0][3].strftime('%Y-%m-%d %H:%M:%S'),  # Format datetime
            "payment_method": result[0][4],
            "shipping_address": {
                "line1": result[0][5],
                "line2": result[0][6],
                "city": result[0][7],
                "state": result[0][8],
                "country": result[0][9],
                "postal_code": result[0][10],
                "phone": result[0][11],
            },
            "items": []
        }

        # Add items to the order
        for row in result:
            order_details["items"].append({
                "product_id": row[12],
                "quantity": row[13],
                "price": float(row[14]),  # Ensure price is float
                "size": row[15],
                "product_name": row[16],
                "image": row[17]
            })

        cur.close()
        return jsonify(order_details), 200

    except Exception as e:
        # Log the exception and return a structured error response
        print(f"Error: {e}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500







