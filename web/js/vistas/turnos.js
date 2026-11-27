// CU-08 Responder turno pendiente: pensado para el celular (botones grandes, una columna).
import { api } from "../api.js";
import { botonAccion, encabezado, lista } from "../componentes.js";
import { avisar, confirmar, el, insigniaEstado } from "../dom.js";
import { fechaCorta, hora } from "../formatos.js";

export async function mostrar(contenedor, contexto) {
  const turnos = await api.misTurnos();
  const pendientes = turnos.filter((t) => t.estado === "PENDIENTE_ACEPTACION");
  const proximos = turnos.filter((t) => t.estado === "CONFIRMADO");
  const recargar = () => mostrar(contenedor, contexto);

  async function responder(turno, acepta) {
    if (!acepta) {
      const ok = await confirmar(
        "¿Rechazar el turno?",
        `Se avisará a quien lo asignó para que busque a otra persona (${fechaCorta(turno.inicio)}, ${hora(turno.inicio)}–${hora(turno.fin)}).`,
        "Rechazar turno",
      );
      if (!ok) return;
    }
    await api.responderTurno(turno.id, acepta);
    avisar(acepta ? "Turno aceptado" : "Turno rechazado", acepta ? "Ya aparece en sus próximos turnos." : "Se avisó al coordinador.");
    await recargar();
  }

  const fila = (t, acciones) =>
    el("li", { clase: "tarjeta lista__item" },
      el("div", {},
        el("strong", {}, `${fechaCorta(t.inicio)} · ${hora(t.inicio)}–${hora(t.fin)}`), el("br"),
        `${t.laboratorio_id} · ${t.horas} h `, insigniaEstado(t.estado)),
      acciones);

  contenedor.replaceChildren(
    encabezado("Mis turnos", "Próximas cuatro semanas"),
    el("section", { "aria-labelledby": "t-pendientes" },
      el("h2", { id: "t-pendientes" }, `Esperan su respuesta (${pendientes.length})`),
      lista(pendientes, (t) =>
        fila(t, el("div", { clase: "acciones" },
          botonAccion("Aceptar", () => responder(t, true), { clase: "boton boton--primario" }),
          botonAccion("Rechazar", () => responder(t, false), { clase: "boton boton--peligro" }))),
      "No tiene turnos pendientes."),
      el("p", { clase: "ayuda" }, "Un turno queda pendiente cuando se le asigna fuera de la disponibilidad que declaró al postularse.")),
    el("section", { "aria-labelledby": "t-proximos", style: "margin-top:1.5rem" },
      el("h2", { id: "t-proximos" }, "Próximos turnos confirmados"),
      lista(proximos, (t) => fila(t, null), "No tiene turnos próximos.")),
  );
}
