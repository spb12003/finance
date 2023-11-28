import os

import pytz
from datetime import datetime

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():

        id = session.get("user_id")


        #lookup then Update current stock price and total_amount
        to_update = db.execute("SELECT symbol, shares FROM purchases WHERE id = ?", id)

        for row in to_update:
            symbol = row['symbol']
            shares = row['shares']
            update = lookup(symbol)

            price = update["price"]
            total_cost = round(price * float(shares), 2)

            #Update price and
            db.execute("UPDATE purchases SET price = ? WHERE symbol = ? AND id = ?", price, symbol, id)
            db.execute("UPDATE purchases SET total_cost = ? WHERE symbol = ? AND id = ?", total_cost, symbol, id)

            #Update total value in db
            users_stocks = db.execute("SELECT total_cost FROM purchases WHERE id = ?", id)
            sum_stocks = round(sum(item['total_cost'] for item in users_stocks), 2)
            db.execute("UPDATE users SET total = cash + ? WHERE id = ?", sum_stocks, id)


        #
        purchases = db.execute("SELECT * FROM purchases WHERE id = ? ORDER BY symbol ASC", id)



        #Update the users' cash balance in index
        cash_list = db.execute("SELECT cash FROM users WHERE id = ?", id)
        cash = sum(item['cash'] for item in cash_list)


        total_list = db.execute("SELECT total FROM users WHERE id = ?", id)
        total = sum(item['total'] for item in total_list)


        return render_template("index.html", purchases=purchases, cash=cash, total=total)






@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():


    #define id as the current users
    id = session.get("user_id")

    if request.method == "POST":
        #CATCHER:
        if not request.form.get("symbol"):
            return apology("must provide a stock ticker")
        if not request.form.get("shares"):
            return apology("must provide a number of shares")

        #Input form into lookup function to get the data
        stock_data = lookup(request.form.get("symbol"))

        #CATCHER: check form for valid stock ticker
        if stock_data is None:
            return apology("No stocks with that ticker found")

        #CATCHER: check that stock # input is an integer

        def is_integer(value):
            try:
                int_value = int(value)
                return True
            except ValueError:
                return False

        # Assuming you retrieve the value of shares from the user input form
        shares = request.form.get("shares")
        if shares is None:
            return apology("must provide an integer for the number of shares")
        if not is_integer(shares):
            return apology("must provide an integer for the number of shares")




        #CATCHER: check that input positive number of shares
        if int(request.form.get("shares")) < 1:
            return apology("must provide a positive number of shares")





        symbol = stock_data["symbol"]
        shares = request.form.get("shares")
        price = stock_data["price"]
        total_cost = price * float(shares)

        #CATCHER: Ensure there is enough cash to complete the purchase
        current_cash = db.execute("SELECT cash FROM users WHERE id = ?", id)
        cash = sum(item['cash'] for item in current_cash)
        print(cash)
        if cash < total_cost:
            return apology("You don't have enough funds to complete this purchase")


        #Subtract purchase from users' balance
        db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", total_cost, id)



        #create a time stamp of the purchase. Insert data into history database
        timezone = pytz.timezone('America/New_York')
        time_stamp = datetime.now(timezone)
        buy="BUY"
        db.execute("INSERT INTO history (symbol, id, shares_h, price_h, time_stamp, buy_sell) VALUES(?, ?, ?, ?, ?, ?)", symbol, id, shares, price, time_stamp, buy)




        #check if user already owns any of the stock being purchased
        existing = db.execute("SELECT symbol FROM purchases WHERE id = ?", id)

        #if any symbols from existing match the purchased stock
        if any(stock['symbol'] == symbol for stock in existing):
            #add the purchase to the existing line
            db.execute("UPDATE purchases SET shares = shares + ? WHERE id = ? AND symbol = ?", shares, id, symbol)
            db.execute("UPDATE purchases SET price = ? WHERE id = ? AND symbol = ?", price, id, symbol)
            db.execute("UPDATE purchases SET total_cost = ? * ? WHERE id = ? AND symbol = ?", price, shares, id, symbol)


            #Update total value in db
            #users_stocks = db.execute("SELECT total_cost FROM purchases WHERE id = ?", id)
            #sum_stocks = sum(item['total_cost'] for item in users_stocks)
            #db.execute("UPDATE users SET total = cash + ? WHERE id = ?", sum_stocks, id)
            flash("Bought!")
            return redirect("/")

            #if it is the first of the stock
            #if symbol != existing():

        db.execute("INSERT INTO purchases (id, symbol, name, shares, price, total_cost) VALUES(?, ?, ?, ?, ?, ?)", id, symbol, symbol, shares, price, total_cost)

            #Update total value in db
            #users_stocks = db.execute("SELECT total_cost FROM purchases WHERE id = ?", id)
            #sum_stocks = sum(item['total_cost'] for item in users_stocks)
            #db.execute("UPDATE users SET total = cash + ? WHERE id = ?", sum_stocks, id)
        flash("Bought!")
        return redirect("/")


    #Update total amount of value (cash plus stocks)

    else:
        return render_template("buy.html")







@app.route("/history")
@login_required
def history():




    id = session.get("user_id")

    history = db.execute("SELECT * FROM history WHERE id = ?", id)

    return render_template("history.html", history=history,)











@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return render_template("login.html")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():

    #if user submits the form
    if request.method == "POST":

        if not request.form.get("symbol"):
            return apology("must provide stock symbol")
        #CATCHER: check that ticker input is a string
        if not isinstance(request.form.get("symbol"), str):
            print(request.form.get("symbol"))
            return apology("must enter a valid ticker symbol")

        #confirm input is a valid ticker
        stock = lookup(request.form.get("symbol"))
        if stock is None:
            return apology("INVALID SYMBOL")




        symbol = stock['name']
        price = usd(stock['price'])
        id = session.get("user_id")
        print(price)

        #create a time stamp of the purchase. Insert data into history database
        timezone = pytz.timezone('America/New_York')
        time_stamp = datetime.now(timezone)

        db.execute("INSERT INTO search_history (symbol, id, price_h, time_stamp) VALUES(?, ?, ?, ?)", symbol, id, price, time_stamp)



        #Note: My personal touch was to add a search history table that is displayed in quote.html


        return render_template("quoted.html", symbol=symbol, price=price)

    else:
        id = session.get("user_id")
        search_history = db.execute("SELECT * FROM search_history WHERE id = ?", id)
        return render_template("quote.html", search_history=search_history)



@app.route("/register", methods=["GET", "POST"])
def register():
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        #Ensure the username isn't already taken
        taken_names = db.execute("SELECT username FROM users")
        req_name = request.form.get("username")
        if any(stock['username'] == req_name for stock in taken_names):
            return apology("Sorry, that username is already taken. Please try another.")

        # Ensure password was submitted
        if not request.form.get("password"):
            return apology("must provide password")

        #Ensure the password and password confirmation are the same
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords Must Match")

        #Hash the password
        pass_hash = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256' , salt_length=8)


        # Insert username into database
        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", request.form.get("username"), pass_hash)


        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():

    if request.method == "POST":

         #CATCHER: Ensure number of shares is input and valid
        if not request.form.get("shares"):
            return apology("must provide a number of shares", 403)
        if not request.form.get("symbol"):
            return apology("must select a stock", 403)




        stock_data = lookup(request.form.get("symbol"))

        id = session.get("user_id")
        symbol = stock_data["symbol"]
        shares = int(request.form.get("shares"))
        price = stock_data["price"]
        total_cost = price * float(shares)

        #create a variable for the current numbers of shares owned
        shares_owned = db.execute("SELECT shares FROM purchases WHERE id = ? AND symbol = ?", id, symbol)
        num_shares = int(sum(item["shares"] for item in shares_owned))

        #CATCHER: Ensure the user has enough shares to sell
        if num_shares < shares:
            return apology("You don't have enough shares to sell")

        #add total_cost to cash; Update cash in users table
        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", total_cost, id)

        #create a time stamp of the purchase. Insert data into history database
        timezone = pytz.timezone('America/New_York')
        time_stamp = datetime.now(timezone)
        sell = 'SELL'
        db.execute("INSERT INTO history (symbol, id, shares_h, price_h, time_stamp, buy_sell) VALUES(?, ?, ?, ?, ?, ?)", symbol, id, shares, price, time_stamp, sell)


        #if the user is selling all shares
        if num_shares == shares:
            #remove the entire line of data
            db.execute("DELETE FROM purchases WHERE id = ? AND symbol = ?", id, symbol)
            #update the users total
            #users_stocks = db.execute("SELECT total_cost FROM purchases WHERE id = ?", id)
            #sum_stocks = sum(item['total_cost'] for item in users_stocks)
            #db.execute("UPDATE users SET total = cash + ? WHERE id = ?", sum_stocks, id)

            return redirect("/")


        #if the user is selling only sum of their shares
        if num_shares > shares:

            print(shares)
            #update entire like of data
            db.execute("UPDATE purchases SET shares = shares - ? WHERE id = ? AND symbol = ?", shares, id, symbol)
            db.execute("UPDATE purchases SET price = ? WHERE id = ? AND symbol = ?", price, id, symbol)
            db.execute("UPDATE purchases SET total_cost = price * shares WHERE id = ? AND symbol = ?", id, symbol)
            #update the users total
            #users_stocks = db.execute("SELECT total_cost FROM purchases WHERE id = ?", id)
            #sum_stocks = sum(item['total_cost'] for item in users_stocks)
            #db.execute("UPDATE users SET total = cash + ? WHERE id = ?", sum_stocks, id)

            return redirect("/")




    else:
        id = session.get("user_id")
        stocks = db.execute("SELECT symbol FROM purchases WHERE id = ?", id)

        return render_template("sell.html", stocks=stocks)
















