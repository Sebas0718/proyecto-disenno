// CU-07 Asignar turno: horario semanal del laboratorio + formulario de asignación.
// El formulario anticipa las reglas (tope, disponibilidad) para prevenir errores,
// pero la decisión final siempre es del servidor (el dominio).
import { api } from "../api.js";
import { campo, conBotonOcupado, encabezado, navegacionSemana, selectorLaboratorio, tarjeta } from "../componentes.js";
import { avisar, el, insigniaEstado } from "../dom.js";
import { DIAS, aFecha, fechaCorta, hora, horas, isoFecha, minutosEntre, sumarDias } from "../formatos.js";

const estado = { laboratorio: null, fecha: null };

export async function mostrar(contenedor, { yo, refrescarAvisos }) {
  const hoy = aFecha(yo.ahora);
  estado.fecha ??= isoFecha(hoy);
  const laboratorios = await api.laboratorios();
  const propios = yo.rol === "COORDINADOR_SOPORTE" ? laboratorios : laboratorios.filter((l) => l.id === yo.laboratorio_id);
  if (!propios.some((l) => l.id === estado.laboratorio)) estado.laboratorio = propios[0].id;

  const [horario, asistentes] = await Promise.all([
    api.horario(estado.laboratorio, estado.fecha),
    api.asistentes(estado.fecha),
  ]);
  const lunes = aFecha(horario.lunes);
  const laboratorio = propios.find((l) => l.id === estado.laboratorio);
  const recargar = () => mostrar(contenedor, { yo, refrescarAvisos });

  const selectorLab =
    propios.length > 1
      ? selectorLaboratorio({
          id: "lab", laboratorios: propios, actual: estado.laboratorio, compacto: true,
          alCambiar: (id) => { estado.laboratorio = id; recargar(); },
        })
      : null;

  contenedor.replaceChildren(
    encabezado(`Horario · ${laboratorio.nombre}`, `${laboratorio.campus} · semana ${horario.semana}`,
      navegacionSemana({ lunes, hoy, alCambiar: (fecha) => { estado.fecha = fecha; recargar(); } }, selectorLab)),
    el("div", { clase: "columnas" },
      tarjeta({ etiqueta: "Turnos de la semana" }, vistaSemana(lunes, horario.turnos, hoy)),
      tarjeta({ etiquetadaPor: "titulo-asignar" },
        formularioAsignar(lunes, hoy, asistentes, async (datos) => {
          const r = await api.asignarTurno({ ...datos, laboratorio_id: estado.laboratorio });
          if (r.requiere_aceptacion) {
            avisar("Turno enviado al asistente", "Quedó pendiente hasta que lo acepte, porque está fuera de su disponibilidad.");
          } else {
            avisar("Turno asignado", "El turno quedó confirmado en el horario.");
          }
          await refrescarAvisos();
          await recargar();
        }))),
  );
}

function vistaSemana(lunes, turnos, hoy) {
  return el("div", { clase: "semana" },
    DIAS.map((nombre, i) => {
      const fecha = sumarDias(lunes, i);
      const iso = isoFecha(fecha);
      const del_dia = turnos.filter((t) => t.inicio.startsWith(iso));
      return el("div", { clase: `dia ${iso === isoFecha(hoy) ? "dia--hoy" : ""}` },
        el("div", { clase: "dia__titulo" }, `${nombre} ${fecha.getDate()}`),
        del_dia.length
          ? del_dia.map((t) =>
              el("div", { clase: `turno ${t.estado === "PENDIENTE_ACEPTACION" ? "turno--pendiente" : ""} ${t.estado === "RECHAZADO" ? "turno--rechazado" : ""}` },
                el("strong", {}, `${hora(t.inicio)}–${hora(t.fin)}`),
                t.asistente_nombre, " ",
                t.estado !== "CONFIRMADO" ? insigniaEstado(t.estado) : null))
          : el("span", { clase: "ayuda" }, "Cerrado"));
    }));
}

function cubre(bloques, inicio, fin) {
  // Misma idea que `cubren()` del dominio: bloques seguidos se suman.
  let cursor = inicio;
  for (const b of [...bloques].sort((a, c) => a.hora_inicio.localeCompare(c.hora_inicio))) {
    if (b.hora_fin <= cursor) continue;
    if (b.hora_inicio > cursor) return false;
    cursor = b.hora_fin;
    if (cursor >= fin) return true;
  }
  return cursor >= fin;
}

function formularioAsignar(lunes, hoy, asistentes, alEnviar) {
  const selAsistente = el("select", { id: "asistente", clase: "campo", required: true },
    el("option", { value: "" }, "Elija un asistente…"),
    asistentes.map((a) =>
      el("option", { value: a.id, disabled: !a.activo },
        a.activo ? `${a.nombre} · cat. ${a.categoria} · ${horas(a.horas_asignadas)} de ${horas(a.tope_horas)}` : `${a.nombre} (no activo)`)));
  // Por defecto, el primer día de la semana que todavía no pasó.
  const primerDiaFuturo = DIAS.map((_, i) => isoFecha(sumarDias(lunes, i))).find((iso) => iso >= isoFecha(hoy));
  const selDia = el("select", { id: "dia", clase: "campo", required: true },
    DIAS.map((nombre, i) => {
      const iso = isoFecha(sumarDias(lunes, i));
      return el("option", { value: iso, selected: iso === primerDiaFuturo }, `${nombre} · ${fechaCorta(iso)}`);
    }));
  const inicio = el("input", { id: "inicio", type: "time", clase: "campo", step: "900", value: "08:00", required: true });
  const fin = el("input", { id: "fin", type: "time", clase: "campo", step: "900", value: "12:00", required: true });
  const pistas = el("div", { clase: "formulario", "aria-live": "polite" });
  const boton = el("button", { clase: "boton boton--primario", type: "submit" }, "Asignar turno");

  function actualizarPistas() {
    pistas.replaceChildren();
    const a = asistentes.find((x) => x.id === selAsistente.value);
    if (!a) return;
    const minutos = minutosEntre(inicio.value, fin.value);
    if (minutos <= 0) {
      pistas.append(el("p", { clase: "nota nota--peligro" }, "La hora de fin debe ser posterior a la de inicio."));
      return;
    }
    const total = a.horas_asignadas + minutos / 60;
    const porcentaje = Math.min(100, (total / a.tope_horas) * 100);
    pistas.append(
      el("div", {},
        el("p", { clase: "ayuda" }, `Con este turno: ${horas(total)} de ${horas(a.tope_horas)} esta semana (todos los laboratorios).`),
        el("div", { clase: `medidor ${total > a.tope_horas ? "medidor--lleno" : ""}`, role: "img", "aria-label": `${Math.round(porcentaje)} % del tope` },
          el("span", { style: `width:${porcentaje}%` }))),
    );
    if (total > a.tope_horas) {
      pistas.append(el("p", { clase: "nota nota--peligro" }, "Superaría su tope semanal: el sistema no lo va a permitir."));
    }
    const diaSemana = (aFecha(selDia.value).getDay() + 6) % 7;
    const bloques = a.disponibilidad.filter((b) => b.dia === diaSemana);
    const declarados = bloques.length ? bloques.map((b) => `${b.hora_inicio}–${b.hora_fin}`).join(", ") : "ninguna";
    pistas.append(el("p", { clase: "ayuda" }, `Disponibilidad declarada ese día: ${declarados}.`));
    if (!cubre(bloques, inicio.value, fin.value)) {
      pistas.append(el("p", { clase: "nota nota--aviso" },
        "Fuera de la disponibilidad que declaró: el turno quedará pendiente hasta que el asistente lo acepte."));
    }
  }

  for (const campo of [selAsistente, selDia, inicio, fin]) campo.addEventListener("input", actualizarPistas);

  return el("form", {
      clase: "formulario",
      onsubmit: (evento) => {
        evento.preventDefault();
        conBotonOcupado(boton, () =>
          alEnviar({ asistente_id: selAsistente.value, dia: selDia.value, hora_inicio: inicio.value, hora_fin: fin.value }));
      },
    },
    el("h2", { id: "titulo-asignar" }, "Asignar turno"),
    campo("Asistente", selAsistente),
    campo("Día", selDia),
    el("div", { clase: "fila" }, campo("Inicio", inicio), campo("Fin", fin)),
    pistas,
    el("div", { clase: "acciones" }, boton),
    el("p", { clase: "ayuda" }, "El sistema revisa traslapes en todos los laboratorios y campus, el tope semanal y que el laboratorio no tenga ya un responsable a esa hora."),
  );
}
