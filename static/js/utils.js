/**
 * Smart Boutique POS — Utilidades compartidas del frontend
 *
 * Este archivo debe cargarse ANTES que cualquier script de página.
 * Expone funciones globales reutilizables para evitar duplicación.
 */

// ── Debounce ──────────────────────────────────────────────────────────────────
/**
 * Retrasa la ejecución de `func` hasta que hayan pasado `delay` ms
 * sin nuevas llamadas. Protege a la API de sobrecarga en inputs de búsqueda.
 * @param {Function} func
 * @param {number} delay - milisegundos de espera (por defecto 300)
 * @returns {Function}
 */
function debounce(func, delay = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => { func.apply(this, args); }, delay);
    };
}

// ── Formateador de moneda ─────────────────────────────────────────────────────
/**
 * Formatea un número como moneda peruana (S/).
 * @param {number} val   - Valor a formatear (null/undefined → 0)
 * @param {number} decimals - Dígitos decimales (por defecto 2)
 * @returns {string}  e.g. "S/ 1,234.56"
 */
const fmtCurrency = (val, decimals = 2) =>
    `S/ ${Number(val || 0).toLocaleString('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
    })}`;

/** Alias corto — mantiene compatibilidad con los módulos que usan fmt() */
const fmt = fmtCurrency;
