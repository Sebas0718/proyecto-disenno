// Formatos y cálculos de fechas, horas y montos. No tocan el DOM, así que se
// pueden probar con Node. Fechas siempre en hora local, como el servidor (ADR-0009).

export const DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
  "septiembre", "octubre", "noviembre", "diciembre"];

export function nombreMes(numero) {
  return MESES[numero - 1];
}

export function aFecha(texto) {
  const [a, m, d] = texto.slice(0, 10).split("-").map(Number);
  return new Date(a, m - 1, d);
}

export function isoFecha(fecha) {
  const m = String(fecha.getMonth() + 1).padStart(2, "0");
  const d = String(fecha.getDate()).padStart(2, "0");
  return `${fecha.getFullYear()}-${m}-${d}`;
}

export function sumarDias(fecha, dias) {
  const copia = new Date(fecha);
  copia.setDate(copia.getDate() + dias);
  return copia;
}

export function hora(textoIso) {
  return textoIso.slice(11, 16);
}

// --- Horas del día: "HH:MM" <-> minutos desde la medianoche -----------------------
export function aMinutos(hhmm) {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

export function aHora(minutos) {
  return `${String(Math.floor(minutos / 60)).padStart(2, "0")}:${String(minutos % 60).padStart(2, "0")}`;
}

export function minutosEntre(inicio, fin) {
  return aMinutos(fin) - aMinutos(inicio);
}

export function sumarMinutos(hhmm, minutos) {
  return aHora(aMinutos(hhmm) + minutos);
}

export function fechaCorta(textoIso) {
  const fecha = aFecha(textoIso);
  return `${DIAS[(fecha.getDay() + 6) % 7].slice(0, 3)} ${fecha.getDate()} ${MESES[fecha.getMonth()].slice(0, 3)}`;
}

// "1 de noviembre de 2026 a las 00:05": en 24 h, como el resto de la interfaz.
// El texto ISO viene sin zona horaria y se lee como hora local (ADR-0009).
const FECHA_Y_HORA = new Intl.DateTimeFormat("es-CR", { dateStyle: "long", timeStyle: "short", hourCycle: "h23" });

export function fechaHora(textoIso) {
  return FECHA_Y_HORA.format(new Date(textoIso.slice(0, 19)));
}

export function colones(texto) {
  return `₡${Number(texto).toLocaleString("es-CR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function decimal(texto) {
  return Number(texto).toLocaleString("es-CR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function horas(numero) {
  return `${Number(numero).toLocaleString("es-CR", { maximumFractionDigits: 2 })} h`;
}
