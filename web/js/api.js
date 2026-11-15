// Cliente de la API. Un solo lugar sabe cómo se habla con el servidor
// (cabecera de sesión, JSON, errores), así las vistas no repiten ese código.

let usuarioActual = null;

export function usarUsuario(id) {
  usuarioActual = id;
}

export class ErrorDeApi extends Error {
  constructor(estado, codigo, mensaje) {
    super(mensaje);
    this.estado = estado;
    this.codigo = codigo;
  }
}

async function pedir(metodo, ruta, cuerpo) {
  const opciones = { method: metodo, headers: {} };
  if (usuarioActual) opciones.headers["X-Usuario-Id"] = usuarioActual;
  if (cuerpo !== undefined) {
    opciones.headers["Content-Type"] = "application/json";
    opciones.body = JSON.stringify(cuerpo);
  }
  let respuesta;
  try {
    respuesta = await fetch(`/api${ruta}`, opciones);
  } catch {
    throw new ErrorDeApi(0, "SIN-CONEXION", "No se pudo conectar con el servidor. Revise su conexión.");
  }
  if (respuesta.ok) {
    const tipo = respuesta.headers.get("content-type") || "";
    return tipo.includes("application/json") ? respuesta.json() : respuesta;
  }
  let datos = {};
  try {
    datos = await respuesta.json();
  } catch {
    /* respuesta sin cuerpo JSON */
  }
  const mensaje = datos.mensaje || datos.detail?.[0]?.msg || datos.detail || "Ocurrió un error inesperado.";
  throw new ErrorDeApi(respuesta.status, datos.codigo || `HTTP-${respuesta.status}`, String(mensaje));
}

export const api = {
  usuarios: () => pedir("GET", "/usuarios"),
  yo: () => pedir("GET", "/yo"),
  laboratorios: () => pedir("GET", "/laboratorios"),
  horario: (lab, fecha) => pedir("GET", `/laboratorios/${lab}/horario?fecha=${fecha}`),
  asistentes: (fecha) => pedir("GET", `/asistentes?fecha=${fecha}`),
  asignarTurno: (datos) => pedir("POST", "/turnos", datos),
  misTurnos: () => pedir("GET", "/mis-turnos"),
  responderTurno: (id, acepta) => pedir("POST", `/turnos/${id}/respuesta`, { acepta }),
  ocupacion: (lab, fecha) => pedir("GET", `/laboratorios/${lab}/ocupacion?fecha=${fecha}`),
  reservar: (datos) => pedir("POST", "/reservas", datos),
  misReservas: () => pedir("GET", "/mis-reservas"),
  cierres: () => pedir("GET", "/cierres"),
  cierre: (anio, mes) => pedir("GET", `/cierres/${anio}/${mes}`),
  cerrarMes: (anio, mes) => pedir("POST", "/cierres", { anio, mes }),
  archivoBecas: (anio, mes) => pedir("GET", `/cierres/${anio}/${mes}/archivo`),
};
