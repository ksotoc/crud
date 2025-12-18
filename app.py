import os
import uuid
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for
from flask_mysqldb import MySQL
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import Config


app = Flask(__name__)
app.config.from_object(Config)

# Carpeta para imágenes
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

mysql = MySQL(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


def guardar_imagen(imagen):
    """
    Guarda una imagen en disco con nombre único
    y retorna el nombre del archivo guardado.
    """
    if imagen and imagen.filename != '':
        extension = os.path.splitext(imagen.filename)[1]
        nombre_unico = f"{uuid.uuid4()}{extension}"
        nombre_seguro = secure_filename(nombre_unico)

        ruta = os.path.join(app.config['UPLOAD_FOLDER'], nombre_seguro)
        imagen.save(ruta)

        return nombre_seguro

    return None

def eliminar_imagen(nombre_imagen):

    if nombre_imagen:
        ruta = os.path.join(app.config['UPLOAD_FOLDER'], nombre_imagen)
        if os.path.exists(ruta):
            os.remove(ruta)


def actualizar_imagen(imagen_nueva, imagen_actual):

    if imagen_nueva and imagen_nueva.filename != '':
        eliminar_imagen(imagen_actual)
        return guardar_imagen(imagen_nueva)

    return imagen_actual



class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()

    if user:
        return User(user[0], user[1], user[2])
    return None


@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[2], password):
            login_user(User(user[0], user[1], user[2]))
            return redirect(url_for('productos'))

    return render_template('auth/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, password)
        )
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('login'))

    return render_template('auth/register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/productos')
@login_required
def productos():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products")
    productos = cur.fetchall()
    cur.close()

    return render_template('productos/index.html', productos=productos)


@app.route('/productos/crear', methods=['GET', 'POST'])
@login_required
def crear_producto():
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        imagen = request.files['imagen']

        nombre_imagen = guardar_imagen(imagen)

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO products (nombre, descripcion, precio, imagen)
            VALUES (%s, %s, %s, %s)
        """, (nombre, descripcion, precio, nombre_imagen))
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('productos'))

    return render_template('productos/crear.html')



@app.route('/productos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_producto(id):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        imagen_nueva = request.files.get('imagen')

        cur.execute("SELECT imagen FROM products WHERE id = %s", (id,))
        imagen_actual = cur.fetchone()[0]

        nombre_imagen = actualizar_imagen(imagen_nueva, imagen_actual)

        cur.execute("""
            UPDATE products
            SET nombre = %s,
                descripcion = %s,
                precio = %s,
                imagen = %s
            WHERE id = %s
        """, (nombre, descripcion, precio, nombre_imagen, id))

        mysql.connection.commit()
        cur.close()

        return redirect(url_for('productos'))

    cur.execute("SELECT * FROM products WHERE id = %s", (id,))
    producto = cur.fetchone()
    cur.close()

    return render_template('productos/editar.html', producto=producto)


@app.route('/productos/eliminar/<int:id>')
@login_required
def eliminar_producto(id):
    cur = mysql.connection.cursor()

    # Obtener nombre de la imagen
    cur.execute("SELECT imagen FROM products WHERE id = %s", (id,))
    resultado = cur.fetchone()

    if resultado:
        nombre_imagen = resultado[0]
        eliminar_imagen(nombre_imagen)  # elimina archivo físico

        # Eliminar registro
        cur.execute("DELETE FROM products WHERE id = %s", (id,))
        mysql.connection.commit()

    cur.close()
    return redirect(url_for('productos'))



if __name__ == '__main__':
    app.run(debug=True)
