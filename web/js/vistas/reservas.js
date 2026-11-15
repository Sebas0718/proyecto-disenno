// CU-15 Reservar máquina. La duración se elige de una lista (máximo 2 h), así el
// error "más de dos horas" no se puede cometer desde la pantalla.
import { api } from "../api.js";
import { aFecha, avisar, avisarError, el, fechaCorta, hora, insigniaEstado, isoFecha } from "../ui.js";

const estado = { laboratorio: null, fecha: null, maquina: null };
const DURACIONES = [30, 60, 90, 120];

export async function mostrar(contenedor, contexto) {
  const hoy = isoFecha(aFecha(contexto.yo.ahora));
  estado.fecha ??= hoy;
  const laboratorios = await api.laboratorios();
  estado.laboratorio ??= laboratorios[0].id;
  const [ocupacion, mias] = await Promise.all([api.ocupacion(estado.laboratorio, estado.fecha), api.misReservas()]);
  const recargar = () => mostrar(contenedor, contexto);
  const abierto = ocupacion.franjas_abiertas;
  if (!abierto.length || !ocupacion.maquinas.some((m) => m.id === estado.maquina && m.en_servicio)) estado.maquina = null;

  const selLab = el("select", { id: "lab-r", clase: "campo", onchange: (e) => { estado.laboratorio = e.target.value; estado.maquina = null; recargar(); } },
    laboratorios.map((l) => el("option", { value: l.id, selected: l.id === estado.laboratorio }, `${l.nombre} · ${l.campus}`)));
  const inFecha = el("input", { id: "fecha-r", type: "date", clase: "campo", min: hoy, value: estado.fecha,
    onchange: (e) => { estado.fecha = e.target.value; recargar(); } });

  const franjas = el("div", { clase: "franjas", "aria-label": "Horario abierto" },
    abierto.length
      ? abierto.map((f) => el("span", { clase: "insignia insignia--exito" }, `Abierto ${hora(f.inicio)}–${hora(f.fin)}`))
      : el("span", { clase: "insignia insignia--peligro" }, "Cerrado todo el día: no hay turnos de asistente. Elija otra fecha."));

  const maquinas = el("div", { clase: "maquinas" },
    ocupacion.maquinas.map((m) =>
      el("button", {
          type: "button", clase: "maquina", disabled: !m.en_servicio || !abierto.length,
          "aria-pressed": String(m.id === estado.maquina),
          onclick: () => { estado.maquina = m.id; recargar(); },
        },
        el("span", { clase: "maquina__codigo" }, m.codigo),
        el("span", { clase: "maquina__detalle" },
          !m.en_servicio ? "Fuera de servicio"
            : !abierto.length ? "Laboratorio cerrado"
            : m.reservas.length ? `Ocupada: ${m.reservas.map((r) => `${hora(r.inicio)}–${hora(r.fin)}${r.propia ? " (suya)" : ""}`).join(", ")}`
            : "Libre todo el horario abierto"))));

  contenedor.replaceChildren(
    el("div", { clase: "encabezado" },
      el("div", {}, el("h1", {}, "Reservar una máquina"),
        el("p", {}, "Máximo 2 horas por reserva, una reserva activa a la vez y 6 horas por semana."))),
    el("div", { clase: "columnas" },
      el("section", { clase: "tarjeta", "aria-label": "Máquinas" },
        el("div", { clase: "fila" },
          el("div", { clase: "grupo" }, el("label", { for: "lab-r" }, "Laboratorio"), selLab),
          el("div", { clase: "grupo" }, el("label", { for: "fecha-r" }, "Fecha"), inFecha)),
        el("h2", { style: "margin-top:1rem" }, `${fechaCorta(estado.fecha)} · ${ocupacion.laboratorio.nombre}`),
        franjas,
        maquinas),
      el("div", { clase: "formulario" },
        el("section", { clase: "tarjeta" }, formularioReserva(ocupacion, recargar)),
        el("section", { clase: "tarjeta", "aria-labelledby": "mis-reservas" },
          el("h2", { id: "mis-reservas" }, "Mis reservas"),
          mias.length
            ? el("ul", { clase: "lista" }, mias.map((r) =>
                el("li", {}, el("strong", {}, `${fechaCorta(r.inicio)} ${hora(r.inicio)}–${hora(r.fin)}`), ` · ${r.maquina_id.replace("M-", "")} `, insigniaEstado(r.estado),
                  r.estado === "ACTIVA" ? el("p", { clase: "ayuda" }, `Preséntese antes de las ${hora(r.limite_de_llegada)} o se libera sola.`) : null)))
            : el("p", { clase: "vacio" }, "Todavía no tiene reservas.")))),
  );
}

function formularioReserva(ocupacion, recargar) {
  const maquina = ocupacion.maquinas.find((m) => m.id === estado.maquina);
  if (!maquina) {
    return el("div", {}, el("h2", {}, "Nueva reserva"), el("p", { clase: "vacio" }, "Elija una máquina disponible de la lista."));
  }
  const primera = ocupacion.franjas_abiertas[0];
  const inicio = el("input", { id: "inicio-r", type: "time", step: "900", clase: "campo", required: true,
    value: primera ? hora(primera.inicio) : "08:00" });
  const duracion = el("select", { id: "duracion-r", clase: "campo" },
    DURACIONES.map((m) => el("option", { value: m, selected: m === 60 }, m < 60 ? `${m} minutos` : `${m / 60} h`)));
  const resumen = el("p", { clase: "ayuda", "aria-live": "polite" });
  const boton = el("button", { type: "submit", clase: "boton boton--primario" }, "Reservar");

  const calcularFin = () => {
    const [h, m] = inicio.value.split(":").map(Number);
    const total = h * 60 + m + Number(duracion.value);
    return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
  };
  const actualizar = () => { resumen.textContent = `De ${inicio.value} a ${calcularFin()}. Si no llega en 15 minutos, la reserva se libera.`; };
  inicio.addEventListener("input", actualizar);
  duracion.addEventListener("input", actualizar);
  actualizar();

  return el("form", {
      clase: "formulario",
      onsubmit: async (evento) => {
        evento.preventDefault();
        boton.disabled = true;
        try {
          const r = await api.reservar({ maquina_id: maquina.id, inicio: `${estado.fecha}T${inicio.value}`, fin: `${estado.fecha}T${calcularFin()}` });
          avisar("Reserva confirmada", `${maquina.codigo}, ${inicio.value}–${calcularFin()}. Preséntese antes de las ${hora(r.limite_de_llegada)}.`);
          recargar();
        } catch (error) {
          avisarError(error);
          boton.disabled = false;
        }
      },
    },
    el("h2", {}, `Nueva reserva · ${maquina.codigo}`),
    el("div", { clase: "fila" },
      el("div", { clase: "grupo" }, el("label", { for: "inicio-r" }, "Hora de inicio"), inicio),
      el("div", { clase: "grupo" }, el("label", { for: "duracion-r" }, "Duración"), duracion)),
    resumen,
    el("div", { clase: "acciones" }, boton));
}
