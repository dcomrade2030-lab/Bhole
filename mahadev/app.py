from flask import Flask, render_template, request, redirect, session
import sqlite3, unicodedata, os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "super_secret_key"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def make_searchable(text):
    text = text.lower()
    text = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in text if not unicodedata.combining(c))

def init_db():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS bhajans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT,
        search_title TEXT,
        views INTEGER DEFAULT 0,
        image TEXT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        password TEXT
    )''')

    cur.execute("SELECT COUNT(*) FROM admin")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO admin (password) VALUES ('mahadev123')")

    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/bhajans')
def bhajans():
    search_query = request.args.get('search', '')
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    if search_query:
        q = make_searchable(search_query)
        cur.execute("SELECT * FROM bhajans WHERE title LIKE ? OR search_title LIKE ? ORDER BY id DESC",
                    ('%'+search_query+'%', '%'+q+'%'))
    else:
        cur.execute("SELECT * FROM bhajans ORDER BY id DESC")

    data = cur.fetchall()
    conn.close()
    return render_template("bhajans.html", bhajans=data, search_query=search_query)

@app.route('/bhajan/<int:id>')
def bhajan(id):
    conn = sqlite3.connect("database.db")
    bhajan = conn.execute("SELECT * FROM bhajans WHERE id=?", (id,)).fetchone()
    conn.execute("UPDATE bhajans SET views = views + 1 WHERE id=?", (id,))
    conn.commit()
    conn.close()

    views = bhajan[4] if session.get("admin") else None
    return render_template("bhajan.html", bhajan=bhajan, views=views)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        conn = sqlite3.connect("database.db")
        stored = conn.execute("SELECT password FROM admin WHERE id=1").fetchone()[0]
        conn.close()
        if password == stored:
            session['admin'] = True
            return redirect('/admin')
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/admin', methods=['GET','POST'])
def admin():
    if not session.get('admin'):
        return redirect('/login')

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        search_title = make_searchable(title)
        image_file = request.files.get('image')
        image_name = None

        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_name = filename

        conn = sqlite3.connect("database.db")
        conn.execute("INSERT INTO bhajans (title,content,search_title,image) VALUES (?,?,?,?)",
                     (title, content, search_title, image_name))
        conn.commit()
        conn.close()
        return redirect('/admin')

    conn = sqlite3.connect("database.db")
    data = conn.execute("SELECT * FROM bhajans ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin.html", bhajans=data)

if __name__ == "__main__":
    app.run(debug=True)
