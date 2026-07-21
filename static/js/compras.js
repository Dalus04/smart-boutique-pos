/**
 * Motor Reactivo - Compras y Abastecimiento (Refactor Arquitectónico v4.5)
 */

let orderItems = [];
let proveedores = [];
let solicitudesOriginales = [];
let borradorIdCompra = null;
let saveTimeout = null;

// DOM Elements
const selProveedor = document.getElementById('select-proveedor');
const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('search-results');
const cartItems = document.getElementById('cart-items');
const cartEmpty = document.getElementById('cart-empty');
const sumItems = document.getElementById('summary-items');
const sumTotal = document.getElementById('summary-total');
const btnProcesar = document.getElementById('btn-procesar');
const toast = document.getElementById('toast');
const toastMsg = document.getElementById('toast-msg');

const fmt = (val) => `S/ ${Number(val).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits:2})}`;

const parseLocalDate = (isoString) => {
    if (!isoString) return new Date();
    let s = isoString;
    if (!s.includes('Z') && !/[+-]\d{2}:\d{2}$/.test(s)) {
        s = s + 'Z';
    }
    return new Date(s);
};

function debounce(func, delay = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => { func.apply(this, args); }, delay);
    };
}

function showToast(msg, isError = false) {
    toastMsg.textContent = msg;
    toast.className = `fixed bottom-4 right-4 text-white px-6 py-3 rounded-lg shadow-lg font-bold transform transition-all duration-300 z-50 flex items-center gap-3 ${isError ? 'bg-red-500' : 'bg-green-500'}`;
    toast.classList.remove('translate-y-20', 'opacity-0');
    
    setTimeout(() => {
        toast.classList.add('translate-y-20', 'opacity-0');
    }, 3000);
}

// -------------------------------------------------------------
// CONTROL DE PESTAÑAS Y DEEP LINKING
// -------------------------------------------------------------
function switchTab(tabId) {
    ['planificacion', 'ordenes', 'historial'].forEach(t => {
        const el = document.getElementById(`tab-${t}`);
        if(el) {
            el.classList.add('hidden');
            if(t === 'planificacion') el.classList.remove('lg:grid');
        }
        
        const btn = document.getElementById(`btn-tab-${t}`);
        if(btn) {
            btn.classList.remove('border-blue-600', 'text-blue-600', 'dark:border-blue-400', 'dark:text-blue-400');
            btn.classList.add('border-transparent', 'text-gray-500', 'dark:text-gray-400');
        }
    });
    
    const targetEl = document.getElementById(`tab-${tabId}`);
    if(targetEl) {
        targetEl.classList.remove('hidden');
        if(tabId === 'planificacion') targetEl.classList.add('lg:grid');
    }
    
    const targetBtn = document.getElementById(`btn-tab-${tabId}`);
    if(targetBtn) {
        targetBtn.classList.remove('border-transparent', 'text-gray-500', 'dark:text-gray-400');
        targetBtn.classList.add('border-blue-600', 'text-blue-600', 'dark:border-blue-400', 'dark:text-blue-400');
    }

    if(tabId === 'historial') cargarHistorialGlobal();
    if(tabId === 'ordenes') cargarOrdenesActivas();
}

function parseURLParams() {
    const params = new URLSearchParams(window.location.search);
    const tab = params.get('tab');
    const hlReq = params.get('hl_req');

    if (tab === 'solicitudes' || tab === 'planificacion') switchTab('planificacion');
    else if (tab && ['ordenes', 'historial'].includes(tab)) switchTab(tab);
    else switchTab('planificacion');

    if (hlReq) {
        setTimeout(() => {
            const row = document.getElementById(`sol-row-${hlReq}`);
            if (row) {
                row.scrollIntoView({ behavior: 'smooth', block: 'center' });
                row.classList.add('bg-amber-100', 'dark:bg-amber-900/40', 'transition-colors', 'duration-1000');
                setTimeout(() => {
                    row.classList.remove('bg-amber-100', 'dark:bg-amber-900/40');
                }, 3000);
            }
        }, 800);
    }
}

// -------------------------------------------------------------
// INICIALIZACIÓN
// -------------------------------------------------------------
async function init() {
    parseURLParams();

    try {
        proveedores = await ApiClient.get('/actores/proveedores');
        if(selProveedor) {
            selProveedor.innerHTML = '<option value="">Seleccione un proveedor...</option>';
            proveedores.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.idProveedor;
                opt.textContent = `${p.numeroDocumento} - ${p.nombreRazonSocial}`;
                selProveedor.appendChild(opt);
            });
        }
        
        // Load Draft Manifest
        const borradorRes = await ApiClient.get('/compras/planificacion/borrador');
        if (borradorRes.borrador) {
            borradorIdCompra = borradorRes.borrador.idCompra;
            if (borradorRes.borrador.idProveedor && borradorRes.borrador.idProveedor > 0) {
                selProveedor.value = borradorRes.borrador.idProveedor;
            }
            orderItems = borradorRes.borrador.items || [];
        }
        
        // DEEP LINKING: Auto-seleccionar proveedor
        const params = new URLSearchParams(window.location.search);
        const supplierId = params.get('select_supplier_id');
        if (supplierId && selProveedor) {
            selProveedor.value = supplierId;
            saveManifesto({ idProveedor: parseInt(supplierId) });
        }
        
        await cargarSolicitudesPendientes();
        updateOrderUI();
        
    } catch (e) {
        console.error("Error inicializando compras", e);
    }
}

// -------------------------------------------------------------
// BUSCADOR EN COLUMNA 1 (Catálogo)
// -------------------------------------------------------------
const performSearch = async () => {
    if(!searchInput || !searchResults) return;
    
    const q = searchInput.value.trim();
    if (!q) {
        searchResults.classList.add('hidden');
        return;
    }
    
    try {
        const resultados = await ApiClient.get('/pos/productos', { q });
        renderSearchResults(resultados);
    } catch (e) {
        console.error(e);
    }
};

function renderSearchResults(productos) {
    searchResults.innerHTML = '';
    
    if (productos.length === 0) {
        searchResults.innerHTML = '<div class="p-4 text-gray-500 text-sm text-center">No se encontraron productos.</div>';
    } else {
        productos.forEach(prod => {
            const item = document.createElement('div');
            item.className = "p-3 mb-2 rounded-lg border border-gray-100 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-blue-300 cursor-pointer flex justify-between items-center transition-all shadow-sm";
            item.innerHTML = `
                <div class="truncate pr-3">
                    <div class="text-[10px] text-gray-400 font-mono tracking-wider">${prod.codigoBarras || '-'}</div>
                    <div class="font-bold text-sm text-gray-800 dark:text-gray-200 truncate">${prod.nombre}</div>
                </div>
                <div class="text-right shrink-0">
                    <div class="text-xs font-bold ${prod.stock <= 5 ? 'text-red-500' : 'text-gray-600 dark:text-gray-400'}">Stock: ${prod.stock}</div>
                </div>
            `;
            item.onclick = () => {
                addToOrder({
                    idProducto: prod.idProducto,
                    codigoBarras: prod.codigoBarras,
                    nombre: prod.nombre,
                    stock: prod.stock,
                    costoUnitario: prod.costo || "",
                    precioLista: prod.precioLista || 0
                }, 1);
                searchInput.value = '';
                searchResults.classList.add('hidden');
                showToast("Producto agregado al borrador");
            };
            searchResults.appendChild(item);
        });
    }
    
    searchResults.classList.remove('hidden');
}

if(searchInput) {
    searchInput.addEventListener('input', debounce(performSearch, 300));
}

let sugerenciasAnaliticasIA = [];

// -------------------------------------------------------------
// SOLICITUDES SEPARADAS (MANUALES VS IA)
// -------------------------------------------------------------
async function cargarSolicitudesPendientes() {
    try {
        const [resSol, resSug] = await Promise.allSettled([
            ApiClient.get('/compras/solicitudes/pendientes'),
            ApiClient.get('/compras/sugerencias')
        ]);

        if (resSol.status === 'fulfilled') {
            solicitudesOriginales = resSol.value.solicitudes || [];
        }

        if (resSug.status === 'fulfilled') {
            const dataSug = resSug.value;
            sugerenciasAnaliticasIA = dataSug.sugerencias || [];
            
            // Sugerir proveedor principal si no hay uno seleccionado
            if (dataSug.proveedorSugerido && selProveedor && (!selProveedor.value || selProveedor.value === "")) {
                selProveedor.value = dataSug.proveedorSugerido;
            }
        }

        renderSolicitudes();
    } catch (e) {
        console.error("Error cargando solicitudes y sugerencias IA", e);
    }
}

function renderSolicitudesCard(s) {
    const itemEnOrden = orderItems.find(i => i.idProducto === s.idProducto);
    const isManual = (s.origen || '').toLowerCase() === 'manual';
    
    let actionBtn = "";
    if (itemEnOrden) {
        actionBtn = `<button class="w-full py-2 mt-2 bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400 font-bold text-xs rounded-lg flex items-center justify-center gap-2 cursor-not-allowed border border-green-200 dark:border-green-800" disabled><i class="fa-solid fa-circle-check"></i> En Borrador</button>`;
    } else {
        const bgBtnClass = isManual 
            ? "bg-blue-50 hover:bg-blue-600 text-blue-700 hover:text-white dark:bg-blue-900/30 dark:hover:bg-blue-600 dark:text-blue-300 border-blue-200 dark:border-blue-800"
            : "bg-indigo-50 hover:bg-indigo-600 text-indigo-700 hover:text-white dark:bg-indigo-900/30 dark:hover:bg-indigo-600 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800";
        actionBtn = `<button onclick='addToOrder({idProducto: ${s.idProducto}, nombre: "${s.productoNombre}", codigoBarras: "${s.codigoBarras}", stock: 0}, ${s.cantidadSugerida});' class="w-full py-2 mt-2 ${bgBtnClass} border transition-colors font-bold text-xs rounded-lg flex items-center justify-center gap-2 shadow-sm"><i class="fa-solid fa-plus"></i> Añadir ${s.cantidadSugerida} u. al Manifiesto</button>`;
    }

    return `
    <div id="sol-row-${s.idSolicitud}" class="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 hover:shadow-md transition-all">
        <div class="font-bold text-gray-900 dark:text-gray-100 text-sm leading-tight">${s.productoNombre}</div>
        <div class="text-[10px] text-gray-400 font-mono mb-2">${s.codigoBarras}</div>
        <div class="text-xs text-gray-600 dark:text-gray-400 italic mb-2">"${s.motivo}"</div>
        ${actionBtn}
    </div>
    `;
}

function renderSugerenciaIACard(s) {
    const itemEnOrden = orderItems.find(i => i.idProducto === s.idProducto);
    let actionBtn = "";
    
    if (itemEnOrden) {
        actionBtn = `<button class="w-full py-2 mt-2 bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400 font-bold text-xs rounded-lg flex items-center justify-center gap-2 cursor-not-allowed border border-green-200 dark:border-green-800" disabled><i class="fa-solid fa-circle-check"></i> En Borrador</button>`;
    } else {
        actionBtn = `<button onclick='addToOrder({idProducto: ${s.idProducto}, nombre: "${s.nombre}", codigoBarras: "${s.codigoBarras}", stock: ${s.stockActual}, costoUnitario: ${s.costo}, precioLista: ${s.precioLista}}, ${s.sugerencia});' class="w-full py-2 mt-2 bg-indigo-50 hover:bg-indigo-600 text-indigo-700 hover:text-white dark:bg-indigo-900/30 dark:hover:bg-indigo-600 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 transition-colors font-bold text-xs rounded-lg flex items-center justify-center gap-2 shadow-sm"><i class="fa-solid fa-robot"></i> Añadir ${s.sugerencia} u. (IA)</button>`;
    }

    return `
    <div class="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border border-indigo-100 dark:border-indigo-900/50 hover:shadow-md transition-all">
        <div class="flex justify-between items-start mb-1">
            <div class="font-bold text-gray-900 dark:text-gray-100 text-sm leading-tight">${s.nombre}</div>
            <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300">${s.velocidadDiaria} u/día</span>
        </div>
        <div class="text-[10px] text-gray-400 font-mono mb-2">${s.codigoBarras} • Stock actual: ${s.stockActual}</div>
        <div class="text-xs text-indigo-600 dark:text-indigo-400 italic mb-2">"${s.contexto}"</div>
        ${actionBtn}
    </div>
    `;
}

function renderSolicitudes() {
    const containerManual = document.getElementById('solicitudes-manuales-chips');
    const containerIa = document.getElementById('sugerencias-ia-chips');
    if (!containerManual || !containerIa) return;

    const manuales = solicitudesOriginales.filter(s => (s.origen || '').toLowerCase() === 'manual');
    const iasPendientes = solicitudesOriginales.filter(s => (s.origen || '').toLowerCase() !== 'manual');

    if (manuales.length === 0) {
        containerManual.innerHTML = `
            <div class="p-4 text-center text-gray-400 text-xs italic">
                No hay solicitudes manuales registradas.
            </div>`;
    } else {
        containerManual.innerHTML = manuales.map(renderSolicitudesCard).join('');
    }

    if (sugerenciasAnaliticasIA.length > 0) {
        containerIa.innerHTML = sugerenciasAnaliticasIA.map(renderSugerenciaIACard).join('');
    } else if (iasPendientes.length > 0) {
        containerIa.innerHTML = iasPendientes.map(renderSolicitudesCard).join('');
    } else {
        containerIa.innerHTML = `
            <div class="p-4 text-center text-gray-400 text-xs italic">
                El inventario está estable. No hay sugerencias de la IA.
            </div>`;
    }
}

// -------------------------------------------------------------
// BORRADOR / MANIFIESTO ACTIVO
// -------------------------------------------------------------
function syncBorrador() {
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(async () => {
        const idProv = parseInt(selProveedor.value) || 0;
        const mTotal = orderItems.reduce((acc, i) => acc + (i.cantidad * parseFloat(i.costoUnitario || 0)), 0);
        
        const payload = {
            idProveedor: idProv,
            montoTotal: mTotal,
            items: orderItems.map(i => ({
                idProducto: i.idProducto,
                cantidad: i.cantidad,
                costoUnitario: parseFloat(i.costoUnitario || 0)
            }))
        };
        
        try {
            const res = await ApiClient.put('/compras/planificacion/borrador', payload);
            borradorIdCompra = res.idCompra;
        } catch(e) {
            console.error("Error sincronizando borrador", e);
        }
    }, 500);
}

function addToOrder(prod, cantidad = 1) {
    const existing = orderItems.find(i => i.idProducto === prod.idProducto);
    if (existing) {
        if (!confirm(`Este producto (${prod.nombre}) ya está en el borrador. ¿Deseas actualizar la cantidad?`)) {
            return;
        }
        existing.cantidad += cantidad;
    } else {
        orderItems.push({
            idProducto: prod.idProducto,
            codigoBarras: prod.codigoBarras,
            nombre: prod.nombre,
            stockActual: prod.stock || 0,
            costoUnitario: prod.costoUnitario || "",
            precioLista: prod.precioLista || 0.0,
            cantidad: cantidad
        });
    }
    updateOrderUI();
    syncBorrador();
    
    if (!existing) {
        setTimeout(() => {
            const input = document.getElementById(`costo-input-${prod.idProducto}`);
            if(input) input.focus();
        }, 50);
    }
}

function removeOrder(idProducto) {
    orderItems = orderItems.filter(i => i.idProducto !== idProducto);
    updateOrderUI();
    syncBorrador();
}

function updateItem(idProducto, field, value) {
    const item = orderItems.find(i => i.idProducto === idProducto);
    if(item) {
        if (field === 'costoUnitario' && value.trim() === "") {
            item[field] = "";
            updateOrderUI();
            syncBorrador();
            return;
        }
        const val = parseFloat(value);
        if(!isNaN(val) && val >= 0) {
            item[field] = val;
            updateOrderUI();
            syncBorrador();
        }
    }
}

function updateOrderUI() {
    if(!cartItems || !cartEmpty) return;
    cartItems.innerHTML = '';
    
    let subtotal = 0;
    let totalItems = 0;
    
    if (orderItems.length === 0) {
        cartEmpty.classList.remove('hidden');
        if(btnProcesar) btnProcesar.disabled = true;
    } else {
        cartEmpty.classList.add('hidden');
        // Permite procesar desde 1 artículo en adelante
        if(btnProcesar) btnProcesar.disabled = false;
        
        orderItems.forEach(item => {
            const itemSubtotal = item.cantidad * parseFloat(item.costoUnitario || 0);
            subtotal += itemSubtotal;
            totalItems += item.cantidad;
            
            const isMargenDestruido = item.precioLista > 0 && parseFloat(item.costoUnitario || 0) >= item.precioLista;
            const bgClass = isMargenDestruido ? "bg-red-50/50 dark:bg-red-900/10" : "hover:bg-gray-50 dark:hover:bg-gray-800/30";
            const alertIcon = isMargenDestruido ? `<i class="fa-solid fa-triangle-exclamation text-red-500" title="Costo supera o iguala precio de venta"></i>` : '';
            
            const costoValStr = item.costoUnitario === "" ? "" : Number(item.costoUnitario).toFixed(2);
            
            const tr = document.createElement('tr');
            tr.className = `${bgClass} transition-colors border-b border-gray-100 dark:border-gray-700/50`;
            tr.innerHTML = `
                <td class="py-3 px-4">
                    <div class="font-bold text-gray-800 dark:text-gray-200 flex items-center gap-2 leading-tight">
                        ${item.nombre} ${alertIcon}
                    </div>
                </td>
                <td class="py-3 px-2 text-center w-20">
                    <input type="number" step="1" min="1" class="w-full px-1 py-1.5 border border-gray-300 bg-white dark:border-gray-600 dark:bg-gray-900 rounded focus:border-blue-500 text-center text-sm font-bold" value="${item.cantidad}" onchange="updateItem(${item.idProducto}, 'cantidad', this.value)">
                </td>
                <td class="py-3 px-2 text-center w-28">
                    <div class="relative group">
                        <span class="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400 text-xs">$</span>
                        <input id="costo-input-${item.idProducto}" type="number" step="0.01" min="0" class="w-full pl-5 pr-1 py-1.5 border ${isMargenDestruido ? 'border-red-300 bg-red-50 text-red-700 dark:border-red-700 dark:bg-red-900/30' : 'border-gray-300 bg-white dark:border-gray-600 dark:bg-gray-900'} rounded focus:border-blue-500 text-right text-sm transition-colors" value="${costoValStr}" onchange="updateItem(${item.idProducto}, 'costoUnitario', this.value)">
                    </div>
                </td>
                <td class="py-3 px-4 text-right font-mono font-bold text-gray-800 dark:text-gray-200 w-24">
                    ${item.costoUnitario === "" ? "-" : fmt(itemSubtotal)}
                </td>
                <td class="py-3 px-2 text-center w-10">
                    <button onclick="removeOrder(${item.idProducto})" class="text-gray-400 hover:text-red-500 transition-colors p-1"><i class="fa-solid fa-trash-can"></i></button>
                </td>
            `;
            cartItems.appendChild(tr);
        });
    }
    
    if(sumItems) sumItems.textContent = totalItems;
    if(sumTotal) sumTotal.textContent = fmt(subtotal); 
    
    renderSolicitudes();
}

if(btnProcesar) {
    btnProcesar.addEventListener('click', async () => {
        if (orderItems.length === 0) return;
        
        const faltanCostos = orderItems.some(i => i.costoUnitario === "");
        if (faltanCostos) {
            showToast("Debes ingresar el costo unitario para todos los artículos", true);
            return;
        }
        
        btnProcesar.disabled = true;
        btnProcesar.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Consolidando...`;
        
        try {
            // Asegurar sincronización síncrona inmediata antes de consolidar
            const idProv = parseInt(selProveedor.value) || 0;
            const mTotal = orderItems.reduce((acc, i) => acc + (i.cantidad * parseFloat(i.costoUnitario || 0)), 0);
            
            const syncRes = await ApiClient.put('/compras/planificacion/borrador', {
                idProveedor: idProv,
                montoTotal: mTotal,
                items: orderItems.map(i => ({
                    idProducto: i.idProducto,
                    cantidad: i.cantidad,
                    costoUnitario: parseFloat(i.costoUnitario || 0)
                }))
            });
            
            const targetBorradorId = syncRes.idCompra || borradorIdCompra;
            
            const res = await ApiClient.post(`/compras/planificacion/borrador/${targetBorradorId}/consolidar`);
            
            showToast(`Orden Emitida Exitosamente (ID: #${res.idCompra})`);
            
            // Limpiar UI local
            orderItems = [];
            if (selProveedor) selProveedor.value = '';
            borradorIdCompra = null;
            updateOrderUI();
            await cargarSolicitudesPendientes();
            
            // Pasar a Pestaña Órdenes
            setTimeout(() => {
                switchTab('ordenes');
            }, 800);
            
        } catch (e) {
            showToast(e.message || "Error al consolidar", true);
            btnProcesar.disabled = false;
            btnProcesar.innerHTML = `<i class="fa-solid fa-lock"></i> Consolidar Orden`;
        }
    });
}

let ordenRecepcionActivaId = null;

// -------------------------------------------------------------
// ÓRDENES ACTIVAS
// -------------------------------------------------------------
async function cargarOrdenesActivas() {
    try {
        const data = await ApiClient.get('/compras/ordenes_activas');
        renderOrdenesActivas(data.ordenes || []);
    } catch(e) {
        console.error("Error cargando órdenes activas", e);
        renderOrdenesActivas([]);
    }
}

function renderOrdenesActivas(ordenes) {
    const tbody = document.getElementById('lista-ordenes-tabla');
    const empty = document.getElementById('ordenes-empty');
    if(!tbody || !empty) return;
    
    if (ordenes.length === 0) {
        tbody.innerHTML = '';
        empty.classList.remove('hidden');
        empty.classList.add('flex');
        return;
    }
    empty.classList.add('hidden');
    empty.classList.remove('flex');
    
    tbody.innerHTML = ordenes.map(o => `
        <tr class="hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors">
            <td class="py-3 px-4 font-mono font-bold text-gray-800 dark:text-gray-200">#${o.idCompra}</td>
            <td class="py-3 px-4 text-sm text-gray-600 dark:text-gray-400">${parseLocalDate(o.fecha).toLocaleString('es-PE')}</td>
            <td class="py-3 px-4 font-semibold text-gray-800 dark:text-gray-200">${o.proveedor}</td>
            <td class="py-3 px-4 text-right font-mono font-bold text-gray-800 dark:text-gray-200">${fmt(o.montoTotal)}</td>
            <td class="py-3 px-4 text-center">
                <span class="bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-300 px-2.5 py-1 rounded text-xs font-bold border border-blue-200 dark:border-blue-800">
                    <i class="fa-solid fa-clock mr-1"></i> ${o.estado}
                </span>
            </td>
            <td class="py-3 px-4 text-right">
                <div class="flex justify-end gap-2">
                    <button onclick="abrirModalDetalleOrden(${o.idCompra})" class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-bold text-xs bg-blue-50 dark:bg-blue-900/30 px-3 py-1.5 rounded-lg transition-colors active:scale-95">
                        Ver Detalles
                    </button>
                    <button onclick="abrirModalRecepcionFisica(${o.idCompra})" class="text-white bg-green-600 hover:bg-green-700 font-bold text-xs px-3 py-1.5 rounded-lg shadow-sm transition-colors active:scale-95 flex items-center gap-1.5">
                        <i class="fa-solid fa-boxes-packing"></i> Recibir Física
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// -------------------------------------------------------------
// HISTORIAL
// -------------------------------------------------------------
async function cargarHistorialGlobal() {
    try {
        const data = await ApiClient.get('/compras/historial');
        renderHistorialGlobal(data.historial || []);
    } catch (e) {
        console.error("Error cargando historial", e);
    }
}

function renderHistorialGlobal(historial) {
    const tbody = document.getElementById('lista-historial-tabla');
    const empty = document.getElementById('historial-empty');
    if(!tbody || !empty) return;

    if (historial.length === 0) {
        tbody.innerHTML = '';
        empty.classList.remove('hidden');
        empty.classList.add('flex');
        return;
    }

    empty.classList.add('hidden');
    empty.classList.remove('flex');

    tbody.innerHTML = historial.map(h => `
        <tr class="hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors">
            <td class="py-3 px-4 font-mono font-bold text-gray-800 dark:text-gray-200">#${h.idCompra}</td>
            <td class="py-3 px-4 text-sm text-gray-600 dark:text-gray-400">${parseLocalDate(h.fecha).toLocaleString('es-PE')}</td>
            <td class="py-3 px-4 font-semibold text-gray-800 dark:text-gray-200">${h.proveedor}</td>
            <td class="py-3 px-4 text-right font-mono font-bold text-gray-800 dark:text-gray-200">${fmt(h.montoTotal)}</td>
            <td class="py-3 px-4 text-center">
                <span class="bg-green-100 text-green-800 dark:bg-green-900/60 dark:text-green-300 px-2 py-1 rounded text-xs font-bold border border-green-200 dark:border-green-800">
                    <i class="fa-solid fa-check"></i> ${h.estado}
                </span>
            </td>
            <td class="py-3 px-4 text-right">
                <button onclick="abrirModalDetalleOrden(${h.idCompra})" class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-bold text-sm bg-blue-50 dark:bg-blue-900/30 px-3 py-1.5 rounded transition-colors active:scale-95">
                    Ver Detalles
                </button>
            </td>
        </tr>
    `).join('');
}

// -------------------------------------------------------------
// MODAL 1: DETALLES DE ORDEN / HISTORIAL
// -------------------------------------------------------------
async function abrirModalDetalleOrden(idCompra) {
    const modal = document.getElementById('modal-detalle-orden');
    const title = document.getElementById('modal-detalle-title');
    const content = document.getElementById('modal-detalle-content');
    
    if(!modal || !title || !content) return;
    
    title.textContent = `Orden #${idCompra}`;
    content.innerHTML = `<div class="flex justify-center p-8"><i class="fa-solid fa-circle-notch fa-spin text-2xl text-blue-600"></i></div>`;
    
    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        const card = modal.querySelector('div');
        if(card) card.classList.remove('scale-95');
    }, 10);

    try {
        const data = await ApiClient.get(`/compras/historial/${idCompra}/detalles`);
        const detallesHTML = data.detalles.map(d => `
            <div class="flex justify-between items-start py-2.5 border-b border-gray-100 dark:border-gray-700 last:border-0 text-sm">
                <div class="flex-1 pr-4">
                    <div class="font-bold text-gray-800 dark:text-gray-200">${d.producto}</div>
                    <div class="text-[10px] text-gray-400 font-mono">${d.codigo}</div>
                </div>
                <div class="text-right shrink-0">
                    <div class="font-bold text-gray-800 dark:text-gray-200">${d.cantidad} u. x ${fmt(d.costoUnitario)}</div>
                    <div class="text-xs font-mono font-bold text-gray-500 dark:text-gray-400">${fmt(d.subtotal)}</div>
                </div>
            </div>
        `).join('');
        
        content.innerHTML = `
            <div class="grid grid-cols-2 gap-4 mb-6 p-4 bg-gray-50 dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700">
                <div>
                    <div class="text-xs text-gray-400 uppercase font-bold tracking-wider mb-1">Proveedor</div>
                    <div class="font-bold text-gray-800 dark:text-gray-200 text-sm">${data.proveedor}</div>
                </div>
                <div>
                    <div class="text-xs text-gray-400 uppercase font-bold tracking-wider mb-1">Fecha de Orden</div>
                    <div class="font-bold text-gray-800 dark:text-gray-200 text-sm">${parseLocalDate(data.fecha).toLocaleString('es-PE')}</div>
                </div>
                <div class="col-span-2 pt-2 border-t border-gray-200 dark:border-gray-700 flex justify-between items-center">
                    <span class="text-xs text-gray-400 uppercase font-bold tracking-wider">Costo Total</span>
                    <span class="font-mono text-xl font-black text-gray-900 dark:text-white">${fmt(data.montoTotal)}</span>
                </div>
            </div>
            
            <h4 class="text-xs font-bold text-gray-600 dark:text-gray-300 uppercase tracking-wider mb-2">Artículos Incluidos</h4>
            <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-1 shadow-sm">
                ${detallesHTML}
            </div>
        `;
    } catch(e) {
        content.innerHTML = `<div class="p-4 text-center text-red-500 font-bold">Error al cargar detalles de la orden.</div>`;
    }
}

function cerrarModalDetalleOrden() {
    const modal = document.getElementById('modal-detalle-orden');
    if(!modal) return;
    const card = modal.querySelector('div');
    if(card) card.classList.add('scale-95');
    modal.classList.add('opacity-0');
    setTimeout(() => { modal.classList.add('hidden'); }, 200);
}

// -------------------------------------------------------------
// MODAL 2: RECEPCIÓN FÍSICA DE MERCADERÍA
// -------------------------------------------------------------
async function abrirModalRecepcionFisica(idCompra) {
    ordenRecepcionActivaId = idCompra;
    const modal = document.getElementById('modal-recepcion-fisica');
    const title = document.getElementById('modal-recepcion-title');
    const subtitle = document.getElementById('modal-recepcion-subtitle');
    const body = document.getElementById('modal-recepcion-body');
    const btn = document.getElementById('btn-confirmar-recepcion');
    
    if(!modal || !title || !body) return;
    
    title.textContent = `Recibir Orden #${idCompra}`;
    if(subtitle) subtitle.textContent = "Cargando datos...";
    body.innerHTML = `<div class="flex justify-center p-8"><i class="fa-solid fa-circle-notch fa-spin text-2xl text-green-600"></i></div>`;
    if(btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-circle-check"></i> Confirmar Recepción`;
    }

    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        const card = modal.querySelector('div');
        if(card) card.classList.remove('scale-95');
    }, 10);

    try {
        const data = await ApiClient.get(`/compras/historial/${idCompra}/detalles`);
        if(subtitle) subtitle.textContent = `${data.proveedor} • ${parseLocalDate(data.fecha).toLocaleDateString('es-PE')}`;
        
        const itemsRows = data.detalles.map((d, index) => `
            <div class="flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-700 last:border-0 text-sm">
                <div class="flex-1 pr-4">
                    <div class="font-bold text-gray-800 dark:text-gray-200">${d.producto}</div>
                    <div class="text-[10px] text-gray-400 font-mono">Solicitados: ${d.cantidad} u.</div>
                </div>
                <div class="w-32 text-right">
                    <label class="block text-[10px] font-bold text-gray-400 uppercase mb-1">Cant. Recibida</label>
                    <input type="number" min="1" value="${d.cantidad}" class="w-full px-2 py-1 border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-900 rounded font-bold text-center text-sm focus:bg-white dark:focus:bg-gray-800">
                </div>
            </div>
        `).join('');

        body.innerHTML = `
            <div>
                <h4 class="text-xs font-bold text-gray-600 dark:text-gray-300 uppercase tracking-wider mb-2">Verificación de Mercadería</h4>
                <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-1 shadow-sm mb-4">
                    ${itemsRows}
                </div>
            </div>
            <div>
                <label class="block text-xs font-bold text-gray-600 dark:text-gray-300 uppercase tracking-wider mb-1">Observaciones de Recepción</label>
                <textarea id="recepcion-observaciones" placeholder="Ingrese notas o discrepancias físicas (opcional)..." class="input-base w-full p-2.5 text-sm bg-gray-50 dark:bg-gray-900 border-gray-300 dark:border-gray-600 rounded-xl h-20 resize-none"></textarea>
            </div>
        `;
        
        if(btn) btn.disabled = false;
        
    } catch(e) {
        body.innerHTML = `<div class="p-4 text-center text-red-500 font-bold">Error al preparar recepción de la orden.</div>`;
    }
}

function cerrarModalRecepcionFisica() {
    const modal = document.getElementById('modal-recepcion-fisica');
    if(!modal) return;
    const card = modal.querySelector('div');
    if(card) card.classList.add('scale-95');
    modal.classList.add('opacity-0');
    setTimeout(() => { modal.classList.add('hidden'); }, 200);
}

async function confirmarRecepcionFisica() {
    if(!ordenRecepcionActivaId) return;
    
    const btn = document.getElementById('btn-confirmar-recepcion');
    if(btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Procesando...`;
    }

    try {
        const res = await ApiClient.put(`/compras/compra/${ordenRecepcionActivaId}/estado`, { estado: "Completada" });
        
        let msgToast = "Mercadería recibida. Stock físico actualizado correctamente.";
        if (res.stock_actualizado && res.stock_actualizado.length > 0) {
            const resumenStock = res.stock_actualizado.map(s => `${s.producto}: ${s.nuevo_stock} u.`).join(' | ');
            msgToast = `Stock actualizado -> ${resumenStock}`;
        }
        
        showToast(msgToast);
        cerrarModalRecepcionFisica();
        await cargarOrdenesActivas();
        await cargarHistorialGlobal();
    } catch(e) {
        showToast("Error al recibir orden: " + e.message, true);
        if(btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-circle-check"></i> Confirmar Recepción`;
        }
    }
}

document.addEventListener('DOMContentLoaded', init);
