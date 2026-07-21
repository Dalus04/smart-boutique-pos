/**
 * Smart POS - Inventario Inteligente v5.5 (Refactorización UI/UX Fase 1)
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

window.dashboardInsights = [];
window.inventoryDataMap = {};

// Dropdown Contextual global state
let activeDropdownId = null;
let globalKPIsData = null;

// Estado Global de Paginación
let currentPage = 1;
let pageSize = 20;
let totalPages = 1;
let totalRecords = 0;

function toggleContextMenu(prodId, event) {
    if (event) event.stopPropagation();
    const targetMenu = document.getElementById(`context-menu-${prodId}`);
    const isHidden = targetMenu ? targetMenu.classList.contains('hidden') : true;

    closeAllDropdowns();

    if (isHidden && targetMenu) {
        targetMenu.classList.remove('hidden');
        activeDropdownId = prodId;
    }
}

function closeAllDropdowns() {
    document.querySelectorAll('.context-menu-dropdown').forEach(el => el.classList.add('hidden'));
    activeDropdownId = null;
}

document.addEventListener('click', (e) => {
    if (!e.target.closest('.context-menu-container')) {
        closeAllDropdowns();
    }
});

// Función Debounce para proteger a la API de sobrecarga
function debounce(func, delay = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => { func.apply(this, args); }, delay);
    };
}

// Formateador de moneda
const fmtCurrency = (val) => `S/ ${(val || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits:2})}`;

// Cargar Categorías para el dropdown
async function loadCategorias() {
    try {
        const categorias = await ApiClient.get('/inventario/categorias');
        window.categoriasList = categorias;
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

// Generador de Badges Semánticos con Tooltips Nativos
function generateBadgeHtml(text, type, tooltipText) {
    let classes = "px-2 py-1 rounded text-xs font-medium w-full text-center ";
    let extraHtml = "";
    
    if (type === 'critico') {
        classes += "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300 font-bold";
        extraHtml = `<span class="relative flex h-2 w-2 mr-1 inline-block">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
        </span>`;
    } else if (type === 'bajo') {
        classes += "bg-orange-50 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300 font-semibold";
    } else if (type === 'optimo') {
        classes += "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300";
    }

    return `
        <div class="relative group cursor-help inline-block w-full">
            <div class="inline-flex items-center justify-center ${classes}">
                ${extraHtml}${text}
            </div>
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
        label = "Estrella (A)";
        colorClass = "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300";
        tooltipText = "Genera el 80% de tus ingresos. Es vital mantenerlo abastecido.";
    } else if (abcClass === 'B') {
        label = "Frecuente (B)";
        colorClass = "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300";
        tooltipText = "Rotación estable. Contribuye de forma media a la facturación.";
    } else {
        label = "Lento (C)";
        colorClass = "bg-gray-50 text-gray-600 dark:bg-gray-700/50 dark:text-gray-300";
        tooltipText = "Baja relevancia. Su impacto en los ingresos totales es menor.";
    }

    return `
        <div class="relative group cursor-help inline-block">
            <div class="flex flex-col items-center">
                <span class="px-2 py-0.5 rounded text-xs font-black ${colorClass}">${label}</span>
                <span class="text-[10px] text-gray-500 dark:text-gray-400 font-semibold mt-0.5">${fmtCurrency(ingresos)}</span>
            </div>
            <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-56 p-2 bg-gray-800 dark:bg-gray-700 text-white text-xs rounded shadow-xl z-50 text-center whitespace-normal font-normal">
                ${tooltipText}
                <div class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800 dark:border-t-gray-700"></div>
            </div>
        </div>
    `;
}

async function refreshGlobalKPIs(force = false) {
    if (globalKPIsData && !force) {
        renderGlobalKPIs(globalKPIsData);
        return;
    }
    try {
        const res = await ApiClient.get('/inventario/kpis-globales');
        globalKPIsData = res;
        renderGlobalKPIs(res);
    } catch (e) {
        console.error("Error al cargar KPIs globales", e);
    }
}

function renderGlobalKPIs(data) {
    const kpis = data.kpis || {};
    const healthScore = kpis.salud_score || 0;
    
    if (kpiHealthScore) kpiHealthScore.textContent = healthScore;
    
    if (kpiHealthStatus) {
        const kpiHealthSubtitle = document.getElementById('kpi-health-subtitle');
        kpiHealthStatus.textContent = kpis.salud_status || 'Analizando...';
        
        if (healthScore >= 90) {
            kpiHealthStatus.className = "text-xs font-bold px-2 py-0.5 rounded text-green-700 bg-green-50 dark:bg-green-900/30 dark:text-green-300";
        } else if (healthScore >= 70) {
            kpiHealthStatus.className = "text-xs font-bold px-2 py-0.5 rounded text-blue-700 bg-blue-50 dark:bg-blue-900/30 dark:text-blue-300";
        } else if (healthScore >= 50) {
            kpiHealthStatus.className = "text-xs font-bold px-2 py-0.5 rounded text-orange-700 bg-orange-50 dark:bg-orange-900/30 dark:text-orange-300";
        } else {
            kpiHealthStatus.className = "text-xs font-bold px-2 py-0.5 rounded text-red-700 bg-red-50 dark:bg-red-900/30 dark:text-red-300";
        }
        if (kpiHealthSubtitle) kpiHealthSubtitle.textContent = kpis.salud_subtitle || '';
    }

    const accionesContainerGrid = document.getElementById('acciones-container-grid');
    if (accionesContainerGrid) {
        let summaryCardsHtml = "";

        if (kpis.solicitudes_en_proceso > 0) {
            summaryCardsHtml += `
                <div class="card p-5 border-l-4 border-amber-500 flex flex-col justify-between h-full hover:shadow-md transition-shadow">
                    <div class="flex items-start gap-3 mb-4">
                        <div class="w-10 h-10 rounded-full flex items-center justify-center shrink-0 bg-amber-100 dark:bg-amber-900/30 text-amber-500 text-lg">
                            <i class="fa-solid fa-clock"></i>
                        </div>
                        <div>
                            <h4 class="font-bold text-gray-800 dark:text-white text-sm">Solicitudes en Proceso</h4>
                            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1 leading-snug">
                                <b>${kpis.solicitudes_en_proceso} producto(s)</b> cuentan con orden de compra o reposición activa.
                            </p>
                        </div>
                    </div>
                    <button onclick="window.location.href='/compras?tab=planificacion'" class="w-full py-2 rounded-lg bg-amber-600 hover:bg-amber-700 text-xs font-bold text-white transition-colors shadow-sm flex items-center justify-center gap-1.5">
                        <i class="fa-solid fa-arrow-right-to-bracket"></i> Ver en Compras
                    </button>
                </div>
            `;
        }

        if (kpis.reabastecimiento_urgente > 0) {
            summaryCardsHtml += `
                <div class="card p-5 border-l-4 border-red-500 flex flex-col justify-between h-full hover:shadow-md transition-shadow">
                    <div class="flex items-start gap-3 mb-4">
                        <div class="w-10 h-10 rounded-full flex items-center justify-center shrink-0 bg-red-100 dark:bg-red-900/30 text-red-500 text-lg">
                            <i class="fa-solid fa-triangle-exclamation"></i>
                        </div>
                        <div>
                            <h4 class="font-bold text-gray-800 dark:text-white text-sm">Reabastecimiento Urgente</h4>
                            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1 leading-snug">
                                <b>${kpis.reabastecimiento_urgente} producto(s)</b> están en stock bajo o riesgo de quiebre.
                            </p>
                        </div>
                    </div>
                    <button onclick="filtrarPorEstadoQuick('Crítico')" class="w-full py-2 rounded-lg bg-red-600 hover:bg-red-700 text-xs font-bold text-white transition-colors shadow-sm flex items-center justify-center gap-1.5">
                        <i class="fa-solid fa-filter"></i> Gestionar en Tabla
                    </button>
                </div>
            `;
        }

        if (kpis.inventario_estable > 0) {
            summaryCardsHtml += `
                <div class="card p-5 border-l-4 border-green-500 flex flex-col justify-between h-full hover:shadow-md transition-shadow">
                    <div class="flex items-start gap-3 mb-4">
                        <div class="w-10 h-10 rounded-full flex items-center justify-center shrink-0 bg-green-100 dark:bg-green-900/30 text-green-500 text-lg">
                            <i class="fa-solid fa-circle-check"></i>
                        </div>
                        <div>
                            <h4 class="font-bold text-gray-800 dark:text-white text-sm">Inventario Estable</h4>
                            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1 leading-snug">
                                <b>${kpis.inventario_estable} producto(s)</b> fluyen óptimamente sin riesgo detectado.
                            </p>
                        </div>
                    </div>
                    <button onclick="filtrarPorEstadoQuick('Óptimo')" class="w-full py-2 rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-xs font-bold text-gray-700 dark:text-gray-200 transition-colors flex items-center justify-center gap-1.5">
                        <i class="fa-solid fa-filter"></i> Ver productos
                    </button>
                </div>
            `;
        }

        accionesContainerGrid.innerHTML = summaryCardsHtml || `
            <div class="card p-6 text-center text-gray-500 text-xs w-full col-span-full border border-dashed border-gray-200 dark:border-gray-700">
                <i class="fa-solid fa-circle-check text-4xl mb-3 text-green-500 opacity-80"></i>
                <p class="font-medium text-gray-700 dark:text-gray-300 text-lg">Todo está bajo control.</p>
                <p class="mt-1 text-sm">No hay acciones urgentes pendientes.</p>
            </div>
        `;
    }
}

async function refreshAllData(shouldHighlight = false) {
    await refreshGlobalKPIs(true);
    await fetchAndRenderData(1, shouldHighlight);
}

// Renderizador principal de tabla
async function fetchAndRenderData(page = 1, shouldHighlight = false) {
    currentPage = page;
    elTableLoading.classList.remove('hidden');
    elTableEmpty.classList.add('hidden');
    
    const params = {
        page: currentPage,
        size: pageSize
    };
    
    const q = elSearchInput.value.trim();
    if (q) params.q = q;
    
    const cat = elFilterCategoria.value;
    if (cat) params.id_categoria = cat;
    
    const est = elFilterEstado.value;
    if (est) params.estado_stock = est;
    
    try {
        const data = await ApiClient.get('/inventario/data', params);
        
        const productosList = data.items || data.productos || [];
        totalRecords = data.total_records !== undefined ? data.total_records : productosList.length;
        totalPages = data.pages || 1;
        currentPage = data.current_page || page;
        
        elTableBody.innerHTML = '';
        window.dashboardInsights = [];
        window.inventoryDataMap = {};
        
        if (productosList.length === 0) {
            elTableEmpty.classList.remove('hidden');
            elTableEmpty.style.display = 'flex';
        } else {
            elTableEmpty.style.display = 'none';
            productosList.forEach(prod => {
                window.dashboardInsights.push({
                    id: prod.idProducto,
                    tipo: prod.categoria,
                    producto: prod.nombre,
                    accion: prod.accion,
                    prioridad: prod.dias_quiebre || 999
                });
                window.inventoryDataMap[prod.idProducto] = prod;

                const tr = document.createElement('tr');
                tr.id = `fila-prod-${prod.idProducto}`;
                tr.className = "hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors cursor-pointer border-b border-gray-100 dark:border-gray-800";
                tr.onclick = (e) => {
                    if (e.target.closest('button') || e.target.closest('.context-menu-container')) return;
                    openOffCanvas(prod.idProducto);
                };
                
                if (prod.riesgo === 'Riesgo Alto' || prod.estado_fisico === 'Crítico') {
                    tr.classList.add('bg-red-50/20', 'dark:bg-red-900/10');
                }
                
                // Mapear Tipos de Estado Operacional
                let badgeEstado = 'optimo';
                let labelEstado = "Óptimo";
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

                // Definir Acción Principal (Badges clickeables)
                let accionPrincipalHtml = "";
                if (prod.tiene_solicitud_pendiente) {
                    accionPrincipalHtml = `
                        <button onclick="event.stopPropagation(); window.location.href='/compras?tab=planificacion${prod.id_solicitud_pendiente ? '&hl_req=' + prod.id_solicitud_pendiente : ''}'" class="w-full max-w-[130px] text-xs font-bold text-amber-700 bg-amber-100 hover:bg-amber-200 dark:bg-amber-900/40 dark:text-amber-300 py-1.5 px-2.5 rounded-lg flex items-center justify-center gap-1.5 shadow-sm transition-all" title="Ver solicitud activa en Compras">
                            ⏳ En proceso
                        </button>`;
                } else if (prod.accion === 'Reponer' || prod.estado_fisico === 'Crítico') {
                    accionPrincipalHtml = `
                        <button onclick="event.stopPropagation(); openSolicitudManualModal(${prod.idProducto})" class="w-full max-w-[130px] text-xs font-bold text-red-700 bg-red-100 hover:bg-red-200 dark:bg-red-900/40 dark:text-red-300 py-1.5 px-2.5 rounded-lg flex items-center justify-center gap-1.5 shadow-sm transition-all" title="Crear solicitud de compra rápida">
                            🔴 Reponer
                        </button>`;
                } else if (prod.estado_fisico === 'Bajo') {
                    accionPrincipalHtml = `
                        <button onclick="event.stopPropagation(); openSolicitudManualModal(${prod.idProducto})" class="w-full max-w-[130px] text-xs font-bold text-orange-700 bg-orange-100 hover:bg-orange-200 dark:bg-orange-900/40 dark:text-orange-300 py-1.5 px-2.5 rounded-lg flex items-center justify-center gap-1.5 shadow-sm transition-all" title="Preparar reposición de stock">
                            🟠 Atención
                        </button>`;
                } else {
                    accionPrincipalHtml = `
                        <button onclick="event.stopPropagation(); openOffCanvas(${prod.idProducto})" class="w-full max-w-[130px] text-xs font-bold text-green-700 bg-green-100 hover:bg-green-200 dark:bg-green-900/40 dark:text-green-300 py-1.5 px-2.5 rounded-lg flex items-center justify-center gap-1.5 shadow-sm transition-all" title="Inventario saludable. Ver detalle en Off-Canvas">
                            🟢 Mantener
                        </button>`;
                }

                // Construcción de Especificaciones secundarias (Talla, Color, Marca)
                let specs = [];
                if (prod.marca) specs.push(`<span class="text-[10px] text-gray-500 bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded border border-gray-200/60 dark:border-gray-700/60 font-semibold">🏷️ ${prod.marca}</span>`);
                if (prod.talla) specs.push(`<span class="text-[10px] text-gray-500 bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded border border-gray-200/60 dark:border-gray-700/60 font-semibold">📏 ${prod.talla}</span>`);
                if (prod.color) specs.push(`<span class="text-[10px] text-gray-500 bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded border border-gray-200/60 dark:border-gray-700/60 font-semibold">🎨 ${prod.color}</span>`);
                let specsHtml = specs.length > 0 ? `<div class="flex gap-1 flex-wrap mt-1">${specs.join('')}</div>` : '';

                // Construcción de Fila en exactamente 7 Columnas
                tr.innerHTML = `
                    <td class="py-3.5 px-4">
                        <div class="flex flex-col gap-1">
                            <div class="flex items-center gap-2">
                                <span class="text-sm font-bold text-gray-900 dark:text-white leading-tight">${prod.nombre}</span>
                                <span class="font-mono text-[11px] text-gray-500 bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded border border-gray-200 dark:border-gray-700">
                                    ${prod.codigoBarras || '-'}
                                </span>
                            </div>
                            ${specsHtml}
                            ${prod.reglas_vinculadas_texto ? `
                                <span class="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5 font-medium flex items-center gap-1">
                                    <i class="fa-solid fa-diagram-project text-purple-500 text-[10px]"></i>
                                    <span>${prod.reglas_vinculadas_texto}</span>
                                </span>` : ''}
                        </div>
                    </td>
                    <td class="py-3.5 px-4 whitespace-nowrap text-center">
                        <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-gray-100 dark:bg-slate-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-slate-700">
                            ${prod.categoria}
                        </span>
                    </td>
                    <td class="py-3.5 px-4 whitespace-nowrap text-center">
                        ${generateAbcBadge(prod.abc, prod.ingresos_generados)}
                    </td>
                    <td class="py-3.5 px-4 whitespace-nowrap text-center">
                        <div class="text-base font-extrabold ${prod.stock <= 5 ? 'text-red-500' : 'text-gray-800 dark:text-gray-200'}">
                            ${prod.stock} <span class="text-xs font-normal text-gray-400">uds</span>
                        </div>
                    </td>
                    <td class="py-3.5 px-4 whitespace-nowrap text-center max-w-[130px]">
                        ${generateBadgeHtml(labelEstado, badgeEstado, ttEstado)}
                    </td>
                    <td class="py-3.5 px-4 whitespace-nowrap text-center">
                        <div class="flex justify-center">
                            ${accionPrincipalHtml}
                        </div>
                    </td>
                    <td class="py-3.5 px-4 whitespace-nowrap text-center">
                        <div class="relative inline-block text-left context-menu-container">
                            <button onclick="toggleContextMenu(${prod.idProducto}, event)" class="w-8 h-8 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700/60 text-gray-500 flex items-center justify-center transition-colors">
                                <i class="fa-solid fa-ellipsis-vertical text-sm"></i>
                            </button>
                            <div id="context-menu-${prod.idProducto}" class="hidden context-menu-dropdown absolute right-0 mt-1 w-48 rounded-xl bg-white dark:bg-gray-800 shadow-xl border border-gray-100 dark:border-gray-700 z-50 py-1 font-medium text-xs">
                                <button onclick="event.stopPropagation(); closeAllDropdowns(); openSolicitudManualModal(${prod.idProducto})" class="w-full text-left px-4 py-2 hover:bg-blue-50 hover:text-blue-600 dark:hover:bg-gray-700/60 text-gray-700 dark:text-gray-200 flex items-center gap-2">
                                    <i class="fa-solid fa-clipboard-question text-blue-500 w-4"></i> Registrar solicitud
                                </button>
                                <button onclick="event.stopPropagation(); closeAllDropdowns(); openEditProductModal(${prod.idProducto})" class="w-full text-left px-4 py-2 hover:bg-amber-50 hover:text-amber-600 dark:hover:bg-gray-700/60 text-gray-700 dark:text-gray-200 flex items-center gap-2">
                                    <i class="fa-solid fa-pen-to-square text-amber-500 w-4"></i> Editar
                                </button>
                                <button onclick="event.stopPropagation(); closeAllDropdowns(); openOffCanvas(${prod.idProducto})" class="w-full text-left px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-700/60 text-gray-700 dark:text-gray-200 flex items-center gap-2 border-t border-gray-100 dark:border-gray-700/50">
                                    <i class="fa-solid fa-eye text-gray-400 w-4"></i> Ver detalle
                                </button>
                            </div>
                        </div>
                    </td>
                `;
                
                elTableBody.appendChild(tr);
            });
        }

        renderPaginationControls(data);
        updateActiveFilterBadge();

        if (shouldHighlight) {
            const rows = elTableBody.querySelectorAll('tr');
            rows.forEach(r => r.classList.add('bg-amber-100/70', 'dark:bg-amber-900/30', 'transition-colors', 'duration-500'));
            setTimeout(() => {
                rows.forEach(r => r.classList.remove('bg-amber-100/70', 'dark:bg-amber-900/30'));
            }, 2000);
        }

    } catch (e) {
        console.error("Error obteniendo datos del inventario", e);
        elTableBody.innerHTML = `<tr><td colspan="7" class="text-center text-red-500 p-4">Error cargando los datos. Ver consola.</td></tr>`;
    } finally {
        elTableLoading.classList.add('hidden');
    }
}

// RENDERIZADOR DE CONTROLES DE PAGINACIÓN DE TABLA
function renderPaginationControls(data) {
    const infoEl = document.getElementById('pagination-info');
    const controlsEl = document.getElementById('pagination-controls');
    if (!infoEl || !controlsEl) return;

    const page = data.current_page || 1;
    const totalP = data.pages || 1;
    const totalR = data.total_records || 0;
    const size = data.page_size || 20;

    if (totalR === 0) {
        infoEl.textContent = 'Mostrando 0 productos';
        controlsEl.innerHTML = '';
        return;
    }

    const start = (page - 1) * size + 1;
    const end = Math.min(page * size, totalR);
    infoEl.textContent = `Mostrando ${start} - ${end} de ${totalR} productos`;

    let html = '';
    
    // Botón Anterior
    const prevDisabled = page <= 1;
    html += `
        <button onclick="goToPage(${page - 1})" ${prevDisabled ? 'disabled' : ''} class="px-2.5 py-1 rounded border border-gray-200 dark:border-gray-700 font-bold ${prevDisabled ? 'opacity-40 cursor-not-allowed text-gray-400' : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200'} transition-colors">
            <i class="fa-solid fa-chevron-left text-[10px]"></i>
        </button>
    `;

    // Botones numéricos
    let startPage = Math.max(1, page - 2);
    let endPage = Math.min(totalP, startPage + 4);
    if (endPage - startPage < 4) {
        startPage = Math.max(1, endPage - 4);
    }

    for (let p = startPage; p <= endPage; p++) {
        const isCurrent = p === page;
        html += `
            <button onclick="goToPage(${p})" class="px-3 py-1 rounded text-xs font-bold ${isCurrent ? 'bg-amber-500 text-white shadow-sm' : 'border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700'} transition-colors">
                ${p}
            </button>
        `;
    }

    // Botón Siguiente
    const nextDisabled = page >= totalP;
    html += `
        <button onclick="goToPage(${page + 1})" ${nextDisabled ? 'disabled' : ''} class="px-2.5 py-1 rounded border border-gray-200 dark:border-gray-700 font-bold ${nextDisabled ? 'opacity-40 cursor-not-allowed text-gray-400' : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200'} transition-colors">
            <i class="fa-solid fa-chevron-right text-[10px]"></i>
        </button>
    `;

    controlsEl.innerHTML = html;
}

function goToPage(pageNum) {
    if (pageNum < 1 || pageNum > totalPages) return;
    fetchAndRenderData(pageNum);
}



// NUEVAS FUNCIONES DE INTERACTIVIDAD (MODALES, TOASTS Y OFFCANVAS)

function scrollToProduct(id) {
    const el = document.getElementById(`fila-prod-${id}`);
    if (el) {
        el.scrollIntoView({behavior: 'smooth', block: 'center'});
        el.classList.add('bg-yellow-100', 'dark:bg-yellow-900/30');
        setTimeout(() => {
            el.classList.remove('bg-yellow-100', 'dark:bg-yellow-900/30');
        }, 2000);
    }
}



function showToast(message, type='info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `px-4 py-3 rounded shadow-lg text-sm font-medium text-white flex items-center gap-2 transform transition-all duration-300 translate-y-full opacity-0 pointer-events-auto ${type === 'info' ? 'bg-blue-600' : 'bg-green-600'}`;
    toast.innerHTML = `<i class="fa-solid fa-circle-info"></i> ${message}`;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.remove('translate-y-full', 'opacity-0');
    }, 10);
    
    setTimeout(() => {
        toast.classList.add('translate-y-full', 'opacity-0');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// PANEL LATERAL OFFCANVAS ENRIQUECIDO
function openOffCanvas(id) {
    const prod = window.inventoryDataMap[id];
    if (!prod) return;
    
    const panel = document.getElementById('offcanvas-panel');
    const title = document.getElementById('offcanvas-title');
    const content = document.getElementById('offcanvas-content');
    
    title.textContent = prod.nombre;
    
    // Especificaciones
    let specs = [];
    if (prod.marca) specs.push(`<span class="text-xs font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 dark:text-gray-300 px-2 py-0.5 rounded">🏷️ Marca: ${prod.marca}</span>`);
    if (prod.talla) specs.push(`<span class="text-xs font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 dark:text-gray-300 px-2 py-0.5 rounded">📏 Talla: ${prod.talla}</span>`);
    if (prod.color) specs.push(`<span class="text-xs font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 dark:text-gray-300 px-2 py-0.5 rounded">🎨 Color: ${prod.color}</span>`);

    content.innerHTML = `
        <div class="space-y-6">
            <!-- Header con código barras -->
            <div class="flex items-center justify-between">
                <span class="font-mono text-xs font-bold text-gray-500 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded border border-gray-200 dark:border-gray-700 select-all">
                    <i class="fa-solid fa-barcode mr-1"></i>${prod.codigoBarras || 'Sin SKU'}
                </span>
                <span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-50 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300">
                    Cat: ${prod.categoria}
                </span>
            </div>

            ${specs.length > 0 ? `<div class="flex gap-2 flex-wrap">${specs.join('')}</div>` : ''}

            <!-- Resumen de Negocio (Métricas clave movidas de la tabla) -->
            <div class="bg-gray-50 dark:bg-gray-800/50 p-4 rounded-xl border border-gray-100 dark:border-gray-700/60">
                <h4 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Métricas Financieras y Rotación</h4>
                <div class="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <span class="block text-gray-500 text-xs">Stock Disponible</span>
                        <span class="font-black text-lg ${prod.stock <= 5 ? 'text-red-500' : 'text-gray-800 dark:text-white'}">${prod.stock} uds</span>
                    </div>
                    <div>
                        <span class="block text-gray-500 text-xs">Margen de Ganancia</span>
                        <span class="font-black text-lg text-green-600 dark:text-green-400">${prod.margen}%</span>
                    </div>
                    <div>
                        <span class="block text-gray-500 text-xs">Días para Quiebre</span>
                        <span class="font-bold text-base ${prod.dias_quiebre < 7 ? 'text-red-500' : 'text-gray-700 dark:text-gray-300'}">${prod.dias_quiebre ? prod.dias_quiebre + ' días' : 'Sin datos'}</span>
                    </div>
                    <div>
                        <span class="block text-gray-500 text-xs">Clasificación ABC</span>
                        <span class="font-bold text-base text-blue-600 dark:text-blue-400">Clase ${prod.abc}</span>
                    </div>
                </div>
            </div>
            
            <!-- Diagnóstico Operacional -->
            <div>
                <h4 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Diagnóstico Operacional</h4>
                <div class="space-y-2.5">
                    <div class="p-3 border border-gray-100 dark:border-gray-700 rounded-lg flex gap-3 items-center bg-white dark:bg-gray-800/40">
                        <i class="fa-solid fa-heart-pulse text-blue-500"></i>
                        <div>
                            <span class="block font-semibold text-xs text-gray-800 dark:text-gray-200">Estado Físico</span>
                            <span class="text-xs text-gray-500">${prod.estado_fisico}</span>
                        </div>
                    </div>
                    <div class="p-3 border border-gray-100 dark:border-gray-700 rounded-lg flex gap-3 items-center bg-white dark:bg-gray-800/40">
                        <i class="fa-solid fa-chart-line text-purple-500"></i>
                        <div>
                            <span class="block font-semibold text-xs text-gray-800 dark:text-gray-200">Riesgo Futuro</span>
                            <span class="text-xs text-gray-500">${prod.riesgo}</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Venta Cruzada (Reglas) -->
            <div>
                <h4 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Venta Cruzada</h4>
                <div class="p-3 rounded-lg bg-purple-50/60 dark:bg-purple-950/30 border border-purple-100 dark:border-purple-900/50 text-xs text-purple-800 dark:text-purple-300 font-medium">
                    <i class="fa-solid fa-diagram-project mr-1 text-purple-600"></i>
                    ${prod.reglas_vinculadas_texto || 'Sin patrones de compra combinada registrados.'}
                </div>
            </div>
            
            <!-- Botones de Acción Directa -->
            <div class="pt-4 border-t border-gray-100 dark:border-gray-700 flex gap-3">
                <button onclick="closeOffCanvas(); openSolicitudManualModal(${prod.idProducto})" class="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-bold py-2.5 px-3 rounded-lg text-xs shadow transition-colors flex items-center justify-center gap-1.5">
                    <i class="fa-solid fa-clipboard-question"></i> Registrar solicitud
                </button>
                <button onclick="closeOffCanvas(); openEditProductModal(${prod.idProducto})" class="px-4 py-2.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-lg text-xs font-bold transition-colors">
                    Editar
                </button>
            </div>
        </div>
    `;
    
    panel.classList.remove('translate-x-full');
    
    // Cargar historial de abastecimiento
    cargarHistorialAbastecimiento(prod.idProducto);
}

async function cargarHistorialAbastecimiento(idProducto) {
    const containerId = 'historial-abastecimiento-container';
    const content = document.getElementById('offcanvas-content');
    
    let histContainer = document.getElementById(containerId);
    if (!histContainer) {
        histContainer = document.createElement('div');
        histContainer.id = containerId;
        histContainer.className = "mt-6";
        
        const actionBtnDiv = content.querySelector('.pt-4.border-t');
        if (actionBtnDiv) {
            content.querySelector('.space-y-6').insertBefore(histContainer, actionBtnDiv);
        } else {
            content.querySelector('.space-y-6').appendChild(histContainer);
        }
    }
    
    histContainer.innerHTML = `<h4 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3"><i class="fa-solid fa-truck-fast"></i> Historial de Abastecimiento</h4><div class="text-center text-xs text-gray-400 py-2">Consultando historial...</div>`;
    
    try {
        const res = await ApiClient.get(`/compras/historial/${idProducto}`);
        const historial = res.historial || [];
        
        if (historial.length === 0) {
            histContainer.innerHTML = `<h4 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3"><i class="fa-solid fa-truck-fast"></i> Historial de Abastecimiento</h4><div class="p-3 border border-gray-100 dark:border-gray-700 rounded-lg text-center text-xs text-gray-500">No hay registros de compras para este producto.</div>`;
            return;
        }
        
        const historyHTML = historial.map(h => {
            const fechaFormateada = new Date(h.fecha).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' });
            let estadoClass = h.estado === 'Completada' ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300' : 'bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300';
            
            return `
            <div class="p-3 border-b border-gray-100 dark:border-gray-700 last:border-0 flex justify-between items-center bg-white dark:bg-gray-800 rounded-lg mb-2 shadow-sm">
                <div>
                    <div class="text-xs font-bold text-gray-800 dark:text-gray-200">${h.proveedor}</div>
                    <div class="text-[10px] text-gray-500">${fechaFormateada} • ${h.cantidad} uds</div>
                </div>
                <div class="text-[10px] font-bold px-2 py-0.5 rounded ${estadoClass}">${h.estado}</div>
            </div>`;
        }).join('');
        
        histContainer.innerHTML = `<h4 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3"><i class="fa-solid fa-truck-fast"></i> Historial de Abastecimiento</h4><div>${historyHTML}</div>`;
        
    } catch (e) {
        console.error("Error cargando historial", e);
        histContainer.innerHTML = `<h4 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3"><i class="fa-solid fa-truck-fast"></i> Historial de Abastecimiento</h4><div class="text-center text-xs text-red-500 py-2">Error cargando historial</div>`;
    }
}

function closeOffCanvas() {
    const panel = document.getElementById('offcanvas-panel');
    panel.classList.add('translate-x-full');
}

// Event Listeners principales
document.addEventListener('DOMContentLoaded', () => {
    loadCategorias().then(() => refreshAllData());
    
    const debouncedSearch = debounce(() => {
        fetchAndRenderData(1);
    }, 300);
    
    elSearchInput.addEventListener('input', debouncedSearch);
    elFilterCategoria.addEventListener('change', () => fetchAndRenderData(1));
    elFilterEstado.addEventListener('change', () => fetchAndRenderData(1));
});

function goToProduct(id) {
    scrollToProduct(id);
}

// FUNCIONES DE FILTROS Y NUEVO PRODUCTO EN BD

function filtrarPorEstadoQuick(estado) {
    elSearchInput.value = '';
    elFilterCategoria.value = '';
    elFilterEstado.value = estado;
    fetchAndRenderData(1, true);
}

function updateActiveFilterBadge() {
    const container = document.getElementById('active-filter-badge-container');
    const textEl = document.getElementById('active-filter-badge-text');
    if (!container || !textEl) return;

    if (elFilterEstado.value) {
        textEl.textContent = `Estado ${elFilterEstado.value.toLowerCase()}`;
        container.classList.remove('hidden');
    } else if (elFilterCategoria.value && elFilterCategoria.options[elFilterCategoria.selectedIndex]) {
        textEl.textContent = `Categoría: ${elFilterCategoria.options[elFilterCategoria.selectedIndex].text}`;
        container.classList.remove('hidden');
    } else if (elSearchInput.value.trim()) {
        textEl.textContent = `Búsqueda: "${elSearchInput.value.trim()}"`;
        container.classList.remove('hidden');
    } else {
        container.classList.add('hidden');
    }
}

function clearFilters() {
    elSearchInput.value = '';
    elFilterCategoria.value = '';
    elFilterEstado.value = '';
    const badgeContainer = document.getElementById('active-filter-badge-container');
    if (badgeContainer) badgeContainer.classList.add('hidden');
    fetchAndRenderData();
}

// GESTIÓN DE CATEGORÍAS DINÁMICAS Y MODALES (NUEVO & EDITAR)

function handleCategorySelectChange(selectEl, wrapperId) {
    const wrapper = document.getElementById(wrapperId);
    if (!wrapper) return;
    if (selectEl.value === '__NEW__') {
        wrapper.classList.remove('hidden');
    } else {
        wrapper.classList.add('hidden');
    }
}

function populateCategorySelect(selectEl, currentVal = '') {
    if (!selectEl || !window.categoriasList) return;
    selectEl.innerHTML = '<option value="">Seleccionar Categoría</option>';
    window.categoriasList.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.id;
        opt.textContent = c.nombre;
        selectEl.appendChild(opt);
    });
    const newOpt = document.createElement('option');
    newOpt.value = '__NEW__';
    newOpt.textContent = '➕ Crear Nueva Categoría...';
    newOpt.className = 'font-bold text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/30';
    selectEl.appendChild(newOpt);

    if (currentVal) selectEl.value = currentVal;
}

async function resolveCategoryId(selectId, inputNewCatId) {
    const select = document.getElementById(selectId);
    const val = select ? select.value : '';
    if (val === '__NEW__') {
        const inputNew = document.getElementById(inputNewCatId);
        const newCatName = inputNew ? inputNew.value.trim() : '';
        if (!newCatName) {
            throw new Error('Debes ingresar el nombre para la nueva categoría');
        }
        const resCat = await ApiClient.post('/inventario/categoria', { nombreCategoria: newCatName });
        await loadCategorias(); // Recargar lista global de categorías
        return resCat.id;
    }
    const catId = parseInt(val);
    if (isNaN(catId) || catId <= 0) {
        throw new Error('Por favor selecciona una categoría válida');
    }
    return catId;
}

function openNewProductModal() {
    const modal = document.getElementById('modal-nuevo-producto');
    const selectCat = document.getElementById('new-prod-categoria');
    const wrapperCat = document.getElementById('wrapper-nueva-categoria-new');
    if (!modal || !selectCat) return;

    populateCategorySelect(selectCat);
    if (wrapperCat) wrapperCat.classList.add('hidden');

    const form = document.getElementById('form-nuevo-producto');
    if (form) form.reset();
    document.getElementById('new-prod-stock').value = 0;

    modal.classList.remove('hidden');
    setTimeout(() => modal.classList.remove('opacity-0'), 10);
}

function closeNewProductModal() {
    const modal = document.getElementById('modal-nuevo-producto');
    if (!modal) return;
    modal.classList.add('opacity-0');
    setTimeout(() => modal.classList.add('hidden'), 300);
}

async function saveNewProduct(e) {
    e.preventDefault();
    const nombre = document.getElementById('new-prod-nombre').value.trim();
    const codigoBarras = document.getElementById('new-prod-codigo').value.trim();
    const precioLista = parseFloat(document.getElementById('new-prod-precio').value);
    const costoProducto = parseFloat(document.getElementById('new-prod-costo').value);
    const marca = document.getElementById('new-prod-marca').value.trim();
    const talla = document.getElementById('new-prod-talla').value.trim();
    const color = document.getElementById('new-prod-color').value.trim();

    if (!nombre || isNaN(precioLista) || isNaN(costoProducto)) {
        showToast('Por favor completa los campos requeridos (*)', 'info');
        return;
    }

    try {
        const idCategoria = await resolveCategoryId('new-prod-categoria', 'new-prod-nueva-cat-input');

        const payload = {
            nombre,
            idCategoria,
            precioLista,
            costoProducto,
            codigoBarras: codigoBarras || null,
            stockInicial: 0,
            marca: marca || null,
            talla: talla || null,
            color: color || null
        };

        const res = await ApiClient.post('/inventario/producto', payload);
        showToast('✅ Producto registrado correctamente.', 'success');
        closeNewProductModal();
        await refreshAllData();
    } catch (err) {
        console.error("Error registrando producto", err);
        showToast(`❌ ${err.message || 'Error guardando producto en la BD'}`, 'info');
    }
}

// FUNCIONES DE EDICIÓN DE PRODUCTO

function openEditProductModal(idProduct) {
    const prod = window.inventoryDataMap[idProduct];
    if (!prod) return;

    const modal = document.getElementById('modal-editar-producto');
    const selectCat = document.getElementById('edit-prod-categoria');
    const wrapperCat = document.getElementById('wrapper-nueva-categoria-edit');
    if (!modal || !selectCat) return;

    populateCategorySelect(selectCat, prod.idCategoria);
    if (wrapperCat) wrapperCat.classList.add('hidden');

    document.getElementById('edit-prod-id').value = prod.idProducto;
    document.getElementById('edit-prod-nombre').value = prod.nombre;
    document.getElementById('edit-prod-codigo').value = prod.codigoBarras !== '-' ? prod.codigoBarras : '';
    document.getElementById('edit-prod-precio').value = prod.precio;
    document.getElementById('edit-prod-costo').value = prod.costo;
    document.getElementById('edit-prod-marca').value = prod.marca || '';
    document.getElementById('edit-prod-talla').value = prod.talla || '';
    document.getElementById('edit-prod-color').value = prod.color || '';

    modal.classList.remove('hidden');
    setTimeout(() => modal.classList.remove('opacity-0'), 10);
}

function closeEditProductModal() {
    const modal = document.getElementById('modal-editar-producto');
    if (!modal) return;
    modal.classList.add('opacity-0');
    setTimeout(() => modal.classList.add('hidden'), 300);
}

async function saveEditProduct(e) {
    e.preventDefault();
    const idProduct = document.getElementById('edit-prod-id').value;
    const nombre = document.getElementById('edit-prod-nombre').value.trim();
    const codigoBarras = document.getElementById('edit-prod-codigo').value.trim();
    const precioLista = parseFloat(document.getElementById('edit-prod-precio').value);
    const costoProducto = parseFloat(document.getElementById('edit-prod-costo').value);
    const marca = document.getElementById('edit-prod-marca').value.trim();
    const talla = document.getElementById('edit-prod-talla').value.trim();
    const color = document.getElementById('edit-prod-color').value.trim();

    if (!idProduct || !nombre || isNaN(precioLista) || isNaN(costoProducto)) {
        showToast('Por favor completa todos los campos requeridos (*)', 'info');
        return;
    }

    try {
        const idCategoria = await resolveCategoryId('edit-prod-categoria', 'edit-prod-nueva-cat-input');

        const payload = {
            nombre,
            idCategoria,
            precioLista,
            costoProducto,
            codigoBarras: codigoBarras || null,
            marca: marca || null,
            talla: talla || null,
            color: color || null
        };

        const res = await ApiClient.put(`/inventario/producto/${idProduct}`, payload);
        showToast('✅ Producto actualizado correctamente.', 'success');
        closeEditProductModal();
        await refreshAllData();
    } catch (err) {
        console.error("Error editando producto", err);
        showToast(`❌ ${err.message || 'No se pudo actualizar el producto'}`, 'info');
    }
}

// FUNCIONES DE SOLICITUD MANUAL DE REPOSICIÓN

function handleMotivoSelectChange(selectEl) {
    const wrapper = document.getElementById('wrapper-motivo-otro');
    if (!wrapper) return;
    if (selectEl.value === '__OTRO__') {
        wrapper.classList.remove('hidden');
    } else {
        wrapper.classList.add('hidden');
    }
}

function openSolicitudManualModal(idProduct) {
    const prod = window.inventoryDataMap[idProduct];
    if (!prod) return;

    const modal = document.getElementById('modal-registrar-solicitud');
    if (!modal) return;

    document.getElementById('sol-prod-id').value = prod.idProducto;
    document.getElementById('sol-prod-nombre-display').textContent = `${prod.nombre} (${prod.codigoBarras && prod.codigoBarras !== '-' ? prod.codigoBarras : 'Sin SKU'})`;

    const sugVal = prod.stock <= 5 ? Math.max(10, Math.round((prod.stock || 1) * 1.5)) : 10;
    const elSugDisplay = document.getElementById('sol-cantidad-sugerida-display');
    if (elSugDisplay) {
        elSugDisplay.innerHTML = `<i class="fa-solid fa-calculator text-xs"></i> <span>${sugVal} uds (basado en demanda)</span>`;
    }
    
    document.getElementById('sol-cantidad').value = sugVal;

    const selectMotivo = document.getElementById('sol-motivo');
    if (selectMotivo) selectMotivo.value = "Reposición manual";

    const wrapperOtro = document.getElementById('wrapper-motivo-otro');
    if (wrapperOtro) wrapperOtro.classList.add('hidden');

    const inputOtro = document.getElementById('sol-motivo-otro');
    if (inputOtro) inputOtro.value = "";

    const elProv = document.getElementById('sol-proveedor');
    if (elProv) elProv.value = "";

    const elObs = document.getElementById('sol-observaciones');
    if (elObs) elObs.value = "";

    modal.classList.remove('hidden');
    setTimeout(() => modal.classList.remove('opacity-0'), 10);
}

function closeSolicitudManualModal() {
    const modal = document.getElementById('modal-registrar-solicitud');
    if (!modal) return;
    modal.classList.add('opacity-0');
    setTimeout(() => modal.classList.add('hidden'), 300);
}

async function saveSolicitudManual(e) {
    e.preventDefault();
    const idProducto = parseInt(document.getElementById('sol-prod-id').value);
    const cantidad = parseInt(document.getElementById('sol-cantidad').value);
    const selectMotivo = document.getElementById('sol-motivo').value;
    const proveedor = document.getElementById('sol-proveedor')?.value.trim() || '';
    const observaciones = document.getElementById('sol-observaciones')?.value.trim() || '';

    let motivoFinal = selectMotivo;
    if (selectMotivo === '__OTRO__') {
        const inputOtro = document.getElementById('sol-motivo-otro');
        motivoFinal = inputOtro ? inputOtro.value.trim() : '';
        if (!motivoFinal) {
            showToast('Por favor especifica el motivo de la solicitud', 'info');
            return;
        }
    }

    if (proveedor) {
        motivoFinal += ` [Proveedor: ${proveedor}]`;
    }
    if (observaciones) {
        motivoFinal += ` - Obs: ${observaciones}`;
    }

    if (isNaN(idProducto) || isNaN(cantidad) || cantidad <= 0) {
        showToast('Por favor ingresa una cantidad válida', 'info');
        return;
    }

    try {
        const payload = {
            idProducto,
            cantidad_sugerida: cantidad,
            motivo: motivoFinal,
            origen: "Manual"
        };

        const res = await ApiClient.post('/compras/solicitud', payload);
        showToast('✅ Solicitud de compra creada correctamente', 'success');
        closeSolicitudManualModal();
        await refreshAllData();
    } catch (err) {
        console.error("Error registrando solicitud manual", err);
        showToast(`❌ ${err.message || 'No se pudo guardar la solicitud'}`, 'info');
    }
}
