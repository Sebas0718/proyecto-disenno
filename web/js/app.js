// Punto de entrada: sesión simulada, pestañas por rol y avisos.
import { api, usarUsuario } from "./api.js";
import { avisarError, el, icono } from "./dom.js";
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
      { id: "horario", titulo: "Horario de laboratorios", icono: "calendar-days", vista: horario },
      { id: "cierre", titulo: "Cierre de mes", icono: "receipt", vista: cierre },
    ];
  }
  if (yo.rol === "COORDINADOR_LABORATORIO") {
    return [{ id: "horario", titulo: "Horario de mi laboratorio", icono: "calendar-days", vista: horario }];
  }
  const secciones = [{ id: "reservas", titulo: "Reservar máquina", icono: "monitor", vista: reservas }];
  if (yo.es_asistente) secciones.unshift({ id: "turnos", titulo: "Mis turnos", icono: "calendar-check", vista: turnos });
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
  document.getElementById("pestanas").addEventListener("keydown", moverEntrePestanas);
  document.getElementById("avisos-boton").addEventListener("click", alternarAvisos);
  document.addEventListener("keydown", cerrarAvisosConEscape);
  document.addEventListener("click", cerrarAvisosAlClicFuera);
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

// Pestañas con el patrón de WAI-ARIA (tablist / tab / tabpanel). Solo la pestaña
// abierta entra en el orden del Tab; entre pestañas se pasa con las flechas.
function pintarPestanas(secciones) {
  const lista = document.getElementById("pestanas");
  lista.replaceChildren(
    ...secciones.map((s) =>
      el("li", { role: "presentation" },
        el("button", {
          clase: "pestana", role: "tab", type: "button", id: `pestana-${s.id}`, "aria-controls": "panel",
          "aria-selected": "false", tabindex: "-1",
          onclick: () => abrir(s, secciones),
        }, icono(s.icono), s.titulo)),
    ),
  );
  const pedida = secciones.find((s) => s.id === seccionPedida);
  seccionPedida = null;
  abrir(pedida || secciones[0], secciones);
}

// Flechas izquierda/derecha (dando la vuelta), Inicio y Fin mueven el foco entre
// pestañas; Enter o Espacio abren la pestaña con el foco. La activación es manual, y no
// al mover el foco, porque abrir una pestaña pide datos al servidor (WAI-ARIA APG).
function moverEntrePestanas(evento) {
  const pestanas = [...document.querySelectorAll("#pestanas [role=tab]")];
  const actual = pestanas.indexOf(document.activeElement);
  const destino = { ArrowRight: actual + 1, ArrowLeft: actual - 1, Home: 0, End: pestanas.length - 1 }[evento.key];
  if (actual === -1 || destino === undefined) return;
  evento.preventDefault();
  pestanas[(destino + pestanas.length) % pestanas.length].focus();
}

async function abrir(seccion, secciones) {
  for (const s of secciones) {
    const pestana = document.getElementById(`pestana-${s.id}`);
    pestana.setAttribute("aria-selected", String(s === seccion));
    pestana.setAttribute("tabindex", s === seccion ? "0" : "-1");
  }
  const panel = document.getElementById("panel");
  panel.setAttribute("aria-labelledby", `pestana-${seccion.id}`);
  panel.replaceChildren(el("p", { clase: "vacio" }, "Cargando…"));
  try {
    await seccion.vista.mostrar(panel, contexto);
  } catch (error) {
    panel.replaceChildren(el("p", { clase: "nota nota--peligro" }, error.message));
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

// El panel de avisos se abre y cierra con su botón, con Esc (el foco vuelve al botón)
// o con un clic fuera de él.
function mostrarAvisos(visible) {
  document.getElementById("avisos-panel").hidden = !visible;
  document.getElementById("avisos-boton").setAttribute("aria-expanded", String(visible));
}

function alternarAvisos() {
  mostrarAvisos(document.getElementById("avisos-panel").hidden);
}

function cerrarAvisosConEscape(evento) {
  if (evento.key !== "Escape" || document.getElementById("avisos-panel").hidden) return;
  mostrarAvisos(false);
  document.getElementById("avisos-boton").focus();
}

function cerrarAvisosAlClicFuera(evento) {
  const panel = document.getElementById("avisos-panel");
  const boton = document.getElementById("avisos-boton");
  if (!panel.hidden && !panel.contains(evento.target) && !boton.contains(evento.target)) mostrarAvisos(false);
}

iniciar();
