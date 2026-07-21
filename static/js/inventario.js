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

window.dashboardInsights = [];
window.inventoryDataMap = {};

// Función Debounce para proteger a la API de sobrecarga
function debounce(func, delay = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => { func.apply(this, args); }, delay);
    };
}

// Formateador de moneda
const fmtCurrency = (val) => `S/ ${val.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits:2})}`;

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
        
        window.dashboardInsights = [];
        window.inventoryDataMap = {};
        
        if (data.productos.length === 0) {
            elTableEmpty.classList.remove('hidden');
            elTableEmpty.style.display = 'flex';
        } else {
            elTableEmpty.style.display = 'none';
            data.productos.forEach(prod => {
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
                tr.className = "hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors cursor-pointer";
                tr.onclick = (e) => {
                    if (e.target.closest('button')) return;
                    openOffCanvas(prod.idProducto);
                };
                
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

                if (prod.tiene_solicitud_pendiente && accionesRecomendadas.length < 6) {
                    accionesRecomendadas.push({
                        id: prod.idProducto,
                        idSolicitud: prod.id_solicitud_pendiente,
                        rawAccion: 'EnProceso',
                        icon: 'fa-clock',
                        borderColor: 'border-amber-500',
                        iconBg: 'bg-amber-100 dark:bg-amber-900/30',
                        iconColor: 'text-amber-500',
                        btnBg: 'bg-amber-600 hover:bg-amber-700',
                        btnText: 'Revisar solicitud',
                        title: 'Solicitud en Proceso',
                        desc: `<b>${prod.nombre}</b> ya cuenta con una solicitud de reposición activa.`
                    });
                } else if (prod.accion === 'Reponer' && accionesRecomendadas.length < 6) {
                    accionesRecomendadas.push({
                        id: prod.idProducto, rawAccion: 'Reponer',
                        icon: 'fa-truck-ramp-box', borderColor: 'border-red-500', iconBg: 'bg-red-100 dark:bg-red-900/30', iconColor: 'text-red-500', btnBg: 'bg-red-600',
                        btnText: 'Resolver',
                        title: 'Quiebre de Stock',
                        desc: `<b>${prod.nombre}</b> se agotará en ${prod.dias_quiebre || 0} días.`
                    });
                } else if (prod.accion === 'Liquidar' && accionesRecomendadas.length < 6) {
                    accionesRecomendadas.push({
                        id: prod.idProducto, rawAccion: 'Liquidar',
                        icon: 'fa-tag', borderColor: 'border-orange-500', iconBg: 'bg-orange-100 dark:bg-orange-900/30', iconColor: 'text-orange-500', btnBg: 'bg-orange-500',
                        btnText: 'Resolver',
                        title: 'Stock Inmovilizado',
                        desc: `<b>${prod.nombre}</b> no tiene rotación reciente.`
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
                    if (prod.tiene_solicitud_pendiente) {
                        accionBtn = `<div class="relative group cursor-help w-full"><button disabled class="w-full text-xs font-bold text-gray-500 bg-gray-100 dark:bg-slate-800 dark:text-gray-400 py-1.5 px-2 rounded opacity-50 flex items-center justify-center gap-1.5 shadow-sm cursor-not-allowed">⏳ En proceso</button><div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-56 p-2 bg-gray-800 dark:bg-gray-700 text-white text-xs rounded shadow-xl z-50 text-center whitespace-normal font-normal">Ya existe una solicitud de reposición activa para este producto.<div class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800 dark:border-t-gray-700"></div></div></div>`;
                    } else {
                        accionBtn = `<div class="relative group cursor-help w-full"><button onclick="event.stopPropagation(); openActionModal(${prod.idProducto}, 'Reponer')" class="w-full text-xs font-bold text-red-600 bg-red-100 dark:bg-red-900/40 dark:text-red-300 py-1.5 px-2 rounded transition-transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-1.5 shadow-sm">🔴 Reponer</button><div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-56 p-2 bg-gray-800 dark:bg-gray-700 text-white text-xs rounded shadow-xl z-50 text-center whitespace-normal font-normal">No tienes stock suficiente para terminar la semana.<div class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800 dark:border-t-gray-700"></div></div></div>`;
                    }
                } else if (prod.accion === "Liquidar") {
                    accionBtn = `<div class="relative group cursor-help w-full"><button onclick="event.stopPropagation(); openActionModal(${prod.idProducto}, 'Liquidar')" class="w-full text-xs font-bold text-orange-600 bg-orange-100 dark:bg-orange-900/40 dark:text-orange-300 py-1.5 px-2 rounded transition-transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-1.5 shadow-sm">🟠 Liquidar</button><div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-56 p-2 bg-gray-800 dark:bg-gray-700 text-white text-xs rounded shadow-xl z-50 text-center whitespace-normal font-normal">Este producto no se vende. Aprovecha su margen para hacer una oferta.<div class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800 dark:border-t-gray-700"></div></div></div>`;
                } else {
                    accionBtn = `<div class="relative group cursor-help w-full"><button onclick="event.stopPropagation(); openActionModal(${prod.idProducto}, 'Mantener')" class="w-full text-xs font-bold text-gray-600 bg-gray-100 dark:bg-gray-700 dark:text-gray-300 py-1.5 px-2 rounded transition-colors flex items-center justify-center gap-1.5 cursor-pointer">🟢 Mantener</button><div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-56 p-2 bg-gray-800 dark:bg-gray-700 text-white text-xs rounded shadow-xl z-50 text-center whitespace-normal font-normal">Tienes la cantidad ideal. No es necesario comprar más.<div class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800 dark:border-t-gray-700"></div></div></div>`;
                }

                let registrarBtn = `<button onclick="event.stopPropagation(); openSolicitudManualModal(${prod.idProducto})" class="w-full text-[11px] font-bold text-gray-700 bg-gray-100 hover:bg-blue-50 hover:text-blue-700 dark:bg-slate-800 dark:text-gray-300 dark:hover:bg-slate-700 dark:hover:text-blue-300 py-1 px-2 rounded transition-colors flex items-center justify-center gap-1 border border-gray-200 dark:border-gray-700 shadow-sm mt-1" title="Registrar solicitud manual para este producto">
                    <i class="fa-solid fa-plus text-[10px]"></i> Registrar solicitud
                </button>`;

                // Construir especificaciones sutiles (Talla, Color, Marca) para evitar sobrecarga visual
                let specs = [];
                if (prod.marca) specs.push(`<span class="text-[10px] text-gray-500 bg-gray-50 dark:bg-gray-900 px-1.5 py-0.5 rounded border border-gray-200/60 dark:border-gray-700/60 font-semibold">🏷️ ${prod.marca}</span>`);
                if (prod.talla) specs.push(`<span class="text-[10px] text-gray-500 bg-gray-50 dark:bg-gray-900 px-1.5 py-0.5 rounded border border-gray-200/60 dark:border-gray-700/60 font-semibold">📏 Talla: ${prod.talla}</span>`);
                if (prod.color) specs.push(`<span class="text-[10px] text-gray-500 bg-gray-50 dark:bg-gray-900 px-1.5 py-0.5 rounded border border-gray-200/60 dark:border-gray-700/60 font-semibold">🎨 ${prod.color}</span>`);
                let specsHtml = specs.length > 0 ? `<div class="flex gap-1 flex-wrap mt-1">${specs.join('')}</div>` : '';

                tr.innerHTML = `
                    <td class="py-4 px-4 font-mono font-bold text-xs">
                        <span class="px-2 py-1 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded border border-gray-200 dark:border-gray-700 select-all inline-block">
                            <i class="fa-solid fa-barcode mr-1 text-gray-400"></i>${prod.codigoBarras || '-'}
                        </span>
                    </td>
                    <td class="py-4 px-4">
                        <div class="flex flex-col gap-1">
                            <span class="text-base font-bold text-gray-900 dark:text-white leading-tight">${prod.nombre}</span>
                            <div class="flex items-center gap-1.5 text-xs flex-wrap font-medium">
                                <span class="text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-slate-800 px-2 py-0.5 rounded border border-gray-200 dark:border-slate-700">${prod.categoria}</span>
                                <span class="px-2 py-0.5 rounded bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300 border border-purple-100 dark:border-purple-900/50 font-bold">${prod.contexto_producto}</span>
                            </div>
                            ${specsHtml}
                            <span class="text-xs text-gray-500 dark:text-gray-400 mt-1 font-medium flex items-center gap-1.5" title="Este artículo ayuda a vender otros artículos de la tienda">
                                <i class="fa-solid fa-diagram-project text-purple-500 dark:text-purple-400"></i>
                                <span>${prod.reglas_vinculadas_texto}</span>
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
                        <div class="flex flex-col gap-1 items-center max-w-[140px] mx-auto">
                            ${accionBtn}
                            ${registrarBtn}
                        </div>
                    </td>
                    <td class="py-4 px-4 whitespace-nowrap text-center">
                        <button onclick="event.stopPropagation(); openEditProductModal(${prod.idProducto})" class="px-2.5 py-1 text-xs font-semibold rounded text-blue-600 bg-blue-50 dark:bg-blue-900/30 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors inline-flex items-center gap-1" title="Editar producto">
                            <i class="fa-solid fa-pen-to-square"></i> Editar
                        </button>
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

        // 3. Renderizar Acciones Prioritarias (Grid en Tab Decisiones)
        const accionesContainerGrid = document.getElementById('acciones-container-grid');
        if (accionesContainerGrid) {
            if (accionesRecomendadas.length > 0) {
                accionesContainerGrid.innerHTML = accionesRecomendadas.map(a => `
                    <div class="card p-5 border-l-4 ${a.borderColor} flex flex-col justify-between h-full hover:shadow-md transition-shadow">
                        <div class="flex items-start gap-3 mb-4">
                            <div class="w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${a.iconBg} ${a.iconColor} text-lg">
                                <i class="fa-solid ${a.icon}"></i>
                            </div>
                            <div>
                                <h4 class="font-bold text-gray-800 dark:text-white text-sm">${a.title}</h4>
                                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1 leading-snug">${a.desc}</p>
                            </div>
                        </div>
                        <div class="flex gap-2 mt-auto">
                            <button onclick="goToProduct(${a.id})" class="flex-1 py-1.5 rounded bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-xs font-semibold text-gray-700 dark:text-gray-300 transition-colors">Ver</button>
                            ${a.rawAccion === 'EnProceso' ? 
                                `<button onclick="window.location.href='/compras?tab=planificacion${a.idSolicitud ? '&hl_req=' + a.idSolicitud : ''}'" class="flex-[2] py-1.5 rounded ${a.btnBg} hover:opacity-90 text-xs font-semibold text-white transition-opacity shadow-sm flex items-center justify-center gap-1.5"><i class="fa-solid fa-arrow-right-to-bracket"></i> ${a.btnText}</button>` :
                                `<button onclick="openActionModal(${a.id}, '${a.rawAccion}')" class="flex-[2] py-1.5 rounded ${a.btnBg} hover:opacity-90 text-xs font-semibold text-white transition-opacity shadow-sm">${a.btnText || 'Resolver'}</button>`
                            }
                        </div>
                    </div>
                `).join('');
            } else {
                accionesContainerGrid.innerHTML = `
                    <div class="card p-6 text-center text-gray-500 text-xs w-full col-span-full border border-dashed border-gray-200 dark:border-gray-700">
                        <i class="fa-solid fa-circle-check text-4xl mb-3 text-green-500 opacity-80"></i>
                        <p class="font-medium text-gray-700 dark:text-gray-300 text-lg">Todo está bajo control.</p>
                        <p class="mt-1 text-sm">No hay acciones urgentes pendientes.</p>
                    </div>
                `;
            }
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

let currentActionContext = null;

function openActionModal(id, accion) {
    const prod = window.inventoryDataMap[id];
    if (!prod) return;
    
    currentActionContext = { id, accion, prod };
    
    const modal = document.getElementById('action-modal');
    const title = document.getElementById('action-modal-title');
    const subtitle = document.getElementById('action-modal-subtitle');
    const body = document.getElementById('action-modal-body');
    const icon = document.getElementById('action-modal-icon');
    const iconBg = document.getElementById('action-modal-icon-bg');
    const btn = document.getElementById('action-modal-btn');
    
    title.textContent = accion === 'Reponer' ? 'Orden de Compra' : (accion === 'Liquidar' ? 'Crear Promoción' : 'Mantener Inventario');
    subtitle.textContent = prod.nombre;
    
    if (accion === 'Reponer') {
        icon.className = "fa-solid fa-truck-ramp-box text-lg text-red-600";
        iconBg.className = "w-10 h-10 rounded-full flex items-center justify-center bg-red-100 dark:bg-red-900/50";
        btn.className = "px-4 py-2 rounded text-sm font-bold text-white shadow-sm transition-colors bg-red-600 hover:bg-red-700";
        btn.textContent = "Generar Orden (Stub)";
        
        body.innerHTML = `
            <div class="space-y-3 text-sm">
                <div class="flex justify-between border-b pb-2 border-gray-200 dark:border-gray-700">
                    <span class="text-gray-500">Stock Actual</span>
                    <span class="font-bold">${prod.stock} uds</span>
                </div>
                <div class="flex justify-between border-b pb-2 border-gray-200 dark:border-gray-700">
                    <span class="text-gray-500">Días para Quiebre</span>
                    <span class="font-bold text-red-500">${prod.dias_quiebre || 0} días</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-500">Sugerencia de Compra</span>
                    <span class="font-bold text-blue-600">+${Math.max(10, Math.round(prod.stock * 1.5))} uds</span>
                </div>
            </div>
        `;
    } else if (accion === 'Liquidar') {
        icon.className = "fa-solid fa-tag text-lg text-orange-600";
        iconBg.className = "w-10 h-10 rounded-full flex items-center justify-center bg-orange-100 dark:bg-orange-900/50";
        btn.className = "px-4 py-2 rounded text-sm font-bold text-white shadow-sm transition-colors bg-orange-500 hover:bg-orange-600";
        btn.textContent = "Aplicar Descuento (Stub)";
        
        body.innerHTML = `
            <div class="space-y-3 text-sm">
                <div class="flex justify-between border-b pb-2 border-gray-200 dark:border-gray-700">
                    <span class="text-gray-500">Stock Inmovilizado</span>
                    <span class="font-bold">${prod.stock} uds</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-500">Margen Actual</span>
                    <span class="font-bold text-green-600">${prod.margen}%</span>
                </div>
            </div>
        `;
    } else {
        icon.className = "fa-solid fa-circle-check text-lg text-green-600";
        iconBg.className = "w-10 h-10 rounded-full flex items-center justify-center bg-green-100 dark:bg-green-900/50";
        btn.className = "px-4 py-2 rounded text-sm font-bold text-white shadow-sm transition-colors bg-green-600 hover:bg-green-700";
        btn.textContent = "Aceptar";
        
        body.innerHTML = `
            <div class="space-y-3 text-sm text-center">
                <p class="text-gray-600 dark:text-gray-300">El inventario de este producto está en estado óptimo.</p>
            </div>
        `;
    }
    
    modal.classList.remove('hidden');
    // slight delay for transition
    setTimeout(() => modal.classList.remove('opacity-0'), 10);
}

function closeActionModal() {
    const modal = document.getElementById('action-modal');
    modal.classList.add('opacity-0');
    setTimeout(() => modal.classList.add('hidden'), 300);
}

async function executeStubAction() {
    if (!currentActionContext) return;
    
    if (currentActionContext.accion === 'Reponer') {
        const btn = document.getElementById('action-modal-btn');
        btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Procesando...`;
        btn.disabled = true;
        
        try {
            const sugCompra = Math.max(10, Math.round(currentActionContext.prod.stock * 1.5));
            const payload = {
                idProducto: currentActionContext.prod.idProducto,
                cantidad_sugerida: sugCompra,
                motivo: "Reposición manual desde Inventario"
            };
            
            const res = await ApiClient.post('/compras/solicitud', payload);
            showToast(`Solicitud enviada, redirigiendo a Compras...`, 'success');
            
            setTimeout(() => {
                window.location.href = `/compras?tab=planificacion&hl_req=${res.idSolicitud}`;
            }, 800);
            
        } catch (e) {
            showToast("Error creando solicitud: " + e.message, 'error');
        } finally {
            closeActionModal();
            closeOffCanvas();
        }
        return;
    }
    
    showToast(`Próximamente: Integración de ${currentActionContext.accion} para ${currentActionContext.prod.nombre}`, 'info');
    closeActionModal();
    closeOffCanvas();
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

function openOffCanvas(id) {
    const prod = window.inventoryDataMap[id];
    if (!prod) return;
    
    const panel = document.getElementById('offcanvas-panel');
    const title = document.getElementById('offcanvas-title');
    const content = document.getElementById('offcanvas-content');
    
    title.textContent = prod.nombre;
    
    content.innerHTML = `
        <div class="space-y-6">
            <div class="bg-gray-50 dark:bg-gray-800/50 p-4 rounded-lg">
                <h4 class="text-xs font-bold text-gray-500 uppercase mb-3">Resumen de Negocio</h4>
                <div class="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <span class="block text-gray-500 text-xs">Stock Físico</span>
                        <span class="font-bold text-lg">${prod.stock}</span>
                    </div>
                    <div>
                        <span class="block text-gray-500 text-xs">Margen</span>
                        <span class="font-bold text-lg text-green-600">${prod.margen}%</span>
                    </div>
                    <div>
                        <span class="block text-gray-500 text-xs">Días Restantes</span>
                        <span class="font-bold text-lg ${prod.dias_quiebre < 7 ? 'text-red-500' : ''}">${prod.dias_quiebre || '-'}</span>
                    </div>
                    <div>
                        <span class="block text-gray-500 text-xs">Rotación ABC</span>
                        <span class="font-bold text-lg">${prod.abc}</span>
                    </div>
                </div>
            </div>
            
            <div>
                <h4 class="text-xs font-bold text-gray-500 uppercase mb-3">Diagnóstico Operacional</h4>
                <div class="space-y-3">
                    <div class="p-3 border border-gray-100 dark:border-gray-700 rounded flex gap-3 items-center">
                        <i class="fa-solid fa-heart-pulse text-gray-400"></i>
                        <div>
                            <span class="block font-medium text-sm">Estado Físico</span>
                            <span class="text-xs text-gray-500">${prod.estado_fisico}</span>
                        </div>
                    </div>
                    <div class="p-3 border border-gray-100 dark:border-gray-700 rounded flex gap-3 items-center">
                        <i class="fa-solid fa-chart-line text-gray-400"></i>
                        <div>
                            <span class="block font-medium text-sm">Riesgo Futuro</span>
                            <span class="text-xs text-gray-500">${prod.riesgo}</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="pt-4 border-t border-gray-100 dark:border-gray-700">
                ${prod.accion === 'Reponer' && prod.tiene_solicitud_pendiente ? `
                    <button disabled class="w-full bg-gray-100 dark:bg-slate-800 text-gray-400 dark:text-gray-500 py-2.5 text-sm shadow cursor-not-allowed font-bold rounded flex items-center justify-center gap-1.5 border border-gray-200 dark:border-slate-700">
                        ⏳ Reposición en Proceso
                    </button>
                ` : `
                    <button onclick="openActionModal(${prod.idProducto}, '${prod.accion}')" class="w-full btn-primary py-2 text-sm shadow">
                        Ejecutar ${prod.accion}
                    </button>
                `}
            </div>
        </div>
    `;
    
    panel.classList.remove('translate-x-full');
    
    // Fetch and render historial
    cargarHistorialAbastecimiento(prod.idProducto);
}

async function cargarHistorialAbastecimiento(idProducto) {
    const containerId = 'historial-abastecimiento-container';
    const content = document.getElementById('offcanvas-content');
    
    // Create container if it doesn't exist
    let histContainer = document.getElementById(containerId);
    if (!histContainer) {
        histContainer = document.createElement('div');
        histContainer.id = containerId;
        histContainer.className = "mt-6";
        
        // Insert before the action button
        const actionBtnDiv = content.querySelector('.pt-4.border-t');
        if (actionBtnDiv) {
            content.querySelector('.space-y-6').insertBefore(histContainer, actionBtnDiv);
        } else {
            content.querySelector('.space-y-6').appendChild(histContainer);
        }
    }
    
    histContainer.innerHTML = `<h4 class="text-xs font-bold text-gray-500 uppercase mb-3"><i class="fa-solid fa-truck-fast"></i> Historial de Abastecimiento</h4><div class="text-center text-xs text-gray-400 py-2">Consultando historial...</div>`;
    
    try {
        const res = await ApiClient.get(`/compras/historial/${idProducto}`);
        const historial = res.historial || [];
        
        if (historial.length === 0) {
            histContainer.innerHTML = `<h4 class="text-xs font-bold text-gray-500 uppercase mb-3"><i class="fa-solid fa-truck-fast"></i> Historial de Abastecimiento</h4><div class="p-3 border border-gray-100 dark:border-gray-700 rounded text-center text-xs text-gray-500">No hay registros de compras para este producto.</div>`;
            return;
        }
        
        const historyHTML = historial.map(h => {
            const fechaFormateada = new Date(h.fecha).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' });
            let estadoClass = h.estado === 'Completada' ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300' : 'bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300';
            
            return `
            <div class="p-3 border-b border-gray-100 dark:border-gray-700 last:border-0 flex justify-between items-center bg-white dark:bg-gray-800 rounded mb-2 shadow-sm">
                <div>
                    <div class="text-xs font-bold text-gray-800 dark:text-gray-200">${h.proveedor}</div>
                    <div class="text-[10px] text-gray-500">${fechaFormateada} • ${h.cantidad} uds</div>
                </div>
                <div class="text-[10px] font-bold px-2 py-0.5 rounded ${estadoClass}">${h.estado}</div>
            </div>`;
        }).join('');
        
        histContainer.innerHTML = `<h4 class="text-xs font-bold text-gray-500 uppercase mb-3"><i class="fa-solid fa-truck-fast"></i> Historial de Abastecimiento</h4><div>${historyHTML}</div>`;
        
    } catch (e) {
        console.error("Error cargando historial", e);
        histContainer.innerHTML = `<h4 class="text-xs font-bold text-gray-500 uppercase mb-3"><i class="fa-solid fa-truck-fast"></i> Historial de Abastecimiento</h4><div class="text-center text-xs text-red-500 py-2">Error cargando historial</div>`;
    }
}

function closeOffCanvas() {
    const panel = document.getElementById('offcanvas-panel');
    panel.classList.add('translate-x-full');
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

// CONTROLADOR DE ESTADO VISUAL (PESTAÑAS)
function switchTab(tabId) {
    const tabProductos = document.getElementById('tab-productos');
    const tabDecisiones = document.getElementById('tab-decisiones');
    const btnProductos = document.getElementById('btn-tab-productos');
    const btnDecisiones = document.getElementById('btn-tab-decisiones');
    
    if (!tabProductos || !tabDecisiones) return;
    
    if (tabId === 'productos') {
        tabProductos.classList.remove('hidden');
        tabDecisiones.classList.add('hidden');
        
        btnProductos.className = "px-6 py-3 font-semibold text-amber-500 border-b-2 border-amber-500 transition-colors flex items-center gap-2";
        btnDecisiones.className = "px-6 py-3 font-semibold text-gray-400 hover:text-gray-700 dark:hover:text-white border-b-2 border-transparent transition-colors flex items-center gap-2";
    } else {
        tabProductos.classList.add('hidden');
        tabDecisiones.classList.remove('hidden');
        
        btnDecisiones.className = "px-6 py-3 font-semibold text-amber-500 border-b-2 border-amber-500 transition-colors flex items-center gap-2";
        btnProductos.className = "px-6 py-3 font-semibold text-gray-400 hover:text-gray-700 dark:hover:text-white border-b-2 border-transparent transition-colors flex items-center gap-2";
    }
}

function goToProduct(id) {
    switchTab('productos');
    setTimeout(() => {
        scrollToProduct(id);
    }, 50);
}

// FUNCIONES DE FILTROS Y NUEVO PRODUCTO EN BD

function clearFilters() {
    elSearchInput.value = '';
    elFilterCategoria.value = '';
    elFilterEstado.value = '';
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
        showToast(`✅ ${res.message || 'Producto registrado correctamente.'}`, 'success');
        closeNewProductModal();
        fetchAndRenderData();
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
        showToast(`✅ ${res.message || 'Producto actualizado en la BD.'}`, 'success');
        closeEditProductModal();
        fetchAndRenderData();
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
    document.getElementById('sol-prod-nombre-display').textContent = `${prod.nombre} (${prod.codigoBarras !== '-' ? prod.codigoBarras : 'Sin SKU'})`;

    // Cantidad sugerida por defecto
    const sugVal = prod.accion === 'Reponer' ? Math.max(1, Math.round(prod.stock * 1.5) || 1) : 1;
    document.getElementById('sol-cantidad').value = sugVal;

    const selectMotivo = document.getElementById('sol-motivo');
    if (selectMotivo) selectMotivo.value = "Reposición manual";

    const wrapperOtro = document.getElementById('wrapper-motivo-otro');
    if (wrapperOtro) wrapperOtro.classList.add('hidden');

    const inputOtro = document.getElementById('sol-motivo-otro');
    if (inputOtro) inputOtro.value = "";

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

    let motivoFinal = selectMotivo;
    if (selectMotivo === '__OTRO__') {
        const inputOtro = document.getElementById('sol-motivo-otro');
        motivoFinal = inputOtro ? inputOtro.value.trim() : '';
        if (!motivoFinal) {
            showToast('Por favor especifica el motivo de la solicitud', 'info');
            return;
        }
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
        showToast(`✅ Solicitud de compra creada (Origen: Manual)`, 'success');
        closeSolicitudManualModal();
        fetchAndRenderData();
    } catch (err) {
        console.error("Error registrando solicitud manual", err);
        showToast(`❌ ${err.message || 'No se pudo guardar la solicitud'}`, 'info');
    }
}
