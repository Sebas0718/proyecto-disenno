// Componentes de interfaz reutilizables, construidos con `el()`. Cada uno arma el
// mismo marcado (y las mismas clases CSS) que antes se repetía a mano en las vistas.
import { el } from "./dom.js";

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
