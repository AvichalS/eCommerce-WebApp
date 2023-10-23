from warnings import catch_warnings
from flask import Flask, render_template, request, redirect, flash, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors, re, hashlib

app = Flask(__name__)

app.secret_key = 'your secret key'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '*I@tbAS7*'
app.config['MYSQL_DB'] = 'abca_app'

mysql = MySQL(app)

# http://localhost:5000/login
@app.route('/login/', methods=['GET', 'POST'])
def login():
    msg = ''
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password,))
        # Fetch one record and return result
        account = cursor.fetchone()
        # If account exists in accounts table in out database
        if account:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            # Redirect to home page
            return redirect(url_for('home'))
        else:
            # Account doesnt exist or username/password incorrect
            msg = 'Incorrect username or password!' 
    # Show the login form with message (if any)
    return render_template('index.html', msg=msg)

# http://localhost:5000/login/logout
@app.route('/login/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   # Redirect to login page
   return redirect(url_for('login'))

# http://localhost:5000/login/register 
@app.route('/login/register', methods=['GET', 'POST'])
def register():
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
                # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s', (username,))
        account = cursor.fetchone()
        # If account exists show error and validation checks
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            # Hash the password
            # hash = password + app.secret_key
            # hash = hashlib.sha1(hash.encode())
            # password = hash.hexdigest()
            # Account doesn't exist, and the form data is valid, so insert the new account into the accounts table
            cursor.execute('INSERT INTO accounts VALUES (NULL, %s, %s, %s)', (username, password, email,))
            mysql.connection.commit()
            msg = 'You have successfully registered!'
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    # Show registration form with message (if any)
    return render_template('register.html', msg=msg)

@app.route('/login/home', methods=['GET', 'POST'])
def home():
    # Check if the user is logged in
    if 'loggedin' in session:
        search_query = request.args.get('search', default='', type=str)

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        if search_query:
            cursor.execute(f'SELECT item_id, item_name, item_price FROM items WHERE item_name LIKE %s;', (f'%{search_query}%',))
        else:
            cursor.execute(f'SELECT item_id, item_name, item_price FROM items;')
        items = cursor.fetchall()

        # Initialize tnf with False values based on the number of items
        tnf = [False] * len(items)

        cursor.execute(f'SELECT item_id FROM items_selected WHERE id = {session["id"]};')
        query = cursor.fetchall()

        for element in query:
            item_id = element["item_id"]
            # Set the corresponding index in tnf to True for items in the cart
            tnf[item_id - 1] = True

        if request.method == 'POST':
            # Clear the user's cart before adding new items
            cursor.execute('DELETE FROM items_selected WHERE id = %s', (session['id'],))
            mysql.connection.commit()

            # Handle form submission and update tnf as needed
            selected_items = [request.form.get(str(i["item_id"])) for i in items]

            items_selected_count = sum(1 for item in selected_items if item)


            if items_selected_count == 0:
                flash("No item selected!")
            else:
                flash("Items added successfully!")

                for i, selected in enumerate(selected_items):
                    if selected:
                        tnf[i] = True
                        # Store the quantity in session
                        quantity = request.form.get('quantity_' + str(items[i]["item_id"])) or 1
                        session[f'quantity_{items[i]["item_id"]}'] = quantity

                for i, selected in enumerate(selected_items):
                    if selected:
                        quantity = request.form.get('quantity_' + str(items[i]["item_id"])) or 1
                        cursor.execute(f'INSERT INTO items_selected (id, item_id, quantity) VALUES ({session["id"]}, {items[i]["item_id"]}, {quantity}) ON DUPLICATE KEY UPDATE quantity = {quantity};')
                        mysql.connection.commit()

        # User is logged in, show them the home page with the updated tnf list
        return render_template('home.html', username=session['username'], items=items, alertshow="True", tnf=tnf, len=len(tnf))

    # User is not logged in, redirect to the login page
    return redirect(url_for('login'))

# http://localhost:5000/login/profile
@app.route('/login/profile')
def profile():
    # Check if the user is logged in
    if 'loggedin' in session:
        # We need all the account info for the user so we can display it on the profile page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE id = %s', (session['id'],))
        account = cursor.fetchone()

        cursor.execute(f'''
    SELECT 
        tab.id, 
        tab.item_name,
        tab.item_price,
        items_selected.quantity,
        tab.item_price * items_selected.quantity AS total_price 
    FROM 
        (SELECT 
            items_selected.id, 
            items_selected.item_id, 
            items_selected.quantity,
            items.item_name,
            items.item_price
        FROM 
            items_selected
        INNER JOIN 
            items 
        ON 
            items_selected.item_id = items.item_id) tab 
    INNER JOIN 
        items_selected
    ON 
        tab.item_id = items_selected.item_id 
    WHERE 
        tab.id = %s;
''', (session["id"],))


        items = cursor.fetchall()
        
        total = sum(item['total_price'] for item in items)
        # Show the profile page with account info and selected items
        return render_template('profile.html', account=account, items=items, total=total)
    # User is not logged in redirect to login page
    return redirect(url_for('login'))


@app.route('/login/profile/clear_cart', methods=['GET'])
def clear_cart():
    # Check if the user is logged in
    if 'loggedin' in session:
        # Delete all items from the user's selected items list
        cursor = mysql.connection.cursor()
        cursor.execute('DELETE FROM items_selected WHERE id = %s', (session['id'],))
        # Get the row count affected by the DELETE operation
        row_count = cursor.rowcount

        if row_count == 0:
            flash('Cart is empty!', 'danger')
        else:
            # Clear quantities in session for all possible items
            cursor.execute(f'SELECT item_id FROM items;')
            all_items = cursor.fetchall()
            for item in all_items:
                item_id = item[0]  # Extract item_id from the tuple
                session.pop(f'quantity_{item_id}', None)

            # Commit the changes to the database
            mysql.connection.commit()

            flash('Your cart has been cleared successfully!', 'success')

        return redirect(url_for('profile'))
    
    # If the user is not logged in, redirect to the login page
    return redirect(url_for('login'))


if __name__=='__main__':
    app.run(debug=True)