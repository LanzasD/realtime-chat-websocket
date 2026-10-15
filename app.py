from flask import Flask, jsonify, render_template, session, redirect, url_for, request, flash
from flask_socketio import SocketIO, send, emit
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


# Inicia la aplicación en Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = "CrustaceoCrujiente"
usuario_conectados = set()


# Indica a Flask como se llama el archivo
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///chat.db"

# Conecta la base de datos con la app
db = SQLAlchemy(app)

# Envuelve la app de Flask con el motor de WebSockets
socketio = SocketIO(app, cors_allowed_origins="*")
# El * se usa para comodín para poder probarlo en entorno local, por seguridad no debería
# dejar pero al ponerle el * le decimos que lo acepte túneles WebSocket desde cualquier origen

class Mensaje(db.Model):
    id = db.Column(db.Integer, primary_key=True) # Número de serie único
    usuario = db.Column(db.String(50), nullable=False) # Nombre del usuario
    texto = db.Column(db.String(500), nullable=False) #El contenido del mensaje
    hora = db.Column(db.String(10), nullable=False)  # La hora

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Unique=True impide que 2 personas se registren con el mismo nombre
    nombre = db.Column(db.String(50), unique= True, nullable=False)
    #Nuna se guarda la contraseña real, solo un "hash" que es un texto cifrado e irreversible
    password_hash = db.Column(db.String(256), nullable=False)
@app.route("/status", methods=["GET"])
def status():
    """
    Ruta de prueba para saber que el backend responde

    Debería responder 200, conforme está perfecto
    ---
    responses:
        200:
            descriptio: El servidor está funcionando
    """
    return jsonify({"mensaje": "El servidor está funcionando"}), 200

@app.route("/")
def index():
    # Si el usuario no tiene sesión activa, le mandamos a loguearse
    if "usuario" not in session:
        return redirect(url_for("login"))

    # Si tiene usuario dejamos que pasar
    return render_template("index.html", usuario_actual=session["usuario"])

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        # Captura lo que se escribe en el formulario
        nombre = request.form["usuario"]
        password = request.form["password"]

        # Verifica que el empleado no exista.
        if Usuario.query.filter_by(nombre=nombre).first():
            flash("El usuario ya existe", 400)
            return redirect(url_for("registro"))

        # Cifra la contraseña y la guarda en su perfil
        password_cifrada = generate_password_hash(password)
        nuevo_empleado = Usuario(nombre=nombre, password_hash=password_cifrada)

        try:
            db.session.add(nuevo_empleado)
            db.session.commit()
            # Redirige al menú principal
            return redirect(url_for("login"))
        except Exception as e:
            db.session.rollback() # Deshace la operación en caso de error
            return f"Error al crear usuario: {str(e)}", 400
    return render_template("registro.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nombre = request.form["usuario"]
        password = request.form["password"]

        # Buscamos el perfil del empleado
        empleado = Usuario.query.filter_by(nombre=nombre).first()

        # Verifica que exista y que la contraseña coincida con el cifrado
        if empleado and check_password_hash(empleado.password_hash, password):
            # Le da su tarjeta de identificación
            session["usuario"] = empleado.nombre
            # Abre la puerta del chat
            return redirect(url_for("index"))
        else:
            flash("Error: Credenciales incorrectas o usuario no encontrado", 400)
            return redirect(url_for("login"))

    return render_template("login.html")

@socketio.on("nuevo_mensaje")
def handle_nuevo_message(datos):
    print(f"Paquete recibido desde el frontend: {datos}")

    # Captura la hora actual en formato horas y minutos
    hora_actual = datetime.now().strftime("%H:%M")

    # Guarda en la base de datos
    # Envía las piezas del diccionario de JavaScript
    nuevo_msg = Mensaje(usuario=datos["usuario"], texto=datos["texto"], hora=hora_actual)

    db.session.add(nuevo_msg) # Prepara el mensaje
    db.session.commit() # Guarda el mensaje

    # Se trasmite a todos los del chat juntando nombre y el mensaje para que
    # HTML lo enseñe bonito

    paquete = {"hora": hora_actual, "usuario": datos["usuario"], "texto": datos["texto"]}
    emit("mensaje_json", paquete, broadcast=True)

@socketio.on("connect")
def manejar_conexion():
    if "usuario" in session:
        nombre = session["usuario"]
        usuario_conectados.add(session["usuario"])
        # Emite la lista actualizada a todos los que están en el chat
        emit("actualizar_usuarios", list(usuario_conectados), broadcast=True)

        # Añade un emoji y texto en cursiva para poder diferenciarlo
        mensaje_sistema = f"{nombre} se ha unido a la sala"

        # inlcude_self=false hace que no te avise de tu propia entrada
        emit("aviso", mensaje_sistema, broadcast=True, include_self=False)

        # Una vez actualiza la lista, le carga el historial a la persona
        print(f"{nombre} se ha conectado. Cargando historial...")

        # Lee todos los mensajes guardados
        historial = Mensaje.query.all()

        # Los envía uno por uno al nuevo usuario
        for msg in historial:
            paquete= {"hora": msg.hora, "usuario": msg.usuario, "texto": msg.texto}
            emit("mensaje_json", paquete)

# Evento temporal que no toca datos
@socketio.on("escribiendo")
def handle_escribiendo(nombre):

    # incluse_self=False es para que no te salga en pantalla que tu estás escribiendo
    emit("alguien_escribe", nombre, broadcast=True, include_self=False)

with app.app_context():
    db.drop_all() # Destruye toda la base de datos anterior y todo su historial
    db.create_all() # Crea la base de datos en el caso que no exista


@socketio.on('disconnect')
def manejar_desconexion():
    if "usuario" in session and session["usuario"] in usuario_conectados:
        nombre = session["usuario"]
        usuario_conectados.remove(nombre)

        # Avisa que alguien se ha ido
        emit("actualizar_usuarios", list(usuario_conectados), broadcast=True)
        print(f"{nombre} se ha desconectado")
        # Anuncia al chat que esa persona se ha desconectado
        mensaje_sistema =f"{nombre} se ha desconectado"
        emit("aviso", mensaje_sistema, broadcast=True, include_self=False)
@app.route("/logout")
def logout():
    session.pop("usuario", None) # Borra al usuario de la memoria
    return redirect(url_for("login"))

if __name__ == "__main__":
    # Con Debug = True se reinicia solo el servidor con cada cambio que se hace en el código
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)