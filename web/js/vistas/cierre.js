// CU-19 Cerrar el mes. Es irreversible, así que se confirma con un diálogo que
// lo dice explícitamente (prevención de errores).
import { api } from "../api.js";
import { campo, encabezado, lista, tarjeta, vacio } from "../componentes.js";
import { avisar, avisarError, confirmar, el } from "../dom.js";
import { aFecha, colones, decimal, fechaHora, horas, nombreMes } from "../formatos.js";

let detalle = null;

export async function mostrar(contenedor, contexto) {
  const ahora = aFecha(contexto.yo.ahora);
  const anterior = new Date(ahora.getFullYear(), ahora.getMonth() - 1, 1);
  const cierres = await api.cierres();
  if (!detalle && cierres.length) detalle = await api.cierre(cierres[0].anio, cierres[0].mes);
  const recargar = () => mostrar(contenedor, contexto);

  const opciones = [el("option", { value: "" }, "Elija un mes…")];
  for (let i = 1; i <= 12; i++) {
    const fecha = new Date(ahora.getFullYear(), ahora.getMonth() - i, 1);
    const anio = fecha.getFullYear();
    const mes = fecha.getMonth() + 1;
    const cerrado = cierres.some((c) => c.anio === anio && c.mes === mes);
    opciones.push(el("option", { value: `${anio}-${mes}`, disabled: cerrado }, `${nombreMes(mes)} ${anio}${cerrado ? " (cerrado)" : ""}`));
  }
  const selMes = el("select", { id: "mes", clase: "campo" }, opciones);
  selMes.value = `${anterior.getFullYear()}-${anterior.getMonth() + 1}`;
  if (selMes.selectedOptions[0]?.disabled) selMes.value = "";

  async function cerrar(evento) {
    evento.preventDefault();
    if (!selMes.value) return;
    const [anio, mes] = selMes.value.split("-").map(Number);
    const ok = await confirmar(
      `¿Cerrar ${nombreMes(mes)} ${anio}?`,
      "Se calculará el pago de cada asistente y se generará el archivo para Becas. Un mes cerrado no se vuelve a calcular ni se corrige.",
      "Cerrar el mes",
    );
    if (!ok) return;
    try {
      detalle = await api.cerrarMes(anio, mes);
      avisar("Mes cerrado", `Total a pagar: ${colones(detalle.total)}. El archivo para Becas está listo.`);
      await contexto.refrescarAvisos();
      recargar();
    } catch (error) {
      avisarError(error);
    }
  }

  async function ver(c) {
    try {
      detalle = await api.cierre(c.anio, c.mes);
      recargar();
    } catch (error) {
      avisarError(error);
    }
  }

  contenedor.replaceChildren(
    encabezado("Cierre de mes", "Consolida las horas reales (marcas de entrada y salida) y calcula el pago para Becas."),
    el("div", { clase: "columnas" },
      tarjeta({ etiqueta: "Resultado del cierre" },
        detalle ? vistaDetalle(detalle) : vacio("Cierre un mes o elija uno de la lista para ver el detalle.")),
      el("div", { clase: "formulario" },
        el("form", { clase: "tarjeta formulario", onsubmit: cerrar },
          el("h2", {}, "Cerrar un mes"),
          campo("Mes", selMes),
          el("p", { clase: "nota nota--info" }, "Solo se puede cerrar un mes que ya terminó. Las tarifas se toman del tarifario vigente en cada fecha."),
          el("div", { clase: "acciones" }, el("button", { clase: "boton boton--primario", type: "submit", disabled: !selMes.value }, "Cerrar mes"))),
        tarjeta({ titulo: "Meses cerrados", id: "historial" },
          lista(cierres, (c) =>
            el("li", { clase: "lista__item" },
              el("span", {}, el("strong", {}, `${nombreMes(c.mes)} ${c.anio}`), el("br"), `${colones(c.total)} · ${c.asistentes} asistentes`),
              el("span", { clase: "acciones" },
                el("button", { clase: "boton", onclick: () => ver(c) }, "Ver"),
                botonDescarga(c))),
          "Todavía no se ha cerrado ningún mes.")))),
  );
}

function botonDescarga(c) {
  return el("button", {
    clase: "boton",
    onclick: async () => {
      try {
        const respuesta = await api.archivoBecas(c.anio, c.mes);
        const enlace = el("a", { href: URL.createObjectURL(await respuesta.blob()), download: `becas-${c.anio}-${String(c.mes).padStart(2, "0")}.csv` });
        // Firefox necesita el enlace dentro del documento, y si la URL se revoca justo
        // después del clic puede cortar la descarga: se revoca un momento después.
        document.body.append(enlace);
        enlace.click();
        enlace.remove();
        setTimeout(() => URL.revokeObjectURL(enlace.href), 1000);
      } catch (error) {
        avisarError(error);
      }
    },
    "aria-label": `Descargar CSV de ${nombreMes(c.mes)} ${c.anio}`,
  }, "CSV");
}

function vistaDetalle(c) {
  const conAlerta = c.liquidaciones.filter((li) => Number(li.horas_no_pagadas) > 0);
  return el("div", {},
    el("h2", {}, `${nombreMes(c.mes)} ${c.anio}`),
    el("p", { clase: "ayuda" }, `Cerrado el ${fechaHora(c.cerrado_en)}.`),
    conAlerta.length
      ? el("p", { clase: "nota nota--aviso" },
          `Hay horas trabajadas por encima del tope semanal que no se pagan: ${conAlerta.map((li) => `${li.nombre} (${horas(li.horas_no_pagadas)})`).join(", ")}.`)
      : null,
    el("div", { clase: "tabla-contenedor" },
      el("table", {},
        el("thead", {}, el("tr", {},
          el("th", {}, "Asistente"), el("th", {}, "Cat."), el("th", { clase: "numero" }, "Horas base"),
          el("th", { clase: "numero" }, "Con recargo"), el("th", { clase: "numero" }, "No pagadas"), el("th", { clase: "numero" }, "Monto"))),
        el("tbody", {},
          c.liquidaciones.length
            ? c.liquidaciones.map((li) =>
                el("tr", { clase: Number(li.horas_no_pagadas) > 0 ? "fila--alerta" : "" },
                  el("td", {}, li.nombre), el("td", {}, li.categoria),
                  el("td", { clase: "numero" }, decimal(li.horas_base)), el("td", { clase: "numero" }, decimal(li.horas_con_recargo)),
                  el("td", { clase: "numero" }, decimal(li.horas_no_pagadas)), el("td", { clase: "numero" }, colones(li.monto))))
            : el("tr", {}, el("td", { colspan: "6", clase: "vacio" }, "Nadie trabajó este mes."))),
        el("tfoot", {}, el("tr", {}, el("td", { colspan: "5" }, "Total"), el("td", { clase: "numero" }, colones(c.total)))))));
}
