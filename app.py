from flask import *
from datetime import timedelta
import sqlite3
import time
from datetime import datetime
import hashlib
from hashlib import sha256
import os
import mysql.connector
import base64
from string import *
from base64 import b64encode
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity


finalDate = datetime.now().strftime('%B %d %Y')

app = Flask(__name__)

db = sqlite3.connect('database.db', check_same_thread=False)

cursor = db.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username VARCHAR(255), email VARCHAR(255), password VARCHAR(255), gender VARCHAR(255), profile_picture BLOB, ip VARCHAR(255), creationDate VARCHAR(255), role VARCHAR(255))")
cursor.execute("CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, content VARCHAR(255), notiOwner VARCHAR(255))")
cursor.execute("CREATE TABLE IF NOT EXISTS bans (id INTEGER PRIMARY KEY AUTOINCREMENT, username VARCHAR(255), ban_reason VARCHAR(255), reviewed VARCHAR(255), moderator VARCHAR(255))")
cursor.execute("CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, author VARCHAR(255), postedOn VARCHAR(255), content VARCHAR(255))")
cursor.execute("CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, reporter VARCHAR(255), reported VARCHAR(255), reason VARCHAR(255))")
cursor.execute("CREATE TABLE IF NOT EXISTS warnings (id INTEGER PRIMARY KEY AUTOINCREMENT, username VARCHAR(255), warning_type VARCHAR(255), content VARCHAR(255), moderator VARCHAR(255), reviewed_on VARCHAR(255))")
cursor.execute("CREATE TABLE IF NOT EXISTS private_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, reciever VARCHAR(255), sender VARCHAR(255), content VARCHAR(255), creationDate VARCHAR(255))")

cursor.execute("UPDATE users SET role = 'Admin' WHERE username = 'youssef'")

def turnToStr(var):
    if var is None:
        return ""
    return str(var).translate(str.maketrans("", "", "'[](),"))

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
app.config['JWT_SECRET_KEY'] = os.environ.get('SECRET_KEY')
jwt = JWTManager(app)
app.permanent_session_lifeitme = timedelta(days=50)

def get_users():
	cursor.execute("SELECT * FROM users")
	res = cursor.fetchall()
	return len(res)

def get_password(username):
	cursor.execute("SELECT password FROM users WHERE username = ?",[username])
	return turnToStr(cursor.fetchone())

ip = "";

@app.route("/", methods=["POST", "GET"])
def sign_up():
	if request.method == "POST":
		session.permanent = True
		username = request.form['username']
		password = request.form["password"]
		encoded_password = sha256(password.encode('utf-8')).hexdigest()
		email = request.form['email']
		gender = request.form['gender']
		with open("static/default.png", "rb") as f:
			image = f.read()
		if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
			ip = request.environ['REMOTE_ADDR']
		else:
			ip = request.environ['HTTP_X_FORWARDED_FOR']
		gender = "Female" if gender == "2" else "Male"
		try:
			cursor.execute("INSERT INTO users (username, email, password, gender, profile_picture, ip, creationDate, role) VALUES (?,?,?,?,?,?,?,?)",(username,email,encoded_password,gender,image,ip,finalDate,"User"))
			db.commit()
			session["username"] = username
			session["role"] = "User"
			session["isBanned"] = False
			session["canPost"] = True
			session["gender"] = gender
			session["experiments"] = []
			return redirect(url_for('home'))
		except mysql.connector.errors.IntegrityError:
			flash("Username is already taken.", "error")
			return redirect(url_for('sign_up'))
	else:
		if "username" in session:
			return redirect(url_for("home"))
		return render_template("sign_up.html")

def unbanUser(username):
    cursor.execute("DELETE FROM bans WHERE username = ?", [username])
    db.commit()

def getIP(username):
    cursor.execute("SELECT ip FROM users WHERE username = ?", [username])
    return turnTostr(cursor.fetchone())

def banUs(username, reason):
    cursor.execute("INSERT INTO bans (username, ban_reason, reviewed, moderator) VALUES (?,?,?,?)", (username, reason, finalDate, session["username"]))
    db.commit()

def purgeAllPosts(usernamePURGE):
    cursor.execute("UPDATE posts SET content = ? WHERE author = ?", ("[Content deleted]", usernamePURGE))
    db.commit()

def getPassword(username):
    cursor.execute("SELECT password FROM users WHERE username = ?", [username])
    return turnToStr(cursor.fetchone())

def getCreation(username):
    cursor.execute("SELECT creationDate FROM users WHERE username = ?", [username])
    return turnTostr(cursor.fetchone())

def getGender(username):
    cursor.execute("SELECT gender FROM users WHERE username = ?", [username])
    return turnToStr(cursor.fetchone())

def getNA(username):
    cursor.execute("SELECT id FROM notifications WHERE notiOwner = ?", [username])
    res = cursor.fetchall()
    return int(len(res))

def getRole(username):
    cursor.execute("SELECT role FROM users WHERE username = ?", [username])
    return turnToStr(cursor.fetchone())

def checkIsBanned(username):
    cursor.execute("SELECT id FROM bans WHERE username = ?", [username])
    res = cursor.fetchall()
    return len(res) >= 1

def warnUser(username, reason, warning_type):
    cursor.execute("INSERT INTO warnings (username, warning_type, content, moderator, reviewed_on) VALUES (?,?,?,?,?)", (username, warning_type, reason, session["username"], finalDate))
    db.commit()

def checkIsValid(username):
    cursor.execute("SELECT username FROM users WHERE username = ?", [username])
    res = cursor.fetchall()
    return len(res) >= 1

def getWarningLevel(username):
    cursor.execute("SELECT warning_type FROM warnings WHERE username = ?", [username])
    return turnToStr(cursor.fetchone())

@app.route("/home", methods=["POST", "GET"]) 
def home():
	if "username" in session:
		username = session["username"]
		isBanned = session["isBanned"]
		gender = turnToStr(session["gender"])
		role = session["role"]
		if isBanned:
			return redirect(url_for("suspended"))
		return render_template("home.html", role=role, username=username, gender=gender, noAm=getNA(session["username"]))
	else:
		return redirect(url_for("sign_up"))

@app.route("/unban/<username>")
def unbanus(username):
	if session["username"] and session["role"] == "Admin":
		unbanUser(username)
		flash("Sucesfully unbanned user", "success")
		return redirect(url_for("ban_list"))
	else:
		abort(403)

@app.route("/warnings")
def warnings():
	if "username" in session:
		cursor.execute("SELECT * FROM warnings WHERE username = ?",[session["username"]])
		warn = cursor.fetchall()
		if session["isBanned"]:
			return redirect(url_for("suspended"))
		return render_template("warnings.html", warn=warn)
	else:
		return redirect(url_for("login"))

#Error handlers
@app.errorhandler(404)
def page_not_found(e):
	 return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden(e):
	return render_template("403.html"), 403

@app.route("/login", methods=["POST", "GET"])
def login():
	if request.method == "POST":
		session.permanent = True
		username = request.form['username']
		password = request.form['password']
		password = sha256(password.encode('utf-8')).hexdigest()
		cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?",(username,password))
		results = cursor.fetchall()
		if len(results) <= 0:
			flash("Invalid information provided.", "error")
			return redirect(url_for("login"))
		else:
			session["username"] = username
			session["experiments"] = []
			session["gender"] = turnToStr(getGender(username))
			session["canPost"] = True
			warningLevel = getWarningLevel(session["username"])
			if warningLevel == "3":
				session["canPost"] = False
			cursor.execute("SELECT * FROM bans WHERE username = ?",[session["username"]])
			res = cursor.fetchall()
			if len(res) > 0:
				# The user is banned now time to let the website know that the user is banned
				session["isBanned"] = True
			else:
				session["isBanned"] = False
			userList = [session["username"]]
			cursor.execute("SELECT role FROM users WHERE username = ?", userList)
			role = cursor.fetchone()
			role = str(role).replace("(", '')
			role = str(role).replace(")", '')
			role = str(role).replace("'", '')
			role = str(role).replace(",", '')
			session["role"] = role
			return redirect(url_for('home'))
	else:
		if "username" in session:
			return redirect(url_for("home"))
		return render_template("login.html")

@app.route("/users/<Profileid>")
def users(Profileid):
    if "username" in session:
        role = session["role"]
        cursor.execute("SELECT * FROM users WHERE id = ?", [Profileid])
        res = cursor.fetchone()
        if res is None:
            abort(404)
        if session["isBanned"]:
            return redirect(url_for('suspended'))
        cursor.execute("SELECT username FROM users WHERE id = ?",[Profileid])
        username = str(cursor.fetchone()[0])
        if checkIsBanned(username):
            abort(404)
        return render_template("profile.html", profileData=res, role=role)
    else:
        return redirect(url_for("login"))

@app.route("/delete-post/<postId>", methods=["POST", "GET"])
def delete_post(postId):
	if session["isBanned"]:
		return redirect(url_for("suspended"))
	cursor.execute("SELECT author FROM posts WHERE id = ?",[postId])
	val = cursor.fetchone()
	val = turnToStr(val)
	if session["username"] == val or 0 in session["experiments"]:
		data_list = [postId]
		cursor.execute("DELETE FROM posts WHERE id = ?",data_list)
		db.commit()
		flash("Sucesfully deleted post", "success")
		return redirect(url_for("posts"))
	else:
		abort(403)

@app.route("/report/<username>", methods=["POST", "GET"])
def report(username):
	if request.method == "POST":
		reason = request.form['reason']
		reporter = session["username"]
		reported = username
		cursor.execute("INSERT INTO reports (reporter, reported, reason) VALUES (?,?,?)",(reporter,reported,reason))
		db.commit()
		flash(f"Sucesfully reported {reported}", "success")
		return redirect(url_for("report", username=username))
	else:
		if "username" in session:
			isBanned = session["isBanned"]
			if isBanned:
				return redirect(url_for("suspended"))
		else:
			return redirect(url_for("login"))
		return render_template("report.html", reported=username)


@app.route("/messages")
def messages():
	if "username" in session:
		if session["isBanned"]:
			return redirect(url_for("suspended"))
		cursor.execute("SELECT * FROM private_messages WHERE reciever = ?",[session["username"]])
		messages = cursor.fetchall()
		return render_template("messages.html", messages=messages)
	else:
		return redirect(url_for("login"))

@app.route("/send-pm", methods=["POST", "GET"])
def send_pm():
	if request.method == "POST":
		username = request.form['username']
		content = request.form['content']
		cursor.execute("INSERT INTO private_messages (reciever,sender,content,creationDate) VALUES (?,?,?,?)",(username,session["username"],content,finalDate))
		db.commit()
		flash("Sucesfully sent private message!", "success")
		return redirect(url_for('send_pm'))
	else:
		if "username" not in session:
			return redirect(url_for('login'))
		elif session["isBanned"]:
			return redirect(url_for('suspended'))
		else:
			return render_template("send_pm.html")

@app.route("/posts")
def posts():
	if "username" in session:
		username = session["username"]
		role = session["role"]
		cursor.execute("SELECT * FROM posts")
		posts = cursor.fetchall()
		if session['isBanned']:
			return redirect(url_for("suspended"))
		return render_template("posts.html", rank=role, posts=posts)
	else:
		return redirect(url_for("login"))

@app.route("/check-reports/<user>")
def checkUserReports(user):
	if "username" in session:
		if session["role"] == "Admin":
			cursor.execute("SELECT * FROM reports WHERE reported = ?",[user])
			return render_template("userWarnings.html", warnings=cursor.fetchall())
		else:
			abort(403)
	else:
		return redirect(url_for("login"))



@app.route('/image/<username>')
def get_image(username):
    cursor.execute('SELECT profile_picture FROM users WHERE username = ?',[username])
    image_data = cursor.fetchone()[0]
    
    return Response(image_data, mimetype='image/jpeg')


@app.route("/upload-pic", methods=["POST", "GET"])
def upload_pic():
	if session["isBanned"]:
		return redirect(url_for('suspended'))
	if request.method == "POST":
		image_data = request.files['image'].read()
		cursor.execute("UPDATE users SET profile_picture = ? WHERE username = ?",(image_data,session["username"]))
		db.commit()
		flash("Sucesfully uploaded a image", "success")
		return redirect(url_for("upload_pic"))
	else:
		return render_template("upload_image.html")


@app.route("/warn", methods=["POST", "GET"])
def warn_user():
	if session["role"] == "Admin":
		if request.method == "POST":
			username = request.form['username']
			reason = request.form['reason']
			warning_type = request.form['warning_type']
			if session["role"] != "Admin":
				abort(403)
			else:
				cursor.execute("INSERT INTO warnings (username, warning_type, content, moderator, reviewed_on) VALUES (?,?,?,?,?)",(username,warning_type,reason,session["username"],finalDate))
				db.commit()
				flash(f"Warned {username} sucesfully", "success")
				return redirect(url_for("warn_user"))
				if warning_type == "2":
					purgeAllPosts(username)
				elif warning_type == "3":
					pass
				elif warning_type == "4":
					banUs(username, "Having a warning with level of 4")
		return render_template("warn.html")
	else:
		abort(403)

@app.route("/create-post", methods=["POST", "GET"])
def create_post():
	if session["canPost"] == False:
		return "<h1>Your posting ability has been revoked.</h1>"
	if request.method == "POST":
		author = session["username"]
		post = request.form["text"]
		postedOn = finalDate
		cursor.execute("INSERT INTO posts (author, postedOn, content) VALUES (?,?,?)",(author, postedOn, post))
		db.commit()
		flash("Sucesfully added post", "success")
		return redirect(url_for("posts"))
	else:
		if "username" in session:
			return render_template("newPost.html")
		if session["isBanned"]:
			return redirect(url_for('suspended'))
		else:
			return redirect(url_for('login'))


@app.route("/edit-post/<postId>", methods=["POST", "GET"])
def edit_post(postId):
	if request.method == "POST":
		newPost = request.form["post"]
		cursor.execute("UPDATE posts SET content = ? WHERE id = ?",(newPost,postId))
		db.commit()
		flash("Sucesfully updated post", "success")
		return redirect(url_for("posts"))
	cursor.execute("SELECT author FROM posts WHERE id = ?",[postId])
	val = cursor.fetchone()
	val = turnToStr(val)
	if session["username"] == val or 0 in session["experiments"]:
		cursor.execute("SELECT content FROM posts WHERE id = ?",[postId])
		postContent = turnToStr(cursor.fetchone())
		if session["isBanned"]:
			return redirect(url_for("suspended"))
		return render_template("edit_post.html", current_content=postContent)
	else:
		abort(403)

@app.route("/settings", methods=["POST", "GET"])
def settings():
	if "username" in session:
		if request.method == "POST":
			if session["role"] == "User":
				abort(403)
			exp = turnToStr(request.form.getlist('experiment'))
			if exp == "0":
				if 0 in session["experiments"]:
					flash("You already got this enabled", "fail")
				else:
					session["experiments"].append(0)
					flash("Sucesfully enabled", "success")
			elif exp == "1":
				if 1 in session["experiments"]:
					flash("You already got this enabled", "fail")
				else:
					session["experiments"].append(1)
					flash("Sucesfully enabled", "success")

			elif exp == "2":
				if 2 in session["experiments"]:
					flash("You already got this enabled", "fail")
				else:
					session["experiments"].append(2)
					access_token = create_access_token(identity=session["username"])
					response = redirect(url_for("settings"))
					response.set_cookie('access_token', access_token)
					flash("Sucesfully enabled", "success")
					return response

			elif exp == "100":
				session["experiments"].pop()
				flash("Sucesfully disabled all experiments", "success")
			return redirect(url_for("settings"))
		else:
			if session["isBanned"]:
				return redirect(url_for("suspended"))
			username = session["username"]
			gender = session["gender"]
			role = session["role"]
			return render_template("settings.html", username=username, gender=gender, role=role)
	else:
		return redirect(url_for("login"))


@app.route("/settings/username", methods=["POST", "GET"])
def changeUser():
	if request.method == "POST":
		newUser = request.form["newUsername"]
		try:
			cursor.execute("UPDATE users SET username = ? WHERE username = ?", (newUser, session["username"]))
			db.commit()
			flash("Username updated sucesfully!", "success")
			session["username"] = newUser
			return redirect(url_for("changeUser"))
		except:
			flash("Username is already taken!", "error")
			return redirect(url_for("changeUser"))
	else:
		if "username" in session:
			username = session["username"]
			isBanned = session["isBanned"]
			if isBanned:
				return redirect(url_for('suspended'))
			return render_template("usernameUpdate.html", username=username)
		else:
			return redirect(url_for("login"))

@app.route("/settings/password", methods=["POST", "GET"])
def changePassword():
	if request.method == "POST":
		newPassword = request.form["newPassword"]
		oldPassword = request.form["oldPassword"]
		password2 = request.form["passwordConfirm"]
		oldPassword = sha256(oldPassword.encode('utf-8')).hexdigest()
		currentPassword = getPassword(session["username"])
		if oldPassword != currentPassword:
			flash("Old password does not match with current password!", "error")
			return redirect(url_for("changePassword"))
		elif newPassword != password2:
			flash("Password does not match with the second password!", "error")
			return redirect(url_for("changePassword"))
		else:
			newPassword = sha256(newPassword.encode('utf-8')).hexdigest()
			cursor.execute("UPDATE users SET password = ? WHERE username = ?", (newPassword, session["username"]))
			db.commit()
			flash("Password updated sucesfully", "success")
			return redirect(url_for("changePassword"))
			session.pop("username", None)
			session.pop("isBanned", None)
			session.pop("role", None)
			session.pop("canPost", None)
			flash("Please login again", "error")
			return redirect(url_for("login"))
	else:
		if "username" in session:
			isBanned = session["isBanned"]
			if isBanned:
				return redirect(url_for('suspended'))
			return render_template("passwordUpdate.html")
		else:
			return redirect(url_for("login"))

		

@app.route("/staff-only", methods=["POST", "GET"])
def staff():
	if "username" in session:
		if session["role"] == "Admin":
			if request.method == "POST":
				user = request.form['user']
				reason = request.form['reason']
				warning_type = request.form['warning_type']
				action = turnToStr(request.form.getlist('actions'))
				if action == "ban":
					banUs(user, reason)
					flash(f"Banned {user} sucesfully", "success")
					return redirect(url_for('staff'))
				elif action == "purgeposts":
					purgeAllPosts(user)
					flash("Sucesfully purged all user posts", "success")
					return redirect(url_for("staff"))
				elif action == "warn":
					warnUser(user, reason, warning_type)
					flash("User warned sucesfully","success")
					return redirect(url_for('staff'))
				elif action == "reports":
					return redirect(url_for("checkUserReports", user=user))
				elif action == "unban":
					unbanUser(user)
					flash(f"{user} Has been unbanned sucesfully", "success")
					return redirect(url_for('staff'))

			return render_template("staffOnly.html")
		else:
			abort(403)
	else:
		return redirect(url_for('login'))


	return render_template("staffOnly.html")

@app.route("/search/<username>")
def search(username):
	cursor.execute("SELECT id FROM users WHERE username = ?",[username])
	userId = turnToStr(cursor.fetchone()[0])
	print(userId)
	return redirect(url_for("users", Profileid=userId))

@app.route("/all-users")
def all_users():
	if "username" in session:
		if session["role"] == "Admin":
			cursor.execute("SELECT * FROM users")
			users = cursor.fetchall()
			return render_template("all_users.html", users=users, users_amount=get_users())
		else:
			abort(403)
	else:
		return redirect(url_for("login"))

@app.route("/moderate/<username>", methods=["POST", "GET"])
def moderate(username):
	if "username" in session:
		if session["role"] == "Admin":
			isValid = checkIsValid(username)
			if isValid == True:
				role = getRole(username)
				gender = turnToStr(getGender(username))
				if request.method == "POST":
					rank = request.form["rank"]
					if session["role"] == "Admin":
						cursor.execute("UPDATE users SET role = ? WHERE username = ?",(rank,username))
						db.commit()
						flash("Updated rank sucesfully!", "success")
						return redirect(url_for("moderate", username=username))
					else:
						flash("You do not have permissions!")
						return redirect(url_for("home"))
				else:
					return render_template("moderate.html", role=role, username=username, gender=gender)
			else:
				abort(404)
		else:
			abort(403)
	else:
		return redirect(url_for('login'))

@app.route("/banU/<username>")
def banU(username):
	if "username" in session:
		if session["role"] == "Admin":
			banUs(username, "No reason provided")
			flash("User banned sucesfully", "success")
			return redirect(url_for("moderate", username=username))
		else:
			abort(403)
	else:
		return redirect(url_for("login"))

@app.route("/purge-all-posts/<username>")
def purgeAll(username):
	if "username" in session:
		if session["role"] == "Admin":
			purgeAllPosts(username)
			flash("Purged all user posts sucesfully", "success")
			return redirect(url_for("purgeAll", username=username))
		else:
			abort(403)
	else:
		return redirect(url_for("login"))




@app.route("/staff-only/ban", methods=["POST", "GET"])
def ban():
	if request.method == "POST":
		userToBan = request.form["userBan"]
		banReason = request.form["reason"]
		cursor.execute("SELECT * FROM users WHERE username = ?", [userToBan])
		res = cursor.fetchall()
		if len(res) <= 0:
			flash("User does not exist", "error")
			return redirect(url_for("staff"))
		else:
			if session["role"] == "Admin":
				cursor.execute("INSERT INTO bans (username, ban_reason, reviewed, moderator) VALUES (?,?,?,?)",(userToBan,banReason,finalDate, session["username"]))
				db.commit()
				flash("Banned user sucesfully", "success")
				return redirect(url_for("staff"))
			else:
				flash("You do not have permissions!", "error")
				return redirect(url_for("home"))
	else:
		if "username" in session:
			role = session["role"]
			if role == "Admin":
				cursor.execute("SELECT * FROM bans")
				results = cursor.fetchall()
				return render_template("staffBan.html", results=results)
			else:
				abort(403)
		else:
			return redirect(url_for("login"))

@app.route("/staff-only/unban", methods=["POST", "GET"])
def unban():
	if request.method == "POST":
		userToUnBan = request.form["userunBan"]
		cursor.execute("SELECT * FROM users WHERE username = ?", [userToUnBan])
		res = cursor.fetchall()
		if len(res) <= 0:
			flash("User does not exist", "error")
			return redirect(url_for("staff"))

		else:
			if session["role"] == "Admin":
				cursor.execute("DELETE FROM bans WHERE username = ?", [userToUnBan])
				db.commit()
				flash("Unbanned user sucesfully", "success")
				return redirect(url_for("staff"))
			else:
				flash("You do not have permissions!", "error")
				return redirect(url_for("home"))
	else:
		if "username" in session:
			role = session["role"]
			if role == "Admin":
				cursor.execute("SELECT * FROM bans")
				results = cursor.fetchall()
				return render_template("staffUnban.html", results=results)
			else:
				abort(403)
		else:
			return redirect(url_for("login"))

@app.route("/staff-only/reports")
def reports():
	if "username" in session:
		if session["role"] == "Admin":
			cursor.execute("SELECT * FROM reports")
			reports = cursor.fetchall()
			return render_template("staffReports.html", reports=reports)
		else:
			abort(403)
	else:
		return redirect(url_for("login"))

@app.route("/markDone/<reportId>")
def markDone(reportId):
	if "username" in session:
		if session["role"] == "Admin":
			cursor.execute("DELETE FROM reports WHERE id = ?",[reportId])
			db.commit()
			flash("Sucesfully marked report as done.", "success")
			return redirect(url_for("reports"))
		else:
			abort(403)
	else:
		return redirect(url_for("login"))



@app.route("/suspended")
def suspended():
	if "username" in session:
		if session["role"] == "Admin" or session["isBanned"]:
			cursor.execute("SELECT reviewed FROM bans WHERE username = ?",[session["username"]])
			reviewed = cursor.fetchone()
			reviewed = turnToStr(reviewed)
			cursor.execute("SELECT moderator FROM bans WHERE username = ?", [session["username"]])
			moderator = cursor.fetchone()
			moderator = turnToStr(moderator)
			cursor.execute("SELECT ban_reason FROM bans WHERE username = ?", [session["username"]])
			reason = cursor.fetchone()
			reviewed = turnToStr(reason)
			return render_template("banMessage.html", reviewed=reviewed, moderator=moderator, reason=reason)
		else:
			return redirect(url_for("login"))
	else:
		return redirect(url_for("home"))

@app.route("/ban-list")
def ban_list():
	if "username" in session:
		if session["role"] == "Admin":
			cursor.execute("SELECT * FROM bans")
			bans = cursor.fetchall()
			return render_template("ban_list.html", bans=bans)
		else:
			abort(403)
	else:
		return redirect(url_for("login"))

@app.route("/delete-pm/<pm_id>")
def delete_pm(pm_id):
	if "username" in session:
		if session["isBanned"] == True:
			return redirect(url_for("suspended"))
		cursor.execute("SELECT reciever FROM private_messages WHERE id = ?",[pm_id])
		reciever = turnToStr(cursor.fetchone())
		if reciever != session["username"]:
			abort(403)
		else:
			cursor.execute("DELETE FROM private_messages WHERE id = ?",[pm_id])
			db.commit()
			flash("Sucesfully deleted private message", "success")
			return redirect(url_for("messages"))

	else:
		return redirect(url_for("login"))

@app.route("/logout")
def logout():
	session.pop("username", None)
	session.pop("isBanned", None)
	session.pop("role", None)
	session.pop("gender", None)
	session.pop("canPost", None)
	response = redirect(url_for("login"))
	response.delete_cookie("access_token")
	return response

if __name__ == "__main__":
	app.run(debug=True)