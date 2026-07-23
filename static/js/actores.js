/**
 * Lógica Reactiva para Actores Comerciales (Saneamiento e Inactivación - Fase 2)
 */

let currentTab = 'clientes'; // 'clientes' o 'proveedores'
let dataList = [];
let editId = null;
let currentOffcanvasTab = 'info';

// Paginación Server-Side State
let currentPage = 1;
let currentLimit = 10;
let totalPages = 1;
let totalRecords = 0;

// DOM Elements
const tableHead = document.getElementById('table-head');
const tableBody = document.getElementById('table-body');
const tableLoading = document.getElementById('table-loading');
const tableEmpty = document.getElementById('table-empty');

const modal = document.getElementById('actor-modal');
const modalTitle = document.getElementById('modal-title');
const btnNuevoTexto = document.getElementById('btn-nuevo-texto');
const searchInput = document.getElementById('search-actor');

// Métricas DOM
const mTotal = document.getElementById('metric-total');
const mActivos = document.getElementById('metric-activos');
const mTicket = document.getElementById('metric-ticket');

// Form Elements
const form = document.getElementById('actor-form');
const fTipoDoc = document.getElementById('form-tipo-doc');
const fNumDoc = document.getElementById('form-num-doc');
const docError = document.getElementById('doc-error');

const camposCliente = document.getElementById('campos-cliente');
const fNombres = document.getElementById('form-nombres');
const fApellidos = document.getElementById('form-apellidos');

const camposProveedor = document.getElementById('campos-proveedor');
const fRazonSocial = document.getElementById('form-razon-social');

const fTelefono = document.getElementById('form-telefono');
const fCorreo = document.getElementById('form-correo');

const camposDireccion = document.getElementById('campos-direccion');
const fDireccion = document.getElementById('form-direccion');

// fmt y debounce disponibles desde utils.js (cargado en base.html)


function tiempoRelativo(isoString) {
    if (!isoString) return '<span class="text-gray-400 font-normal">Sin operaciones</span>';
    
    let dateStr = isoString;
    if (!isoString.includes('Z') && !/[+-]\d{2}:\d{2}$/.test(isoString)) {
        dateStr = isoString + 'Z';
    }
    
    const fecha = new Date(dateStr);
    const ahora = new Date();
    const diffMs = ahora - fecha;
    
    const diffSegs = Math.max(0, Math.floor(diffMs / 1000));
    const diffMins = Math.floor(diffSegs / 60);
    const diffHoras = Math.floor(diffMins / 60);
    const diffDias = Math.floor(diffHoras / 24);
    
    const fechaAbsoluta = fecha.toLocaleString('es-PE', { dateStyle: 'short', timeStyle: 'short' });
    
    let textoRelativo = '';
    if (diffSegs < 60) {
        textoRelativo = `Hace ${diffSegs}s`;
    } else if (diffMins < 60) {
        textoRelativo = `Hace ${diffMins} min${diffMins !== 1 ? 's' : ''}`;
    } else if (diffHoras < 24) {
        textoRelativo = `Hace ${diffHoras} h`;
    } else if (diffDias < 30) {
        textoRelativo = `Hace ${diffDias} d`;
    } else if (diffDias < 365) {
        const meses = Math.floor(diffDias / 30);
        textoRelativo = `Hace ${meses} mes${meses > 1 ? 'es' : ''}`;
    } else {
        const años = Math.floor(diffDias / 365);
        textoRelativo = `Hace ${años} a`;
    }
    
    return `<span class="cursor-help font-medium text-gray-700 dark:text-gray-300" title="Fecha exacta: ${fechaAbsoluta}">${textoRelativo}</span>`;
}



// -------------------------------------------------------------
// NAVEGACIÓN Y RENDERIZADO
// -------------------------------------------------------------
async function switchTab(tab) {
    currentTab = tab;
    currentPage = 1;
    searchInput.value = '';
    
    const btnC = document.getElementById('btn-tab-clientes');
    const btnP = document.getElementById('btn-tab-proveedores');
    
    if (tab === 'clientes') {
        btnC.className = "flex-1 lg:flex-none px-6 py-2.5 rounded-lg font-bold transition-colors bg-primary text-white shadow-sm";
        btnP.className = "flex-1 lg:flex-none px-6 py-2.5 rounded-lg font-bold transition-colors text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800";
        btnNuevoTexto.textContent = "Nuevo Cliente";
        document.getElementById('metric-total-label').textContent = "Total Clientes";
        document.getElementById('metric-activos-label').textContent = "Clientes Frecuentes";
        document.getElementById('metric-ticket-label').textContent = "Ticket Promedio Global";
        renderTableHeaders(['Documento', 'Cliente', 'Estado / Frecuencia', 'Categoría Preferida', 'Última Compra', 'Acciones']);
    } else {
        btnP.className = "flex-1 lg:flex-none px-6 py-2.5 rounded-lg font-bold transition-colors bg-primary text-white shadow-sm";
        btnC.className = "flex-1 lg:flex-none px-6 py-2.5 rounded-lg font-bold transition-colors text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800";
        btnNuevoTexto.textContent = "Nuevo Proveedor";
        document.getElementById('metric-total-label').textContent = "Total Proveedores";
        document.getElementById('metric-activos-label').textContent = "Proveedores Activos";
        document.getElementById('metric-ticket-label').textContent = "Compra Promedio Global";
        renderTableHeaders(['RUC', 'Razón Social', 'Estado / Relación', 'Línea de Suministro', 'Último Pedido', 'Acciones']);
    }
    
    await fetchData();
}

function renderTableHeaders(headers) {
    tableHead.innerHTML = headers.map(h => 
        `<th class="py-3 px-4 text-xs font-bold text-gray-600 dark:text-gray-300 uppercase tracking-wider ${h==='Acciones'?'text-right':''}">${h}</th>`
    ).join('');
}

function updateMetrics(list, totalRecs) {
    mTotal.textContent = totalRecs !== undefined ? totalRecs : list.length;
    
    let sumTicket = 0;
    let ticketCount = 0;
    
    if (currentTab === 'clientes') {
        const frecuentesCount = list.filter(item => (item.frecuencia || 0) >= 3).length;
        mActivos.textContent = frecuentesCount;
    } else {
        mActivos.textContent = totalRecs !== undefined ? totalRecs : list.length;
    }

    list.forEach(item => {
        if (item.ticket_promedio > 0) {
            sumTicket += item.ticket_promedio;
            ticketCount++;
        }
    });

    mTicket.textContent = ticketCount > 0 ? fmt(sumTicket / ticketCount) : 'S/ 0.00';
}

function getSubtleBadgeHtml(frecuencia, esCliente) {
    const isFrecuente = frecuencia >= 3;
    
    if (esCliente) {
        if (isFrecuente) {
            return `<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"><i class="fa-solid fa-star text-[9px] mr-1"></i> Frecuente (${frecuencia})</span>`;
        } else if (frecuencia > 0) {
            return `<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border border-blue-200 dark:border-blue-800">Registrado (${frecuencia})</span>`;
        } else {
            return `<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400">Sin compras</span>`;
        }
    } else {
        if (isFrecuente) {
            return `<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"><i class="fa-solid fa-handshake text-[9px] mr-1"></i> Frecuente (${frecuencia})</span>`;
        } else if (frecuencia > 0) {
            return `<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border border-blue-200 dark:border-blue-800">Activo (${frecuencia})</span>`;
        } else {
            return `<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400">Sin pedidos</span>`;
        }
    }
}

async function fetchData(query = '') {
    tableLoading.classList.remove('hidden');
    tableEmpty.classList.add('hidden');
    tableBody.innerHTML = '';
    closeAllDropdowns();
    
    try {
        const endpoint = currentTab === 'clientes' ? '/actores/clientes' : '/actores/proveedores';
        const params = { page: currentPage, limit: currentLimit };
        if (query) params.q = query;
        
        const response = await ApiClient.get(endpoint, params);
        
        if (response && response.data !== undefined) {
            dataList = response.data || [];
            totalPages = response.total_pages || 1;
            currentPage = response.current_page || 1;
            totalRecords = response.total_records || 0;
        } else {
            dataList = Array.isArray(response) ? response : [];
            totalPages = 1;
            currentPage = 1;
            totalRecords = dataList.length;
        }
        
        updateMetrics(dataList, totalRecords);
        renderPagination('pagination-container', {
            total: totalRecords,
            page: currentPage,
            pages: totalPages,
            limit: currentLimit
        }, (newPage, newLimit) => {
            currentLimit = newLimit;
            currentPage = newPage;
            fetchData(searchInput.value.trim());
        });
        
        if (dataList.length === 0) {
            tableEmpty.classList.remove('hidden');
        } else {
            dataList.forEach(item => {
                const tr = document.createElement('tr');
                const id = currentTab === 'clientes' ? item.idCliente : item.idProveedor;
                tr.className = "hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors border-b border-gray-100 dark:border-gray-800/60 cursor-pointer relative";
                tr.onclick = (e) => {
                    if (e.target.closest('.context-menu-container')) return;
                    openOffCanvas(id);
                };
                
                const esCliente = currentTab === 'clientes';
                const badgeHtml = getSubtleBadgeHtml(item.frecuencia, esCliente);
                const nombreMain = esCliente ? `${item.nombres} ${item.apellidos}` : item.nombreRazonSocial;

                tr.innerHTML = `
                    <td class="py-3.5 px-4 whitespace-nowrap text-sm font-mono">
                        <span class="font-bold text-gray-900 dark:text-gray-100 text-sm">${item.numeroDocumento}</span> 
                        <span class="text-[10px] text-gray-400 dark:text-gray-500 uppercase ml-1.5 font-semibold">${item.tipoDocumento}</span>
                    </td>
                    <td class="py-3.5 px-4">
                        <div class="font-bold text-gray-900 dark:text-gray-100 text-sm">${nombreMain}</div>
                    </td>
                    <td class="py-3.5 px-4 whitespace-nowrap">${badgeHtml}</td>
                    <td class="py-3.5 px-4 whitespace-nowrap text-xs text-gray-600 dark:text-gray-300 font-medium">
                        ${item.especialidad || (esCliente ? 'Sin compras' : 'Sin pedidos')}
                    </td>
                    <td class="py-3.5 px-4 whitespace-nowrap text-sm">
                        ${tiempoRelativo(item.ultima_transaccion)}
                    </td>
                    <td class="py-3.5 px-4 whitespace-nowrap text-right text-sm context-menu-container">
                        <div class="relative inline-block text-left">
                            <button onclick="toggleDropdown(${id}, event)" class="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700/80 transition-colors">
                                <i class="fa-solid fa-ellipsis-vertical text-base"></i>
                            </button>
                            <div id="dropdown-${id}" class="hidden absolute right-0 mt-1 w-44 bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-100 dark:border-gray-700 z-30 py-1.5 text-xs text-left">
                                <button onclick="triggerAction(${id}, 'operacion', event)" class="w-full px-4 py-2 flex items-center gap-2.5 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700/60 font-medium">
                                    <i class="fa-solid fa-cart-shopping text-blue-500"></i> ${esCliente ? 'Registrar Venta' : 'Registrar Compra'}
                                </button>
                                <button onclick="triggerAction(${id}, 'editar', event)" class="w-full px-4 py-2 flex items-center gap-2.5 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700/60 font-medium">
                                    <i class="fa-solid fa-pen-to-square text-amber-500"></i> Editar
                                </button>
                                <button onclick="triggerAction(${id}, 'detalle', event)" class="w-full px-4 py-2 flex items-center gap-2.5 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700/60 font-medium">
                                    <i class="fa-solid fa-eye text-purple-500"></i> Ver Detalle
                                </button>
                                <button onclick="triggerAction(${id}, 'historial', event)" class="w-full px-4 py-2 flex items-center gap-2.5 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700/60 font-medium">
                                    <i class="fa-solid fa-clock-rotate-left text-emerald-500"></i> Historial
                                </button>
                                <div class="border-t border-gray-100 dark:border-gray-700/60 my-1"></div>
                                <button onclick="inactivarActor(${id}, event)" class="w-full px-4 py-2 flex items-center gap-2.5 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 font-medium">
                                    <i class="fa-solid fa-user-xmark text-red-500"></i> Inactivar
                                </button>
                            </div>
                        </div>
                    </td>
                `;
                tableBody.appendChild(tr);
            });
        }
    } catch (e) {
        console.error("Error fetching data:", e);
    } finally {
        tableLoading.classList.add('hidden');
    }
}

// -------------------------------------------------------------
// INACTIVACIÓN SEGURA (SOFT-DELETE)
// -------------------------------------------------------------
async function inactivarActor(id, event) {
    if (event) event.stopPropagation();
    closeAllDropdowns();
    
    const esCliente = currentTab === 'clientes';
    const item = dataList.find(i => (esCliente ? i.idCliente : i.idProveedor) === id);
    const nombre = item ? (esCliente ? `${item.nombres} ${item.apellidos}` : item.nombreRazonSocial) : `ID #${id}`;
    
    if (!confirm(`¿Estás seguro de que deseas inactivar a "${nombre}"?\nEl registro cambiará su estado a 'INACTIVO' y dejará de mostrarse en las listas activas.`)) {
        return;
    }
    
    const endpoint = esCliente ? `/actores/clientes/${id}/inactivar` : `/actores/proveedores/${id}/inactivar`;
    
    try {
        await ApiClient.patch(endpoint);
        closeOffCanvas();
        await fetchData(searchInput.value.trim());
    } catch (e) {
        alert(e.message || "Error al inactivar el registro");
    }
}

// -------------------------------------------------------------
// MENÚ CONTEXTUAL (DROPDOWN)
// -------------------------------------------------------------
function toggleDropdown(id, event) {
    if (event) event.stopPropagation();
    
    const dropdown = document.getElementById(`dropdown-${id}`);
    const isHidden = dropdown.classList.contains('hidden');
    
    closeAllDropdowns();
    
    if (isHidden) {
        dropdown.classList.remove('hidden');
    }
}

function closeAllDropdowns() {
    document.querySelectorAll('[id^="dropdown-"]').forEach(el => el.classList.add('hidden'));
}

document.addEventListener('click', () => {
    closeAllDropdowns();
});

function triggerAction(id, action, event) {
    if (event) event.stopPropagation();
    closeAllDropdowns();
    
    const esCliente = currentTab === 'clientes';
    
    if (action === 'operacion') {
        if (esCliente) {
            window.location.href = `/pos?tab=venta&select_client_id=${id}`;
        } else {
            window.location.href = `/compras?tab=planificacion&select_supplier_id=${id}`;
        }
    } else if (action === 'editar') {
        editActor(id);
    } else if (action === 'detalle') {
        openOffCanvas(id, 'info');
    } else if (action === 'historial') {
        openOffCanvas(id, 'actividad');
    }
}

searchInput.addEventListener('input', debounce(() => {
    currentPage = 1;
    fetchData(searchInput.value.trim());
}, 350));

// -------------------------------------------------------------
// PANEL OFF-CANVAS AMBULATORIO Y REESTRUCTURADO
// -------------------------------------------------------------
function switchOffcanvasTab(tabName) {
    currentOffcanvasTab = tabName;
    
    const btnInfo = document.getElementById('offcanvas-tab-info');
    const btnAct = document.getElementById('offcanvas-tab-actividad');
    const btnAcc = document.getElementById('offcanvas-tab-acciones');
    
    const secInfo = document.getElementById('offcanvas-sec-info');
    const secAct = document.getElementById('offcanvas-sec-actividad');
    const secAcc = document.getElementById('offcanvas-sec-acciones');
    
    const activeClass = "flex-1 py-2 text-xs font-bold uppercase tracking-wider text-primary border-b-2 border-primary transition-colors";
    const inactiveClass = "flex-1 py-2 text-xs font-bold uppercase tracking-wider text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 border-b-2 border-transparent transition-colors";
    
    btnInfo.className = tabName === 'info' ? activeClass : inactiveClass;
    btnAct.className = tabName === 'actividad' ? activeClass : inactiveClass;
    btnAcc.className = tabName === 'acciones' ? activeClass : inactiveClass;
    
    secInfo.classList.toggle('hidden', tabName !== 'info');
    secAct.classList.toggle('hidden', tabName !== 'actividad');
    secAcc.classList.toggle('hidden', tabName !== 'acciones');
}

function openOffCanvas(id, initialTab = 'info') {
    const item = dataList.find(i => (currentTab === 'clientes' ? i.idCliente : i.idProveedor) === id);
    if (!item) return;

    const overlay = document.getElementById('offcanvas-overlay');
    const panel = document.getElementById('offcanvas-panel');
    const esCliente = currentTab === 'clientes';

    // Header Info
    document.getElementById('offcanvas-badge-container').innerHTML = getSubtleBadgeHtml(item.frecuencia, esCliente);
    document.getElementById('offcanvas-title').textContent = esCliente ? `${item.nombres} ${item.apellidos}` : item.nombreRazonSocial;
    document.getElementById('offcanvas-subtitle').textContent = `${item.tipoDocumento}: ${item.numeroDocumento}`;

    // Tab 1: Identificación y Contacto
    document.getElementById('offcanvas-tipo-doc').textContent = item.tipoDocumento;
    document.getElementById('offcanvas-num-doc').textContent = item.numeroDocumento;
    document.getElementById('offcanvas-phone').textContent = (item.telefono && item.telefono !== "-") ? item.telefono : 'Sin teléfono';
    document.getElementById('offcanvas-email').textContent = (item.correoElectronico && item.correoElectronico !== "-") ? item.correoElectronico : 'Sin correo electrónico';
    
    const addressRow = document.getElementById('offcanvas-address-row');
    if (!esCliente) {
        addressRow.classList.remove('hidden');
        document.getElementById('offcanvas-address').textContent = (item.direccion && item.direccion !== "-") ? item.direccion : 'Sin dirección registrada';
    } else {
        addressRow.classList.add('hidden');
    }

    // Tab 2: Métricas de Negocio & Actividad
    document.getElementById('offcanvas-metric-1-label').textContent = esCliente ? 'Transacciones' : 'Pedidos';
    document.getElementById('offcanvas-metric-1-value').textContent = item.frecuencia || 0;
    
    document.getElementById('offcanvas-metric-2-label').textContent = esCliente ? 'Ticket Promedio' : 'Compra Promedio';
    document.getElementById('offcanvas-metric-2-value').textContent = fmt(item.ticket_promedio || 0);

    const totalAcumulado = (item.frecuencia || 0) * (item.ticket_promedio || 0);
    document.getElementById('offcanvas-total-acumulado').textContent = fmt(totalAcumulado);

    document.getElementById('offcanvas-especialidad').textContent = item.especialidad || (esCliente ? 'Sin compras' : 'Sin suministros');

    document.getElementById('offcanvas-ultima-fecha').innerHTML = item.ultima_transaccion 
        ? tiempoRelativo(item.ultima_transaccion) 
        : '<span class="text-gray-400">Sin historial</span>';

    // Tab 3: Acciones
    const btnOperacion = document.getElementById('offcanvas-btn-operacion');
    const actionText = document.getElementById('offcanvas-action-text');
    actionText.textContent = esCliente ? 'Registrar Venta' : 'Registrar Compra';
    btnOperacion.onclick = () => {
        closeOffCanvas();
        triggerAction(id, 'operacion');
    };

    const btnEditar = document.getElementById('offcanvas-btn-editar');
    btnEditar.onclick = () => {
        closeOffCanvas();
        editActor(id);
    };

    const btnInactivar = document.getElementById('offcanvas-btn-inactivar');
    if (btnInactivar) {
        btnInactivar.onclick = () => {
            inactivarActor(id);
        };
    }

    // Cambiar a la pestaña seleccionada
    switchOffcanvasTab(initialTab);

    // Mostrar modal lateral
    overlay.classList.remove('hidden');
    setTimeout(() => {
        overlay.classList.remove('opacity-0');
        panel.classList.remove('translate-x-full');
    }, 10);
}

function closeOffCanvas() {
    const overlay = document.getElementById('offcanvas-overlay');
    const panel = document.getElementById('offcanvas-panel');
    
    overlay.classList.add('opacity-0');
    panel.classList.add('translate-x-full');
    setTimeout(() => {
        overlay.classList.add('hidden');
    }, 300);
}

// -------------------------------------------------------------
// GESTIÓN DEL MODAL CREACIÓN / EDICIÓN
// -------------------------------------------------------------
function openActorModal(item = null) {
    docError.classList.add('hidden');
    fNumDoc.classList.remove('border-red-500');
    
    if (currentTab === 'clientes') {
        modalTitle.textContent = item ? "Editar Cliente" : "Nuevo Cliente";
        camposCliente.classList.remove('hidden');
        camposProveedor.classList.add('hidden');
        camposDireccion.classList.add('hidden');
        
        fNombres.required = true;
        fApellidos.required = true;
        fRazonSocial.required = false;
        
        fTipoDoc.innerHTML = `
            <option value="DNI">DNI (8 dígitos)</option>
            <option value="RUC">RUC (11 dígitos)</option>
        `;
    } else {
        modalTitle.textContent = item ? "Editar Proveedor" : "Nuevo Proveedor";
        camposCliente.classList.add('hidden');
        camposProveedor.classList.remove('hidden');
        camposDireccion.classList.remove('hidden');
        
        fNombres.required = false;
        fApellidos.required = false;
        fRazonSocial.required = true;
        
        fTipoDoc.innerHTML = `<option value="RUC">RUC (11 dígitos)</option>`;
    }
    
    if (item) {
        editId = currentTab === 'clientes' ? item.idCliente : item.idProveedor;
        fTipoDoc.value = item.tipoDocumento;
        fNumDoc.value = item.numeroDocumento;
        fTelefono.value = item.telefono === "-" ? "" : item.telefono;
        fCorreo.value = item.correoElectronico === "-" ? "" : item.correoElectronico;
        
        if (currentTab === 'clientes') {
            fNombres.value = item.nombres;
            fApellidos.value = item.apellidos;
        } else {
            fRazonSocial.value = item.nombreRazonSocial;
            fDireccion.value = item.direccion === "-" ? "" : item.direccion;
        }
    } else {
        editId = null;
        form.reset();
        if (currentTab === 'clientes') fTipoDoc.value = "DNI";
    }
    
    openModal('actor-modal');
}

function closeActorModal() {
    closeModal('actor-modal');
    editId = null;
}

function editActor(id) {
    const item = dataList.find(i => (currentTab === 'clientes' ? i.idCliente : i.idProveedor) === id);
    if (item) openActorModal(item);
}

// -------------------------------------------------------------
// VALIDACIÓN Y GUARDADO
// -------------------------------------------------------------
async function saveActor() {
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    const num = fNumDoc.value.trim();
    const isRuc = fTipoDoc.value === 'RUC';
    
    const isValidDni = /^\d{8}$/.test(num);
    const isValidRuc = /^\d{11}$/.test(num);
    
    if ((isRuc && !isValidRuc) || (!isRuc && !isValidDni)) {
        fNumDoc.classList.add('border-red-500');
        docError.textContent = isRuc ? "El RUC debe tener exactamente 11 números." : "El DNI debe tener exactamente 8 números.";
        docError.classList.remove('hidden');
        return;
    }
    
    docError.classList.add('hidden');
    fNumDoc.classList.remove('border-red-500');
    
    const btnSave = document.getElementById('btn-save');
    btnSave.disabled = true;
    btnSave.innerHTML = getSpinnerHtml("Guardando...");
    
    const endpoint = currentTab === 'clientes' 
        ? (editId ? `/actores/clientes/${editId}` : `/actores/clientes`)
        : (editId ? `/actores/proveedores/${editId}` : `/actores/proveedores`);
        
    const method = editId ? 'put' : 'post';
    
    const payload = {
        tipoDocumento: fTipoDoc.value,
        numeroDocumento: num,
        telefono: fTelefono.value.trim() || null,
        correoElectronico: fCorreo.value.trim() || null
    };
    
    if (currentTab === 'clientes') {
        payload.nombres = fNombres.value.trim();
        payload.apellidos = fApellidos.value.trim();
    } else {
        payload.nombreRazonSocial = fRazonSocial.value.trim();
        payload.direccion = fDireccion.value.trim() || null;
    }
    
    try {
        await ApiClient[method](endpoint, payload);
        closeActorModal();
        await fetchData();
    } catch (e) {
        alert(e.message || "Error al guardar");
    } finally {
        btnSave.disabled = false;
        btnSave.textContent = "Guardar";
    }
}

// Inicialización
document.addEventListener('DOMContentLoaded', () => {
    switchTab('clientes');
});
