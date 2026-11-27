// Ayudas de interfaz compartidas: crear elementos, mensajes, confirmaciones y formatos.

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

export function avisar(titulo, texto = "", tipo = "exito") {
  const contenedor = document.getElementById("mensajes");
  const mensaje = el("div", { clase: `mensaje mensaje--${tipo}`, role: tipo === "error" ? "alert" : "status" },
    el("strong", {}, titulo), texto);
  contenedor.append(mensaje);
  setTimeout(() => mensaje.remove(), tipo === "error" ? 9000 : 5000);
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

// --- Fechas: siempre en hora local, como el servidor (ADR-0009) ---------------
export const DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
  "septiembre", "octubre", "noviembre", "diciembre"];

export function nombreMes(numero) {
  return MESES[numero - 1];
}

export function aFecha(texto) {
  const [a, m, d] = texto.slice(0, 10).split("-").map(Number);
  return new Date(a, m - 1, d);
}

export function isoFecha(fecha) {
  const m = String(fecha.getMonth() + 1).padStart(2, "0");
  const d = String(fecha.getDate()).padStart(2, "0");
  return `${fecha.getFullYear()}-${m}-${d}`;
}

export function sumarDias(fecha, dias) {
  const copia = new Date(fecha);
  copia.setDate(copia.getDate() + dias);
  return copia;
}

export function hora(textoIso) {
  return textoIso.slice(11, 16);
}

export function fechaCorta(textoIso) {
  const fecha = aFecha(textoIso);
  return `${DIAS[(fecha.getDay() + 6) % 7].slice(0, 3)} ${fecha.getDate()} ${MESES[fecha.getMonth()].slice(0, 3)}`;
}

// "1 de noviembre de 2026 a las 00:05": en 24 h, como el resto de la interfaz.
// El texto ISO viene sin zona horaria y se lee como hora local (ADR-0009).
const FECHA_Y_HORA = new Intl.DateTimeFormat("es-CR", { dateStyle: "long", timeStyle: "short", hourCycle: "h23" });

export function fechaHora(textoIso) {
  return FECHA_Y_HORA.format(new Date(textoIso.slice(0, 19)));
}

export function colones(texto) {
  return `₡${Number(texto).toLocaleString("es-CR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function decimal(texto) {
  return Number(texto).toLocaleString("es-CR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function horas(numero) {
  return `${Number(numero).toLocaleString("es-CR", { maximumFractionDigits: 2 })} h`;
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

export function insigniaEstado(estado) {
  const [texto, tono] = ESTADOS[estado] || [estado, ""];
  return el("span", { clase: `insignia insignia--${tono}` }, texto);
}
