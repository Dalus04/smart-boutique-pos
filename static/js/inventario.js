/**
 * Smart POS - Inventario Inteligente v5.5
 * Lógica Web para el Catálogo e Inventario
 */

// Elementos del DOM
const elSearchInput = document.getElementById('search-input');
const elFilterCategoria = document.getElementById('filter-categoria');
const elFilterEstado = document.getElementById('filter-estado');
const elTableBody = document.getElementById('table-body');
const elTableLoading = document.getElementById('table-loading');
const elTableEmpty = document.getElementById('table-empty');

// KPIs DOM v5.5
const kpiHealthScore = document.getElementById('kpi-health-score');
const kpiHealthStatus = document.getElementById('kpi-health-status');
const accionesContainer = document.getElementById('acciones-container');
const insightTrack = document.getElementById('insights-track');

// Función Debounce para proteger a la API de sobrecarga
function debounce(func, delay = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => { func.apply(this, args); }, delay);
    };
}

// Formateador de moneda
const fmtCurrency = (val) => `$${val.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits:2})}`;

// Cargar Categorías para el dropdown
async function loadCategorias() {
    try {
        const categorias = await ApiClient.get('/inventario/categorias');
        categorias.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat.id;
            option.textContent = cat.nombre;
            elFilterCategoria.appendChild(option);
        });
    } catch (e) {
        console.error("Error cargando categorías", e);
    }
}

// Generador de Badges Semánticos con Tooltips Nativos (Tailwind group-hover)
function generateBadgeHtml(text, type, tooltipText) {
    let classes = "px-2 py-1 rounded text-xs font-medium w-full text-center ";
    let extraHtml = "";
    
    if (type === 'critico') {
        classes += "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300";
        extraHtml = `<span class="relative flex h-2 w-2 mr-1 inline-block">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
        </span>`;
    } else if (type === 'bajo') {
        classes += "bg-orange-50 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300";
    } else if (type === 'optimo') {
        classes += "bg-gray-50 text-gray-600 dark:bg-gray-700/50 dark:text-gray-300";
    }

    // Estructura de Tooltip Nativo
    return `
        <div class="relative group cursor-help inline-block w-full">
            <div class="inline-flex items-center justify-center ${classes}">
                ${extraHtml}${text}
            </div>
            <!-- Tooltip -->
            <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-56 p-2 bg-gray-800 dark:bg-gray-700 text-white text-xs rounded shadow-xl z-50 text-center whitespace-normal leading-tight font-normal">
                ${tooltipText}
                <div class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800 dark:border-t-gray-700"></div>
            </div>
        </div>
    `;
}

// Generador de Badge ABC (Pareto) -> Impacto en Ventas
function generateAbcBadge(abcClass, ingresos) {
    let colorClass = "";
    let tooltipText = "";
    let label = "";
    if (abcClass === 'A') {
        label = "Estrella";
        colorClass = "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300";
        tooltipText = "Genera el 80% de tus ingresos. Es vital mantenerlo abastecido.";
    } else if (abcClass === 'B') {
        label = "Frecuente";
        colorClass = "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300";
        tooltipText = "Rotación estable. Contribuye de forma media a la facturación.";
    } else {
        label = "Lento";
        colorClass = "bg-gray-50 text-gray-600 dark:bg-gray-700/50 dark:text-gray-300";
        tooltipText = "Baja relevancia. Su impacto en los ingresos totales es menor.";
    }

    return `
        <div class="relative group cursor-help inline-block">
            <div class="flex flex-col items-center">
                <span class="px-2 py-0.5 rounded text-xs font-black ${colorClass}">${label}</span>
                <span class="text-[10px] text-green-600 dark:text-green-400 font-bold mt-1">${fmtCurrency(ingresos)}</span>
            </div>
            <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-56 p-2 bg-gray-800 dark:bg-gray-700 text-white text-xs rounded shadow-xl z-50 text-center whitespace-normal font-normal">
                ${tooltipText}
                <div class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800 dark:border-t-gray-700"></div>
            </div>
        </div>
    `;
}

// Renderizador principal de tabla
async function fetchAndRenderData() {
    elTableLoading.classList.remove('hidden');
    elTableEmpty.classList.add('hidden');
    
    const params = {};
    const q = elSearchInput.value.trim();
    if (q) params.q = q;
    
    const cat = elFilterCategoria.value;
    if (cat) params.id_categoria = cat;
    
    const est = elFilterEstado.value;
    if (est) params.estado_stock = est;
    
    try {
        const data = await ApiClient.get('/inventario/data', params);
        
        // 1. Renderizar Filas y recopilar acciones
        elTableBody.innerHTML = '';
        const accionesRecomendadas = [];
        
        if (data.productos.length === 0) {
            elTableEmpty.classList.remove('hidden');
            elTableEmpty.style.display = 'flex';
        } else {
            elTableEmpty.style.display = 'none';
            data.productos.forEach(prod => {
                const tr = document.createElement('tr');
                tr.className = "hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors";
                
                if (prod.riesgo === 'Riesgo Alto' || prod.estado_fisico === 'Crítico') {
                    tr.classList.add('bg-red-50/20', 'dark:bg-red-900/10');
                }
                
                // Mapear Tipos de Badge y Tooltips para UX Filosófico
                let badgeEstado = 'optimo';
                let labelEstado = "Flujo Constante";
                let ttEstado = "El inventario fluye saludablemente sin riesgo inminente de agotarse.";
                if (prod.estado_fisico === 'Crítico') {
                    badgeEstado = 'critico';
                    labelEstado = "Atención Inmediata";
                    ttEstado = "Te quedarás sin producto antes de que termine la semana si no repones hoy.";
                } else if (prod.estado_fisico === 'Bajo') {
                    badgeEstado = 'bajo';
                    labelEstado = "Vigilar";
                    ttEstado = "El nivel de inventario está disminuyendo. Prepara una orden de compra.";
                }
                
                let badgeRiesgo = 'optimo';
                let labelRiesgo = "Demanda Cubierta";
                let ttRiesgo = "El stock disponible cubrirá de sobra las compras estimadas para esta semana.";
                if (prod.riesgo === 'Riesgo Alto') {
                    badgeRiesgo = 'critico';
                    labelRiesgo = "Quiebre Futuro";
                    ttRiesgo = "Aunque aún hay stock físico, no alcanzará para cubrir la demanda esperada de los próximos 7 días.";
                } else if (prod.riesgo === 'Riesgo Medio') {
                    badgeRiesgo = 'bajo';
                    labelRiesgo = "Stock Ajustado";
                    ttRiesgo = "El stock cubre la demanda estimada, pero podrías agotarlo si hay un pico de ventas inesperado.";
                }

                // Generar acción en panel izquierdo si es relevante
                if (prod.accion === 'Reponer' && accionesRecomendadas.length < 5) {
                    accionesRecomendadas.push({
                        icon: 'fa-box-open', color: 'text-red-500', bg: 'bg-red-50 dark:bg-red-900/20',
                        text: `Reponer urgente <b>${prod.nombre}</b>. Se agotará en ${prod.dias_quiebre} días.`
                    });
                } else if (prod.accion === 'Liquidar' && accionesRecomendadas.length < 5) {
                    accionesRecomendadas.push({
                        icon: 'fa-tags', color: 'text-orange-500', bg: 'bg-orange-50 dark:bg-orange-900/20',
                        text: `Ofrecer descuento en <b>${prod.nombre}</b>. No se está vendiendo.`
                    });
                }
                
                const diasRestantesHTML = prod.dias_quiebre ? 
                    `<div class="relative group cursor-help inline-block">
                        <div class="text-base font-bold ${prod.dias_quiebre < 7 ? 'text-red-500' : (prod.dias_quiebre < 15 ? 'text-orange-500' : 'text-gray-700 dark:text-gray-300')}">${prod.dias_quiebre} d</div>
                        <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-56 p-2 bg-gray-800 dark:bg-gray-700 text-white text-xs rounded shadow-xl z-50 text-center whitespace-normal font-normal">
                            Te quedan ${prod.dias_quiebre} días de inventario a tu ritmo de ventas actual.
                            <div class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800 dark:border-t-gray-700"></div>
                        </div>
                    </div>` 
                    : `<div class="text-sm text-gray-400" title="No hay suficiente historial de ventas para predecir">-</div>`;

                let accionBtn = "";
                if (prod.accion === "Reponer") {
                    accionBtn = `<div class="relative group cursor-help w-full"><button class="w-full text-xs font-bold text-red-600 bg-red-100 dark:bg-red-900/40 dark:text-red-300 py-1.5 px-2 rounded transition-transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-1.5 shadow-sm">🔴 Reponer</button><div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-56 p-2 bg-gray-800 dark:bg-gray-700 text-white text-xs rounded shadow-xl z-50 text-center whitespace-normal font-normal">No tienes stock suficiente para terminar la semana.<div class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800 dark:border-t-gray-700"></div></div></div>`;
                } else if (prod.accion === "Liquidar") {
                    accionBtn = `<div class="relative group cursor-help w-full"><button class="w-full text-xs font-bold text-orange-600 bg-orange-100 dark:bg-orange-900/40 dark:text-orange-300 py-1.5 px-2 rounded transition-transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-1.5 shadow-sm">🟠 Liquidar</button><div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-56 p-2 bg-gray-800 dark:bg-gray-700 text-white text-xs rounded shadow-xl z-50 text-center whitespace-normal font-normal">Este producto no se vende. Aprovecha su margen para hacer una oferta.<div class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800 dark:border-t-gray-700"></div></div></div>`;
                } else {
                    accionBtn = `<div class="relative group cursor-help w-full"><button class="w-full text-xs font-bold text-gray-600 bg-gray-100 dark:bg-gray-700 dark:text-gray-300 py-1.5 px-2 rounded transition-colors flex items-center justify-center gap-1.5 cursor-default">🟢 Mantener</button><div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-56 p-2 bg-gray-800 dark:bg-gray-700 text-white text-xs rounded shadow-xl z-50 text-center whitespace-normal font-normal">Tienes la cantidad ideal. No es necesario comprar más.<div class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800 dark:border-t-gray-700"></div></div></div>`;
                }

                tr.innerHTML = `
                    <td class="py-4 px-4">
                        <div class="flex flex-col">
                            <span class="text-sm font-bold text-gray-900 dark:text-gray-100">${prod.nombre}</span>
                            <span class="text-xs text-gray-600 dark:text-gray-300 font-medium flex items-center gap-1.5 mt-0.5">
                                <span>${prod.categoria}</span>
                                <span>•</span>
                                <span class="font-semibold text-purple-600 dark:text-purple-400">${prod.contexto_producto}</span>
                            </span>
                            <span class="text-xs text-gray-500 dark:text-gray-300 mt-0.5 font-medium" title="Este artículo ayuda a vender otros artículos de la tienda">
                                <i class="fa-solid fa-diagram-project text-purple-400 mr-1"></i>${prod.reglas_vinculadas_texto}
                            </span>
                        </div>
                    </td>
                    <td class="py-4 px-4 whitespace-nowrap text-center">
                        ${generateAbcBadge(prod.abc, prod.ingresos_generados)}
                    </td>
                    <td class="py-4 px-4 whitespace-nowrap text-center">
                        <div class="relative group cursor-help inline-block">
                            <div class="text-sm font-bold text-gray-800 dark:text-gray-200">${prod.margen}%</div>
                            <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-56 p-2 bg-gray-800 dark:bg-gray-700 text-white text-xs rounded shadow-xl z-50 text-center whitespace-normal font-normal">
                                Retorno: Por cada unidad vendida, ganas un ${prod.margen}% tras descontar el costo.
                                <div class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800 dark:border-t-gray-700"></div>
                            </div>
                        </div>
                    </td>
                    <td class="py-4 px-4 whitespace-nowrap text-center">
                        <div class="text-lg font-bold ${prod.stock <= 5 ? 'text-red-500' : 'text-gray-700 dark:text-gray-300'}">${prod.stock}</div>
                    </td>
                    <td class="py-4 px-4 whitespace-nowrap text-center">
                        ${diasRestantesHTML}
                    </td>
                    <td class="py-4 px-4 whitespace-nowrap text-center space-y-1.5 flex flex-col items-center max-w-[140px] mx-auto">
                        ${generateBadgeHtml(labelEstado, badgeEstado, ttEstado)}
                        ${generateBadgeHtml(labelRiesgo, badgeRiesgo, ttRiesgo)}
                    </td>
                    <td class="py-4 px-4 whitespace-nowrap text-center">
                        ${accionBtn}
                    </td>
                `;
                
                elTableBody.appendChild(tr);
            });
        }

        // 2. Actualizar Salud de Stock
        const total = data.kpis.productos_activos;
        const criticos = data.kpis.riesgo_alto_critico;
        const healthScore = total > 0 ? Math.max(0, Math.round(((total - criticos) / total) * 100)) : 0;
        kpiHealthScore.textContent = healthScore;
        const kpiHealthSubtitle = document.getElementById('kpi-health-subtitle');
        
        if (healthScore >= 90) {
            kpiHealthStatus.textContent = "Excelente";
            kpiHealthStatus.className = "text-xs font-bold px-2 py-0.5 rounded text-green-700 bg-green-50 dark:bg-green-900/30 dark:text-green-300";
            if (kpiHealthSubtitle) kpiHealthSubtitle.textContent = `Significa que el ${healthScore}% de tu catálogo fluye sin riesgo de quiebre.`;
        } else if (healthScore >= 70) {
            kpiHealthStatus.textContent = "Estable";
            kpiHealthStatus.className = "text-xs font-bold px-2 py-0.5 rounded text-blue-700 bg-blue-50 dark:bg-blue-900/30 dark:text-blue-300";
            if (kpiHealthSubtitle) kpiHealthSubtitle.textContent = `El inventario está controlado, pero hay un ${100 - healthScore}% de artículos que requieren vigilancia.`;
        } else if (healthScore >= 50) {
            kpiHealthStatus.textContent = "Requiere Atención";
            kpiHealthStatus.className = "text-xs font-bold px-2 py-0.5 rounded text-orange-700 bg-orange-50 dark:bg-orange-900/30 dark:text-orange-300";
            if (kpiHealthSubtitle) kpiHealthSubtitle.textContent = `Advertencia: El ${100 - healthScore}% de tu catálogo podría agotarse si no realizas reposiciones.`;
        } else {
            kpiHealthStatus.textContent = "Crítico";
            kpiHealthStatus.className = "text-xs font-bold px-2 py-0.5 rounded text-red-700 bg-red-50 dark:bg-red-900/30 dark:text-red-300";
            if (kpiHealthSubtitle) kpiHealthSubtitle.textContent = `¡Peligro! El ${100 - healthScore}% de tus productos están agotándose y perdiendo ventas potenciales.`;
        }

        // 3. Renderizar Panel Izquierdo de Acciones Prioritarias
        if (accionesRecomendadas.length > 0) {
            accionesContainer.innerHTML = accionesRecomendadas.map(a => `
                <div class="${a.bg} p-3 rounded-lg border border-gray-100 dark:border-gray-700/50 flex gap-3 items-start">
                    <i class="fa-solid ${a.icon} ${a.color} mt-0.5"></i>
                    <p class="text-xs text-gray-700 dark:text-gray-300 leading-snug">${a.text}</p>
                </div>
            `).join('');
        } else {
            accionesContainer.innerHTML = `
                <div class="text-center text-gray-500 text-sm mt-10">
                    <i class="fa-solid fa-check-circle text-4xl mb-2 text-green-400 opacity-50"></i>
                    <p>Todo está bajo control.</p>
                </div>
            `;
        }

        // 4. Renderizar Insights Carrusel
        insightTrack.innerHTML = '';
        const insights = [];
        if (data.kpis.stock_total > 0) insights.push({ icon: 'fa-boxes-stacked', color: 'text-blue-500', bg: 'bg-blue-100', text: `Stock total valorizado disponible para la venta.` });
        if (criticos > 0) insights.push({ icon: 'fa-triangle-exclamation', color: 'text-red-500', bg: 'bg-red-100', text: `${criticos} productos requieren reposición inminente.` });
        insights.push({ icon: 'fa-hand-holding-dollar', color: 'text-green-500', bg: 'bg-green-100', text: `Clasificación Pareto (ABC) aplicada al ${total} productos.` });

        insights.forEach((ins, idx) => {
            const el = document.createElement('div');
            el.className = `w-full shrink-0 flex items-center gap-4 insight-slide absolute inset-0 transition-opacity duration-500 ${idx === 0 ? 'opacity-100 z-10' : 'opacity-0 z-0 pointer-events-none'}`;
            el.innerHTML = `
                <div class="h-10 w-10 rounded-full ${ins.bg} dark:bg-gray-700 ${ins.color} flex items-center justify-center text-lg shrink-0">
                    <i class="fa-solid ${ins.icon}"></i>
                </div>
                <p class="text-gray-700 dark:text-gray-200 font-medium text-sm md:text-base leading-tight">${ins.text}</p>
            `;
            insightTrack.appendChild(el);
        });

    } catch (e) {
        console.error("Error obteniendo datos del inventario", e);
        elTableBody.innerHTML = `<tr><td colspan="7" class="text-center text-red-500 p-4">Error cargando los datos. Ver consola.</td></tr>`;
    } finally {
        elTableLoading.classList.add('hidden');
    }
}

// Variables globales para el carrusel
let currentInsightIndex = 0;

function showInsight(index) {
    const slides = document.querySelectorAll('.insight-slide');
    if (slides.length === 0) return;
    
    if (index >= slides.length) currentInsightIndex = 0;
    else if (index < 0) currentInsightIndex = slides.length - 1;
    else currentInsightIndex = index;

    slides.forEach((slide, i) => {
        if (i === currentInsightIndex) {
            slide.classList.replace('opacity-0', 'opacity-100');
            slide.classList.replace('z-0', 'z-10');
            slide.classList.remove('pointer-events-none');
        } else {
            slide.classList.replace('opacity-100', 'opacity-0');
            slide.classList.replace('z-10', 'z-0');
            slide.classList.add('pointer-events-none');
        }
    });
}

function nextInsight() {
    showInsight(currentInsightIndex + 1);
}

function prevInsight() {
    showInsight(currentInsightIndex - 1);
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    loadCategorias().then(() => fetchAndRenderData());
    
    const debouncedSearch = debounce(() => {
        fetchAndRenderData();
    }, 300);
    
    elSearchInput.addEventListener('input', debouncedSearch);
    elFilterCategoria.addEventListener('change', fetchAndRenderData);
    elFilterEstado.addEventListener('change', fetchAndRenderData);

    // Rotación automática del carrusel cada 5 segundos
    setInterval(nextInsight, 5000);
});
