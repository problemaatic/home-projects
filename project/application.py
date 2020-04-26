import os
import datetime
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import sys

from helpers import apology, login_required, lookup, usd, is_number

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
db = SQL("sqlite:///project.db")


@app.route("/")
@login_required
def index():
    return render_template("index.html")




@app.route("/add", methods=["GET", "POST"])
@login_required
def add():

    # If new cost submitted
    if request.method == "POST":

        # Check number was submitted
        # for cost per unit field
        t = request.form.get("unitCost")
        ppu = is_number(t)

        # If not a number, prompt user
        # for a number by using if statement
        # in Jinja template to render error message
        if not ppu:
            return render_template("addcost.html", s = session["s"], ppu = ppu)

        # Get variables from new cost form
        cost_name = request.form.get("costName")
        unit = request.form.get("unit")
        currency = request.form.get("currency")
        unit_cost = request.form.get("unitCost")
        quantity = request.form.get("quantity")

        # Calculate total amount of cost
        cost_total = float(unit_cost) * float(quantity)

        # Get id of project selected
        x = db.execute("SELECT id FROM projects WHERE project_name = :project_name",
        project_name = session["s"])
        project_id = x[0]["id"]

        # Add cost details to database
        db.execute("INSERT INTO costs (project_id, cost_name, total_cost, unit, unit_cost, quantity, currency) VALUES (:project_id, :cost_name, :cost_total, :unit, :unit_cost, :quantity, :currency)",
        project_id = project_id, cost_name = cost_name, cost_total = cost_total, unit = unit, unit_cost = unit_cost, quantity = quantity, currency = currency)

        # If valid form submitted
        # render table showing breakdown of
        # all project costs
        return redirect("/breakdown")

    # If new cost from requested
    # render cost form
    else:
        return render_template("addcost.html", s = session["s"])




@app.route("/breakdown", methods=["GET", "POST"])
@login_required
def breakdown():

    # If delete cost form submitted
    if request.method == "POST":

        # Get id of cost to delete
        cost_id = request.form.get("costId")

        # Get name of cost to delete
        s = db.execute("SELECT cost_name FROM costs WHERE id = :cost_id",
        cost_id = cost_id)
        cost_name = s[0]["cost_name"]
        # Delete cost from database
        db.execute("DELETE FROM costs WHERE id = :cost_id",
        cost_id = cost_id)

        # Flash alert cormirming deletion
        flash(f"{cost_name} Deleted from project")
        return redirect("/breakdown")

    else:
        # Get id of project selected
        x = db.execute("SELECT id FROM projects WHERE project_name = :project_name",
        project_name = session["s"])
        project_id = x[0]["id"]

        # Get all costs from selected project
        costs = db.execute("SELECT costs.id, unit, currency, quantity, unit_cost, total_cost, cost_name FROM costs JOIN projects ON project_id = projects.id WHERE projects.id = :project_id",
        project_id = project_id)

        project_total = 0
        for cost in costs:
            project_total += cost["total_cost"]

        return render_template("breakdown.html", costs = costs, s = session["s"], project_total = project_total)





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





@app.route("/new", methods=["GET", "POST"])
@login_required
def new():
    """ Create new project """

    # If user submits new project name
    if request.method == 'POST':

        # Get project name submitted by user
        project_name = request.form.get("projectName")

        # Check if user already has project with this name
        rows = db.execute("SELECT project_name FROM projects WHERE user_id = :user_id AND project_name = :project_name",
        user_id = session["user_id"], project_name = project_name)

        # If project name exists, prompt user for another
        # by using if statement in template file to render
        # a form with error message
        if rows:
            return render_template("new.html", project_name=project_name, rows=rows)

        # If project name is new:
        else:

            # Insert new project into database
            db.execute("INSERT INTO projects (user_id, project_name) VALUES (:user_id, :project_name)",
            user_id = session["user_id"], project_name = project_name)

            # Direct user to projects page
            return redirect("/projects")

    # Gets new project form
    else:
        return render_template("new.html")






@app.route("/projects", methods=["GET", "POST"])
@login_required
def about():

    # If project view or delete form submitted
    if request.method == "POST":

        # If view project form submitted
        if 'projectName' in request.form:
            # Get project name
            s = request.form.get("projectName")

            # Stores project name as global variable
            session["s"] = s

            # Get id of project selected
            x = db.execute("SELECT id FROM projects WHERE project_name = :project_name",
            project_name = s)
            project_id = x[0]["id"]

            # Get costs of current project
            costs = db.execute("SELECT cost_name, total_cost FROM costs JOIN projects ON projects.id = costs.project_id WHERE costs.project_id = :project_id",
            project_id = project_id)

            # if costs is empty, inform user
            if not costs:
                return render_template("empty.html", s = session["s"])

            else:
                return redirect("/breakdown")

        # If delete project form submitted
        elif 'deleteProject' in request.form:

            # Get project id
            project_id = request.form.get("deleteProject")

            # Get project name
            l = db.execute("SELECT project_name FROM projects WHERE id = :project_id",
            project_id = project_id)
            project_name = l[0]["project_name"]

            # flash confirmation alert
            flash(f"{project_name} deleted from projects")

            # Delete project from database
            db.execute("DELETE FROM projects WHERE id = :project_id",
            project_id = project_id)
            return redirect("/projects")

    # If projects page requested
    else:

        # Get all of current users projects
        projects = db.execute("SELECT project_name, projects.id, SUM(total_cost) as project_cost, currency FROM projects LEFT JOIN costs ON projects.id = project_id WHERE user_id = :user_id GROUP BY project_name",
            user_id = session["user_id"])

        # Render table showing projects
        return render_template("projects.html", projects = projects)






@app.route("/register", methods=["GET", "POST"])
def register():

    # If register form submitted
    if request.method == "POST":

        # Get username from user input
        username = request.form.get("username")

        # Get password from user input
        ptxt_password = request.form.get("password")

        # Get confirmation from user input
        confirm = request.form.get("confirmation")

        # Check username does not exist
        rows = db.execute("SELECT * from users WHERE username = :username", username = username)
        if rows:
            return apology("That username already exists, please choose another")

        # Encrypt user password
        password = generate_password_hash(ptxt_password)

        # Add username and password to database
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :password)", username = username, password = password)


        # direct user to login
        return redirect("/login")

    # If register form requested
    else:
        return render_template("register.html")
