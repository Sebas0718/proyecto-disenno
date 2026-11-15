// Punto de entrada: sesión simulada, pestañas por rol y avisos.
import { api, usarUsuario } from "./api.js";
import { avisarError, el } from "./ui.js";
import * as cierre from "./vistas/cierre.js";
import * as horario from "./vistas/horario.js";
import * as reservas from "./vistas/reservas.js";
import * as turnos from "./vistas/turnos.js";

const CLAVE_USUARIO = "compulab.usuario";

// Qué ve cada rol (principio de "reconocer antes que recordar": solo aparecen
// las secciones que la persona puede usar).
function seccionesPara(yo) {
  if (yo.rol === "COORDINADOR_SOPORTE") {
    return [
      { id: "horario", titulo: "Horario de laboratorios", vista: horario },
      { id: "cierre", titulo: "Cierre de mes", vista: cierre },
    ];
  }
  if (yo.rol === "COORDINADOR_LABORATORIO") {
    return [{ id: "horario", titulo: "Horario de mi laboratorio", vista: horario }];
  }
  const secciones = [{ id: "reservas", titulo: "Reservar máquina", vista: reservas }];
  if (yo.es_asistente) secciones.unshift({ id: "turnos", titulo: "Mis turnos", vista: turnos });
  return secciones;
}

const GRUPOS = [
  ["COORDINADOR_SOPORTE", "Coordinación de soporte"],
  ["COORDINADOR_LABORATORIO", "Coordinación de laboratorio"],
  ["ASISTENTE", "Asistentes"],
  ["ESTUDIANTE", "Estudiantes"],
];

function leerPreferencia() {
  try {
    return localStorage.getItem(CLAVE_USUARIO);
  } catch {
    return null;
  }
}

function guardarPreferencia(id) {
  try {
    localStorage.setItem(CLAVE_USUARIO, id);
  } catch {
    /* sin almacenamiento: no pasa nada */
  }
}

async function iniciar() {
  const selector = document.getElementById("usuario");
  let usuarios;
  try {
    usuarios = await api.usuarios();
  } catch (error) {
    avisarError(error);
    return;
  }
  for (const [rol, titulo] of GRUPOS) {
    const del_grupo = usuarios.filter((u) =>
      rol === "ASISTENTE" ? u.es_asistente : rol === "ESTUDIANTE" ? u.rol === rol && !u.es_asistente : u.rol === rol,
    );
    if (!del_grupo.length) continue;
    selector.append(
      el("optgroup", { label: titulo },
        del_grupo.map((u) => el("option", { value: u.id }, u.laboratorio_id ? `${u.nombre} (${u.laboratorio_id})` : u.nombre))),
    );
  }
  // Enlace directo para la demo: ?usuario=CL-1&seccion=horario
  const parametros = new URLSearchParams(location.search);
  seccionPedida = parametros.get("seccion");
  const guardado = parametros.get("usuario") || leerPreferencia();
  if (guardado && usuarios.some((u) => u.id === guardado)) selector.value = guardado;
  selector.addEventListener("change", () => entrar(selector.value));
  document.getElementById("avisos-boton").addEventListener("click", alternarAvisos);
  await entrar(selector.value);
}

let contexto = null;
let seccionPedida = null;

async function entrar(usuarioId) {
  usarUsuario(usuarioId);
  guardarPreferencia(usuarioId);
  try {
    const yo = await api.yo();
    contexto = { yo, refrescarAvisos };
    pintarAvisos(yo.avisos);
    pintarPestanas(seccionesPara(yo));
  } catch (error) {
    avisarError(error);
  }
}

function pintarPestanas(secciones) {
  const lista = document.getElementById("pestanas");
  lista.replaceChildren(
    ...secciones.map((s, i) =>
      el("li", { role: "presentation" },
        el("button", {
          clase: "pestana", role: "tab", id: `pestana-${s.id}`, "aria-selected": i === 0 ? "true" : "false",
          onclick: () => abrir(s, secciones),
        }, s.titulo)),
    ),
  );
  const pedida = secciones.find((s) => s.id === seccionPedida);
  seccionPedida = null;
  abrir(pedida || secciones[0], secciones);
}

async function abrir(seccion, secciones) {
  for (const s of secciones) {
    document.getElementById(`pestana-${s.id}`).setAttribute("aria-selected", s === seccion ? "true" : "false");
  }
  const contenido = document.getElementById("contenido");
  contenido.replaceChildren(el("p", { clase: "vacio" }, "Cargando…"));
  try {
    await seccion.vista.mostrar(contenido, contexto);
  } catch (error) {
    contenido.replaceChildren(el("p", { clase: "nota nota--peligro" }, error.message));
  }
}

async function refrescarAvisos() {
  try {
    const yo = await api.yo();
    contexto.yo = yo;
    pintarAvisos(yo.avisos);
  } catch {
    /* los avisos no son críticos */
  }
}

function pintarAvisos(avisos) {
  const contador = document.getElementById("avisos-contador");
  contador.textContent = String(avisos.length);
  contador.hidden = avisos.length === 0;
  document.getElementById("avisos-lista").replaceChildren(
    ...(avisos.length
      ? avisos.map((a) => el("li", {}, el("strong", {}, a.asunto), el("br"), a.mensaje))
      : [el("li", { clase: "vacio" }, "No tiene avisos.")]),
  );
}

function alternarAvisos() {
  const panel = document.getElementById("avisos-panel");
  panel.hidden = !panel.hidden;
  document.getElementById("avisos-boton").setAttribute("aria-expanded", String(!panel.hidden));
}

iniciar();
