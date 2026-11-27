// Componentes de interfaz reutilizables, construidos con `el()`. Cada uno arma el
// mismo marcado (y las mismas clases CSS) que antes se repetía a mano en las vistas.
import { avisarError, el } from "./dom.js";
import { isoFecha, sumarDias } from "./formatos.js";

// Campo de formulario con su etiqueta. El `for` sale del id del control, así la
// etiqueta y el campo no se pueden desincronizar (WCAG 1.3.1).
export function campo(etiqueta, control) {
  return el("div", { clase: "grupo" }, el("label", { for: control.id }, etiqueta), control);
}

// Encabezado de pantalla: título, subtítulo con el contexto y, a la derecha, acciones.
export function encabezado(titulo, subtitulo, ...acciones) {
  return el("div", { clase: "encabezado" },
    el("div", {}, el("h1", {}, titulo), subtitulo ? el("p", {}, subtitulo) : null),
    ...acciones);
}

// Sección en tarjeta. Con `titulo` lleva su h2 (con `id`) y queda etiquetada por él.
// Si el título está más adentro, se nombra con `etiquetadaPor` (id de ese título) o,
// si no tiene título visible, con `etiqueta` (aria-label).
export function tarjeta({ titulo, id, etiqueta, etiquetadaPor } = {}, ...hijos) {
  return el("section", { clase: "tarjeta", "aria-label": etiqueta, "aria-labelledby": titulo ? id : etiquetadaPor },
    titulo ? el("h2", { id }, titulo) : null,
    ...hijos);
}

// Texto para cuando no hay nada que mostrar.
export function vacio(texto) {
  return el("p", { clase: "vacio" }, texto);
}

// Lista con un elemento por cada dato, o `textoVacio` si no hay ninguno.
export function lista(datos, elemento, textoVacio) {
  return datos.length ? el("ul", { clase: "lista" }, datos.map(elemento)) : vacio(textoVacio);
}

// Selector de laboratorio con su etiqueta. `alCambiar` recibe el id elegido.
export function selectorLaboratorio({ id, laboratorios, actual, alCambiar, compacto = false }) {
  return campo("Laboratorio",
    el("select", { id, clase: compacto ? "campo campo--compacto" : "campo", onchange: (e) => alCambiar(e.target.value) },
      laboratorios.map((l) => el("option", { value: l.id, selected: l.id === actual }, `${l.nombre} · ${l.campus}`))));
}

// Botones semana anterior / hoy / siguiente. `alCambiar` recibe una fecha ISO de la
// semana elegida. `otros` son controles que van antes de los botones (por ejemplo,
// el selector de laboratorio).
export function navegacionSemana({ lunes, hoy, alCambiar }, ...otros) {
  const ir = (fecha) => () => alCambiar(isoFecha(fecha));
  return el("div", { clase: "navegacion-semana" },
    ...otros,
    el("button", { clase: "boton", onclick: ir(sumarDias(lunes, -7)), "aria-label": "Semana anterior" }, "‹ Anterior"),
    el("button", { clase: "boton", onclick: ir(hoy) }, "Hoy"),
    el("button", { clase: "boton", onclick: ir(sumarDias(lunes, 7)), "aria-label": "Semana siguiente" }, "Siguiente ›"));
}

// Corre `accion` con el botón deshabilitado, para que no se envíe dos veces, y si
// falla muestra el error en lenguaje del usuario (H9). Lo usan formularios y botones.
export async function conBotonOcupado(boton, accion) {
  boton.disabled = true;
  try {
    await accion();
  } catch (error) {
    avisarError(error);
  } finally {
    boton.disabled = false;
  }
}

// Botón que ejecuta una acción asíncrona con `conBotonOcupado`.
export function botonAccion(texto, accion, atributos = {}) {
  const boton = el("button", { clase: "boton", ...atributos, onclick: () => conBotonOcupado(boton, accion) }, texto);
  return boton;
}
