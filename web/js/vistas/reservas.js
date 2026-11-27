// CU-15 Reservar máquina. La hora de inicio y la duración se eligen de listas que
// solo ofrecen lo permitido (dentro de una franja abierta, máximo 2 h), así esos
// errores no se pueden cometer desde la pantalla.
import { api } from "../api.js";
import { campo, encabezado, lista, tarjeta, vacio } from "../componentes.js";
import { avisar, avisarError, el, insigniaEstado } from "../dom.js";
import { aFecha, aHora, aMinutos, fechaCorta, hora, isoFecha, sumarMinutos } from "../formatos.js";

const estado = { laboratorio: null, fecha: null, maquina: null };
const DURACIONES = [30, 60, 90, 120];
const PASO = 15; // minutos entre una hora de inicio posible y la siguiente

// Franjas abiertas del día en minutos; las seguidas se unen, igual que `cubren()` del
// dominio. Un turno empieza y termina el mismo día, así que ninguna pasa de medianoche.
function franjasEnMinutos(franjas) {
  const unidas = [];
  const enMinutos = franjas.map((f) => ({ inicio: aMinutos(hora(f.inicio)), fin: aMinutos(hora(f.fin)) }));
  for (const f of enMinutos.sort((a, b) => a.inicio - b.inicio)) {
    const ultima = unidas.at(-1);
    if (ultima && f.inicio <= ultima.fin) ultima.fin = Math.max(ultima.fin, f.fin);
    else unidas.push(f);
  }
  return unidas;
}

// Horas de inicio de una franja que dejan caber al menos la reserva más corta y que
// no han pasado: `desde` es la hora actual (en minutos) si la fecha es hoy, o 0.
function horasDeInicio(franja, desde) {
  const inicios = [];
  const primera = Math.max(franja.inicio, Math.ceil(desde / PASO) * PASO);
  for (let m = primera; m + DURACIONES[0] <= franja.fin; m += PASO) inicios.push(m);
  return inicios;
}

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
    encabezado("Reservar una máquina", "Máximo 2 horas por reserva, una reserva activa a la vez y 6 horas por semana."),
    el("div", { clase: "columnas" },
      tarjeta({ etiqueta: "Máquinas" },
        el("div", { clase: "fila" }, campo("Laboratorio", selLab), campo("Fecha", inFecha)),
        el("h2", { style: "margin-top:1rem" }, `${fechaCorta(estado.fecha)} · ${ocupacion.laboratorio.nombre}`),
        franjas,
        maquinas),
      el("div", { clase: "formulario" },
        tarjeta({},
          // Hora del servidor (ADR-0009), no la del navegador.
          formularioReserva(ocupacion, estado.fecha === hoy ? aMinutos(hora(contexto.yo.ahora)) : 0, recargar)),
        tarjeta({ titulo: "Mis reservas", id: "mis-reservas" },
          lista(mias, (r) =>
            el("li", {}, el("strong", {}, `${fechaCorta(r.inicio)} ${hora(r.inicio)}–${hora(r.fin)}`), ` · ${r.maquina_id.replace("M-", "")} `, insigniaEstado(r.estado),
              r.estado === "ACTIVA" ? el("p", { clase: "ayuda" }, `Preséntese antes de las ${hora(r.limite_de_llegada)} o se libera sola.`) : null),
          "Todavía no tiene reservas.")))),
  );
}

function formularioReserva(ocupacion, desde, recargar) {
  const maquina = ocupacion.maquinas.find((m) => m.id === estado.maquina);
  if (!maquina) {
    return el("div", {}, el("h2", {}, "Nueva reserva"), vacio("Elija una máquina disponible de la lista."));
  }
  const franjas = franjasEnMinutos(ocupacion.franjas_abiertas)
    .map((f) => ({ ...f, inicios: horasDeInicio(f, desde) }))
    .filter((f) => f.inicios.length);
  if (!franjas.length) {
    return el("div", {}, el("h2", {}, `Nueva reserva · ${maquina.codigo}`),
      el("p", { clase: "nota nota--aviso" }, "No quedan horas abiertas para reservar ese día. Elija otra fecha."));
  }
  const inicio = el("select", { id: "inicio-r", clase: "campo", required: true },
    franjas.map((f) => el("optgroup", { label: `Abierto ${aHora(f.inicio)}–${aHora(f.fin)}` },
      f.inicios.map((m) => el("option", { value: aHora(m) }, aHora(m))))));
  const duracion = el("select", { id: "duracion-r", clase: "campo" },
    DURACIONES.map((m) => el("option", { value: m, selected: m === 60 }, m < 60 ? `${m} minutos` : `${m / 60} h`)));
  const resumen = el("p", { clase: "ayuda", "aria-live": "polite" });
  const boton = el("button", { type: "submit", clase: "boton boton--primario" }, "Reservar");

  const calcularFin = () => sumarMinutos(inicio.value, Number(duracion.value));
  const actualizar = () => {
    const desde = aMinutos(inicio.value);
    const cierre = franjas.find((f) => f.inicio <= desde && desde < f.fin).fin;
    // Las duraciones que terminarían con el laboratorio cerrado no se pueden elegir.
    for (const opcion of duracion.options) opcion.disabled = desde + Number(opcion.value) > cierre;
    if (duracion.selectedOptions[0].disabled) {
      duracion.value = [...duracion.options].filter((o) => !o.disabled).at(-1).value;
    }
    resumen.textContent = `De ${inicio.value} a ${calcularFin()} (abierto hasta las ${aHora(cierre)}). Si no llega en 15 minutos, la reserva se libera.`;
  };
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
    el("div", { clase: "fila" }, campo("Hora de inicio", inicio), campo("Duración", duracion)),
    resumen,
    el("div", { clase: "acciones" }, boton));
}
