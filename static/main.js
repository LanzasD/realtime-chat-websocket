
// Conecta directamente a la IP del servidor
const socket = io("http://127.0.0.1:5000");

// Envia el mensaje dandole al Enter
const inputTexto = document.getElementById("cajaTexto");
inputTexto.addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
        document.getElementById("botonEnviar").click();
    }
});

// Fuerza el scroll hacia abajo
const listaMensajes = document.getElementById("mensajes");
listaMensajes.scrollTop = listaMensajes.scrollHeight

// Pregunta el nombre al entrar al servidor (Antiguo no sirve)
// const nombreUsuario = prompt("¿Cuál es tu nombre de usuario?")


socket.emit("usuario_conectado", nombreUsuario); // Avisa quien se conecta

// El receptor. Escucha si Python devuelve el JSON
socket.on("mensaje_json", function (datos){
    let nuevoMensaje = document.createElement("li");

    // Le da una clase base
    nuevoMensaje.classList.add("burbuja");

    // Convierte cualquier código malicioso en texto normal
    let textoSeguro = escaparHTML(datos.texto)

    // Evalua de quién es el mensaje para pintarlo a un lado o al otro
    if (datos.usuario === nombreUsuario) {
        nuevoMensaje.classList.add("mensaje-mio");
        // Mensaje propio con la hora en pequeño
        nuevoMensaje.innerHTML = `${textoSeguro} <span class="hora-pequena">${datos.hora}</span>`;

    } else {
        nuevoMensaje.classList.add("mensaje-otro");
        // Mensaje de la otra persona con nombre y hora en pequeño
        nuevoMensaje.innerHTML = `<div class="nombre-autor">${datos.usuario}</div> ${textoSeguro} <span class="hora-pequena">${datos.hora}</span>`;
    }

    document.getElementById("mensajes").appendChild(nuevoMensaje);
    hacerScrollAbajo();
});

// Gestor de avisos de conexión y desconexión

socket.on("aviso", function (msg) {

    // Muestra si el servidor recibe el aviso de unirse o desconectarse
    console.log(">>> AVISO RECIBIDO DEL SERVIDOR: ", msg);

    const listaMensajes = document.getElementById("mensajes");
    const nuevoMensaje = document.createElement("li");

    // Diseño estandar, en todo el medio de la pantalla para que se vea
    nuevoMensaje.style.width = "100%";
    nuevoMensaje.style.alignSelf = "center";
    nuevoMensaje.style.textAlign = "center";
    nuevoMensaje.style.color = "#ffffff";
    nuevoMensaje.style.fontSize = "0.85em";
    nuevoMensaje.style.margin = "10px 0";

    nuevoMensaje.innerHTML = msg; // Con esto importamos directamente el mensaje de Python

    listaMensajes.appendChild(nuevoMensaje);

    // La pantalla también hace scroll para abajo con los avisos
    listaMensajes.scrollTop = listaMensajes.scrollHeight;
});

// El pulsador. Envía lo escrito
document.getElementById("botonEnviar").addEventListener("click", function () {
    let caja = document.getElementById("cajaTexto");
    let texto = caja.value;

    // Si la caja está vacía no permite enviar nada (.trim() limpia los espacios)
    if (texto.trim() !== "") {
        socket.emit("nuevo_mensaje", {
            usuario: nombreUsuario,
            texto: texto
        });
        caja.value = "";
    }
});

let temporizadorEscribiendo; // Guarda el cronómetro

// Detecta cuando tú tocas una tecla en la caja de texto
document.getElementById("cajaTexto").addEventListener("input", function (){
    socket.emit("escribiendo", nombreUsuario)
});

// Detecta si otro usuario toca una tecla en la caja de texto
socket.on("alguien_escribe", function (nombre) {
    let cartel = document.getElementById("estadoEscribiendo");
    cartel.innerText = nombre + " está escribiendo";

    // Reseteamos el cronómetro cada vez que pulsa una tecla
    clearTimeout(temporizadorEscribiendo);

    // Si pasan 2 segundos sin teclear borramos el aviso
    temporizadorEscribiendo =setTimeout( function () {
        cartel.innerText = ""
    }, 2000 );
});

// Función de autoscroll para abajo del chat
function hacerScrollAbajo() {
    let contenedor = document.getElementById("mensajes");
    contenedor.scrollTop = contenedor.scrollHeight;
}

// Detecta los usuarios que hay conectados
socket.on("actualizar_usuarios", function (listaUsuarios){
    const spanUsuarios = document.getElementById("lista-usuarios-online");

    // Convierte el array a un texto separado por comas
    spanUsuarios.innerText = listaUsuarios.join(", ");
});

// Esto evita los ataques de ejecutar código en XSS
function escaparHTML(texto) {
    let div = document.createElement("div");
    div.innerText = texto;
    return div.innerHTML;
}