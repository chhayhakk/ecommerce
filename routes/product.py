from datetime import datetime, date

import requests
from flask import jsonify, request
from app import app, render_template
from routes.dashboard import get_data
from routes.dashboard import get_categories, mysql



channel_id= "@chhayhak_notify_channel"
bot_token = "7143396464:AAEtiHgXPxWQiR8n9QRwkrhIWYyuYQWz4ro"
bot_username ="chhayhakk_bot"
@app.route('/pos')
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
    form = request.get_json()
    selected_product = form['selected_product']
    total_amount = form['total_amount']
    received_amount = form['received_amount']
    transaction_date = datetime.now()
    ref_code = 'ref_code_001'
    user_id = 1
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

    # (This line is unreachable and should be removed)
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




