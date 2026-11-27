// Ayudas para construir la interfaz: crear elementos, mensajes, confirmaciones e
// insignias de estado. Los formatos de fechas y montos están en formatos.js.

export function el(etiqueta, atributos = {}, ...hijos) {
  const nodo = document.createElement(etiqueta);
  for (const [clave, valor] of Object.entries(atributos)) {
    if (valor === false || valor === null || valor === undefined) continue;
    if (clave.startsWith("on")) nodo.addEventListener(clave.slice(2), valor);
    else if (clave === "clase") nodo.className = valor;
    else nodo.setAttribute(clave, valor === true ? "" : valor);
  }
  for (const hijo of hijos.flat()) {
    if (hijo === null || hijo === undefined || hijo === false) continue;
    nodo.append(hijo instanceof Node ? hijo : document.createTextNode(String(hijo)));
  }
  return nodo;
}

// Títulos en lenguaje del usuario para cada código de error del dominio.
// El detalle (qué turno choca, cuántas horas lleva...) viene del servidor.
const TITULOS = {
  "E-NO-AUTORIZADO": "No tiene permiso para esto",
  "E-NO-ENCONTRADO": "No se encontró",
  "E-INTERVALO-INVALIDO": "Revise las horas",
  "E-DATO-INVALIDO": "Revise los datos",
  "E-EN-EL-PASADO": "Esa hora ya pasó",
  "E-ASISTENTE-INACTIVO": "El asistente ya no está activo",
  "E-TRASLAPE": "Choca con otro turno del asistente",
  "E-LABORATORIO-CUBIERTO": "El laboratorio ya tiene responsable a esa hora",
  "E-TOPE-SEMANAL": "Supera el tope semanal de horas",
  "E-TRANSICION-INVALIDA": "Ya no se puede hacer ese cambio",
  "E-MAQUINA-FUERA-DE-SERVICIO": "Máquina fuera de servicio",
  "E-RESERVA-MUY-LARGA": "Máximo 2 horas por reserva",
  "E-LABORATORIO-CERRADO": "El laboratorio estará cerrado",
  "E-MAQUINA-OCUPADA": "Esa máquina ya está reservada",
  "E-RESERVA-ACTIVA-EXISTENTE": "Ya tiene una reserva activa",
  "E-LIMITE-SEMANAL-RESERVAS": "Llegó al máximo de 6 horas semanales",
  "E-MES-NO-TERMINADO": "El mes todavía no termina",
  "E-MES-YA-CERRADO": "Ese mes ya está cerrado",
  "E-SIN-TARIFARIO": "Faltan las tarifas",
  "SIN-CONEXION": "Sin conexión",
};

// Ícono decorativo de Lucide (web/iconos). Va siempre junto a un texto que dice lo
// mismo, así que se oculta al lector de pantalla para que no lo repita.
export function icono(nombre) {
  return el("span", { clase: `icono icono--${nombre}`, "aria-hidden": "true" });
}

export function avisar(titulo, texto = "", tipo = "exito") {
  const contenedor = document.getElementById("mensajes");
  const mensaje = el("div", { clase: `mensaje mensaje--${tipo}` },
    icono(tipo === "error" ? "circle-alert" : "circle-check"),
    // El rol va en el texto y no en todo el mensaje, para que el lector de pantalla
    // anuncie el mensaje sin leer también el botón de cerrar.
    el("div", { clase: "mensaje__texto", role: tipo === "error" ? "alert" : "status" }, el("strong", {}, titulo), texto),
    el("button", { clase: "mensaje__cerrar", type: "button", "aria-label": "Cerrar mensaje", onclick: () => mensaje.remove() },
      icono("x")));
  contenedor.append(mensaje);
  // Los de éxito se van solos. Los errores se quedan hasta que se cierran, para que dé
  // tiempo de leer qué pasó y qué hacer (H9, WCAG 2.2.1).
  if (tipo !== "error") setTimeout(() => mensaje.remove(), 5000);
}

export function avisarError(error) {
  avisar(TITULOS[error.codigo] || "No se pudo completar", error.message, "error");
}

export function confirmar(titulo, texto, textoBoton = "Confirmar") {
  const dialogo = document.getElementById("dialogo");
  document.getElementById("dialogo-titulo").textContent = titulo;
  document.getElementById("dialogo-texto").textContent = texto;
  document.getElementById("dialogo-confirmar").textContent = textoBoton;
  return new Promise((resolver) => {
    dialogo.addEventListener("close", () => resolver(dialogo.returnValue === "confirmar"), { once: true });
    dialogo.showModal();
  });
}

const ESTADOS = {
  CONFIRMADO: ["Confirmado", "exito"],
  PENDIENTE_ACEPTACION: ["Pendiente de aceptación", "aviso"],
  RECHAZADO: ["Rechazado", "peligro"],
  ACTIVA: ["Activa", "exito"],
  EN_USO: ["En uso", "exito"],
  LIBERADA: ["Liberada por ausencia", "peligro"],
  CANCELADA: ["Cancelada", "peligro"],
};

// El ícono refuerza el color, pero el estado siempre se lee en el texto (WCAG 1.4.1).
const ICONO_DEL_TONO = { exito: "check", aviso: "clock", peligro: "x" };

export function insigniaEstado(estado) {
  const [texto, tono] = ESTADOS[estado] || [estado, ""];
  return el("span", { clase: `insignia insignia--${tono}` }, ICONO_DEL_TONO[tono] ? icono(ICONO_DEL_TONO[tono]) : null, texto);
}
