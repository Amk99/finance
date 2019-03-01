import os

from cs50 import SQL
import os
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("postgres://wdlaedvbfgugvd:a8a0391b8dc9403346155b4e8b196a9ba91be0f25949ba7d639d39fdf701e08d@ec2-107-20-167-11.compute-1.amazonaws.com:5432/ddceka8gco0fd7")


@app.route("/")
@login_required
def index():
    smbols = db.execute("SELECT symbol FROM checktable WHERE userid = :user_d",user_d=session["user_id"])
    grand_ttl = 0
    if smbols != []:
        entries = []
        cashinhand = db.execute("SELECT cash FROM users WHERE id = :user_d",user_d=session["user_id"])
        for symbol in smbols:
            symbol_P = lookup(symbol["symbol"])
            stk = db.execute("SELECT share FROM checktable WHERE userid = :a AND symbol = :b",
                            a = session["user_id"],b=symbol["symbol"])
            if int(stk[0]["share"]) == 0:
                continue
            else:
                info = {}

                info["name"] = symbol_P["name"]
                info["symbol"] = symbol_P["symbol"]
                info["price"] = symbol_P["price"]
                info["shares"] = int(stk[0]["share"])
                info["total"] = int(stk[0]["share"])*float(symbol_P["price"])

                entries.append(info)

        for i in range(len(entries)):
            grand_ttl += entries[i]["total"]
        grand_ttl += float(cashinhand[0]["cash"])

        for i in range(len(entries)):
            entries[i]['price'] = usd(entries[i]['price'])
            entries[i]['total'] = usd(entries[i]['total'])

        return render_template("index.html",entries = entries,cash = usd(cashinhand[0]["cash"]),grand_ttl = usd(grand_ttl))
    else:
        cashhand = db.execute("SELECT cash FROM users WHERE id = :a",
                              a = session["user_id"])
        return render_template("index.html",cash = usd(cashhand[0]["cash"]),grand_ttl = usd(cashhand[0]["cash"]))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":

        row = lookup(request.form.get("symbol"))
        if not row:
            return apology("invalid symbol")
        if not request.form.get("shares"):
            return apology("Must provide number of shares,400")
        try:
            sares = int(request.form.get("shares"))
        except:
            return apology("must be positive integer",400)
        if sares <= 0:
            return apology("cant sell 0 or less",400)
        cashinhand = db.execute("SELECT cash FROM users WHERE id = :user_id",user_id = session["user_id"])
        ttl_Price = float(request.form.get("shares")) * float(row["price"])
        if ttl_Price <= float(cashinhand[0]["cash"]):
            db.execute("INSERT INTO Buytable (userid,sharename,quantity,price,total,dateandtime) VALUES (:p,:q,:r,:s,:t,:u)",
                        p = session["user_id"],
                        q = row["name"],
                        r = request.form.get("shares"),
                        s = row["price"],
                        t = row["price"]*float(request.form.get("shares")),
                        u = datetime.datetime.now())
            updt = db.execute("UPDATE users SET cash = :new_cash WHERE id = :usr_id",new_cash = float(cashinhand[0]["cash"]) - ttl_Price,usr_id = session["user_id"])
            aml = db.execute("INSERT INTO checktable (userid,symbol,name,share,price,total) VALUES(:userid,:symbol,:name,:share,:price,:total)",
                                userid=session["user_id"],
                                symbol=request.form.get("symbol"),
                                name=row["name"],
                                share=int(request.form.get("shares")),
                                price=row["price"],
                                total=int(row["price"])*int(request.form.get("shares")))
            if not aml:
                stk = db.execute("SELECT share FROM checktable WHERE userid = :a AND symbol = :b",a = session["user_id"],b = request.form.get("symbol"))
                apl = db.execute("UPDATE checktable SET share = :l,total = :p,price = :kj WHERE userid = :a AND symbol =:b",l = int(stk[0]["share"]) + int(request.form.get("shares")),
                                a=session["user_id"],b = request.form.get("symbol"),kj = row["price"],
                                p = ((int(stk[0]["share"]) + int(request.form.get("shares")))*int(row["price"])))
            flash("bought!!")
            return redirect("/")
        elif float(cashinhand[0]["cash"]) < ttl_Price:
            return apology("not enough cash")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    history = db.execute("SELECT sharename,price,quantity,dateandtime FROM buytable WHERE userid = :l",l = session["user_id"])
    return render_template("history.html",history = history)


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
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

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
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method =="POST":
        rows = lookup(request.form.get("symbol"))

        if not rows:
            return apology("invalid symbol")

        return render_template("display.html",a = rows)
    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET","POST"])
def register():


    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Missing Username!!", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Missing password", 400)

        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords dont match!",400)

        # Query database for username
        result = db.execute("INSERT INTO users (username,hash) VALUES(:username,:_hash)",username  = request.form.get("username"), _hash = generate_password_hash(request.form.get("password")))

        if not result:
            return apology("username already exists!,403")

        user_id = db.execute("SELECT id FROM users WHERE username = :a",a = request.form.get("username"))
        session["user_id"] = user_id[0]["id"]
        # Redirect user to home page
        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        rows = lookup(request.form.get("symbol"))
        shares = int(request.form.get("shares"))
        if not rows:
            return apology("invalid symbol,400")
        if not shares or shares <= 0:
            return apology ("enter valid quantity,400")

        shares_hd = db.execute("SELECT share FROM checktable WHERE userid = :a AND symbol = :b",a = session["user_id"],b = request.form.get("symbol"))
        shares_held = int(shares_hd[0]["share"])

        #check for valid request#
        if not shares_hd :
            return apology("you do not own this share,103")
        if shares_held == 0:
            return apology ("not enough shares,104")
        if int(request.form.get("shares")) > shares_held:
            return apology ("more than owned",400)

        apk = db.execute("UPDATE checktable SET share = :l,total = :p,price = :kj WHERE userid = :a AND symbol =:b",l = int(shares_hd[0]["share"]) - int(request.form.get("shares")),
                                a = session["user_id"],b = request.form.get("symbol"),kj = rows["price"],
                                p = (int(shares_hd[0]["share"]) - int(request.form.get("shares")))*float(rows["price"]))
        db.execute("INSERT INTO Buytable (userid,sharename,quantity,price,total,dateandtime) VALUES (:p,:q,:r,:s,:t,:u)",
            p = session["user_id"],
            q = rows["name"],
            r = "-" + request.form.get("shares"),
            s = rows["price"],
            t = rows["price"]*float(request.form.get("shares")),
            u = datetime.datetime.now())

        ttl_price = int(request.form.get("shares"))*int(rows["price"])
        cashnhand = db.execute("SELECT cash FROM users WHERE id = :user_id",user_id = session["user_id"])
        hij = db.execute("UPDATE users SET cash = :new_cash WHERE id = :usr_id",new_cash = float(cashnhand[0]["cash"]) + ttl_price,usr_id = session["user_id"])
        flash("sold!")
        return redirect("/")

    else:
        amk = db.execute("SELECT symbol FROM checktable WHERE userid = :k",k = session["user_id"])
        return render_template("sell.html",a = amk)

@app.route("/addcash", methods=["GET", "POST"])
@login_required
def addcash():
    if request.method == "POST":

        if not request.form.get("addcash"):
            return apology("please enter cash",400)
        cashnhand = db.execute("SELECT cash FROM users WHERE id = :user_id",user_id = session["user_id"])
        dbs = db.execute("UPDATE users SET cash = :newcash  WHERE id = :a",newcash = float(request.form.get("addcash")) + float(cashnhand[0]["cash"]),a = session["user_id"])
        return redirect("/")
    else:
        return render_template("addcash.html")

def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

if __name__ == "__main__":
 port = int(os.environ.get("PORT", 8080))
 app.run(host="0.0.0.0", port=port)