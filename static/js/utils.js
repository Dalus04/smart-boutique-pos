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

// ── Parseador de fechas locales ───────────────────────────────────────────────
/**
 * Normaliza una cadena de fecha ISO a objeto Date local.
 * @param {string} isoString
 * @returns {Date}
 */
const parseLocalDate = (isoString) => {
    if (!isoString) return new Date();
    let s = isoString;
    if (!s.includes('Z') && !/[+-]\d{2}:\d{2}$/.test(s)) {
        s = s + 'Z';
    }
    return new Date(s);
};

// ── Helper para Carga de Categorías ───────────────────────────────────────────
/**
 * Obtiene la lista de categorías desde la API.
 * @param {string} endpoint - Endpoint de categorías (por defecto '/inventario/categorias')
 * @returns {Promise<Array>} Promesa que resuelve a la lista de categorías
 */
async function fetchCategorias(endpoint = '/inventario/categorias') {
    return await ApiClient.get(endpoint);
}

// ── Control General de Modales ────────────────────────────────────────────────
/**
 * Abre un modal con animación de entrada (fade-in + scale-100).
 * @param {HTMLElement|string} elementOrId - Elemento DOM o ID del modal.
 */
function openModal(elementOrId) {
    const modal = typeof elementOrId === 'string' ? document.getElementById(elementOrId) : elementOrId;
    if (!modal) return;
    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        const card = modal.querySelector('.transform') || modal.firstElementChild;
        if (card) card.classList.remove('scale-95');
    }, 10);
}

/**
 * Cierra un modal con animación de salida (fade-out + scale-95).
 * @param {HTMLElement|string} elementOrId - Elemento DOM o ID del modal.
 * @param {number} delay - Tiempo en ms antes de ocultarlo (por defecto 300ms).
 */
function closeModal(elementOrId, delay = 300) {
    const modal = typeof elementOrId === 'string' ? document.getElementById(elementOrId) : elementOrId;
    if (!modal) return;
    modal.classList.add('opacity-0');
    const card = modal.querySelector('.transform') || modal.firstElementChild;
    if (card) card.classList.add('scale-95');
    setTimeout(() => {
        modal.classList.add('hidden');
    }, delay);
}

// ── Sistema Unificado de Notificaciones Toast ────────────────────────────────
/**
 * Muestra una notificación Toast apilable y animada.
 * @param {string} message - Mensaje a mostrar
 * @param {string|boolean} type - 'success', 'error', 'info', 'warning' (o boolean: true=error, false=success)
 */
function showToast(message, type = 'success') {
    let toastType = type;
    if (typeof type === 'boolean') {
        toastType = type ? 'error' : 'success';
    }
    
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none';
        document.body.appendChild(container);
    }
    
    const toast = document.createElement('div');
    
    let bgClass = 'bg-emerald-600 text-white';
    let iconClass = 'fa-circle-check';
    
    if (toastType === 'error') {
        bgClass = 'bg-red-600 text-white';
        iconClass = 'fa-circle-xmark';
    } else if (toastType === 'info') {
        bgClass = 'bg-blue-600 text-white';
        iconClass = 'fa-circle-info';
    } else if (toastType === 'warning') {
        bgClass = 'bg-amber-500 text-white';
        iconClass = 'fa-triangle-exclamation';
    }
    
    toast.className = `px-4 py-3 rounded-xl shadow-lg font-bold text-sm transform transition-all duration-300 translate-y-4 opacity-0 flex items-center gap-2.5 pointer-events-auto ${bgClass}`;
    toast.innerHTML = `<i class="fa-solid ${iconClass}"></i> <span>${message}</span>`;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.remove('translate-y-4', 'opacity-0');
    }, 10);
    
    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-x-4');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ── Generador de Spinners de Carga Unificados ─────────────────────────────────
/**
 * Genera el HTML para un icono de carga (spinner) unificado con la paleta del sistema (text-primary).
 * @param {string} text - Texto opcional a mostrar junto al spinner.
 * @param {string} sizeClass - Clase opcional de tamaño (ej. "text-2xl").
 * @returns {string} String HTML con el spinner.
 */
function getSpinnerHtml(text = '', sizeClass = '') {
    const icon = `<i class="fa-solid fa-circle-notch fa-spin text-primary ${sizeClass}"></i>`;
    return text ? `${icon} <span>${text}</span>` : icon;
}

/**
 * Inyecta un contenedor de carga centrado en el elemento o ID indicado.
 * @param {HTMLElement|string} elementOrId - Elemento DOM o su ID.
 * @param {string} text - Texto opcional de carga.
 * @param {string} pyClass - Clase de padding (por defecto "p-8").
 */
function setLoadingHtml(elementOrId, text = '', pyClass = 'p-8') {
    const el = typeof elementOrId === 'string' ? document.getElementById(elementOrId) : elementOrId;
    if (!el) return;
    el.innerHTML = `<div class="flex justify-center items-center gap-2 ${pyClass}">${getSpinnerHtml(text, 'text-2xl')}</div>`;
}


