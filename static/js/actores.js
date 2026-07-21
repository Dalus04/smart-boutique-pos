/**
 * Lógica Reactiva para Actores Comerciales (Catálogo Contextual e Inteligente)
 */

let currentTab = 'clientes'; // 'clientes' o 'proveedores'
let dataList = [];
let editId = null;

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

// Utils & Helpers
const fmt = (val) => `S/ ${Number(val).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits:2})}`;

function tiempoRelativo(isoString) {
    if (!isoString) return '<span class="text-gray-400 font-normal">Sin operaciones</span>';
    
    // Dado que el backend almacena las fechas con datetime.utcnow() (sin timezone),
    // debemos añadir 'Z' al final del ISO string para que JavaScript lo interprete como UTC
    // y lo convierta a la hora local peruana (-05:00) correctamente.
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
        textoRelativo = `Hace ${diffSegs} segundo${diffSegs !== 1 ? 's' : ''}`;
    } else if (diffMins < 60) {
        textoRelativo = `Hace ${diffMins} minuto${diffMins !== 1 ? 's' : ''}`;
    } else if (diffHoras < 24) {
        textoRelativo = `Hace ${diffHoras} hora${diffHoras !== 1 ? 's' : ''}`;
    } else if (diffDias < 30) {
        textoRelativo = `Hace ${diffDias} día${diffDias !== 1 ? 's' : ''}`;
    } else if (diffDias < 365) {
        const meses = Math.floor(diffDias / 30);
        textoRelativo = `Hace ${meses} mes${meses > 1 ? 'es' : ''}`;
    } else {
        const años = Math.floor(diffDias / 365);
        textoRelativo = `Hace ${años} año${años !== 1 ? 's' : ''}`;
    }
    
    return `<span class="cursor-help font-medium text-gray-700 dark:text-gray-300" title="Fecha exacta: ${fechaAbsoluta}">${textoRelativo}</span>`;
}

function debounce(func, delay = 350) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => { func.apply(this, args); }, delay);
    };
}

// -------------------------------------------------------------
// NAVEGACIÓN Y RENDERIZADO
// -------------------------------------------------------------
async function switchTab(tab) {
    currentTab = tab;
    searchInput.value = '';
    
    const btnC = document.getElementById('tab-clientes');
    const btnP = document.getElementById('tab-proveedores');
    
    if (tab === 'clientes') {
        btnC.className = "flex-1 lg:flex-none px-6 py-2.5 rounded-lg font-bold transition-colors bg-primary text-white shadow-sm";
        btnP.className = "flex-1 lg:flex-none px-6 py-2.5 rounded-lg font-bold transition-colors text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800";
        btnNuevoTexto.textContent = "Nuevo Cliente";
        document.getElementById('metric-total-label').textContent = "Total Clientes";
        document.getElementById('metric-activos-label').textContent = "Clientes VIP";
        document.getElementById('metric-ticket-label').textContent = "Ticket Promedio Global";
        renderTableHeaders(['Documento', 'Cliente', 'Frecuencia de compra', 'Categorías favoritas', 'Última compra', 'Oportunidad comercial', 'Acciones']);
    } else {
        btnP.className = "flex-1 lg:flex-none px-6 py-2.5 rounded-lg font-bold transition-colors bg-primary text-white shadow-sm";
        btnC.className = "flex-1 lg:flex-none px-6 py-2.5 rounded-lg font-bold transition-colors text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800";
        btnNuevoTexto.textContent = "Nuevo Proveedor";
        document.getElementById('metric-total-label').textContent = "Total Proveedores";
        document.getElementById('metric-activos-label').textContent = "Órdenes en Tránsito";
        document.getElementById('metric-ticket-label').textContent = "Compra Promedio";
        renderTableHeaders(['RUC', 'Razón Social', 'Estado de la relación', 'Líneas que provee', 'Último pedido', 'Próxima acción', 'Acciones']);
    }
    
    await fetchData();
}

function renderTableHeaders(headers) {
    tableHead.innerHTML = headers.map(h => 
        `<th class="py-3 px-4 text-xs font-bold text-gray-600 dark:text-gray-300 uppercase tracking-wider ${h==='Acciones'?'text-right':''}">${h}</th>`
    ).join('');
}

function updateMetrics(list) {
    mTotal.textContent = list.length;
    
    let activosCount = 0;
    let sumTicket = 0;
    let ticketCount = 0;
    
    const thirtyDaysAgo = Date.now() - (30 * 24 * 60 * 60 * 1000);

    list.forEach(item => {
        if (item.ultima_transaccion) {
            const lastDate = new Date(item.ultima_transaccion).getTime();
            if (lastDate >= thirtyDaysAgo) {
                activosCount++;
            }
        }
        if (item.ticket_promedio > 0) {
            sumTicket += item.ticket_promedio;
            ticketCount++;
        }
    });

    mActivos.textContent = activosCount;
    mTicket.textContent = ticketCount > 0 ? fmt(sumTicket / ticketCount) : 'S/ 0.00';
}

function getBadgeHtml(frecuencia, ultimaTransaccion, esCliente) {
    const isFrecuente = frecuencia >= 3;
    const lastOpDate = ultimaTransaccion ? new Date(ultimaTransaccion).getTime() : null;
    const isActivo = lastOpDate && (Date.now() - lastOpDate) < (30 * 24 * 60 * 60 * 1000);
    
    if (esCliente) {
        if (isFrecuente && isActivo) {
            return `<span class="cursor-help bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-200 border border-emerald-700/50 text-xs px-2.5 py-1 rounded font-bold shadow-sm" title="Cliente recurrente con 3 o más compras registradas y actividad en el último mes"><i class="fa-solid fa-star mr-1 text-emerald-600 dark:text-emerald-400"></i> Frecuente</span>`;
        } else if (isActivo) {
            return `<span class="cursor-help bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-200 border border-blue-700/50 text-xs px-2.5 py-1 rounded font-bold shadow-sm" title="Cliente activo que ha realizado compras durante los últimos 30 días"><i class="fa-solid fa-check mr-1 text-blue-600 dark:text-blue-400"></i> Activo</span>`;
        } else if (frecuencia > 0) {
            return `<span class="cursor-help bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-200 border border-amber-700/50 text-xs px-2.5 py-1 rounded font-bold shadow-sm" title="Cliente registrado que no ha comprado en los últimos 30 días"><i class="fa-solid fa-clock-rotate-left mr-1 text-amber-600 dark:text-amber-400"></i> Esporádico</span>`;
        } else {
            return `<span class="cursor-help bg-gray-100 text-gray-700 dark:bg-gray-700/80 dark:text-gray-200 border border-gray-600 text-xs px-2.5 py-1 rounded font-bold shadow-sm" title="Cliente registrado sin compras en el sistema"><i class="fa-solid fa-user-minus mr-1 text-gray-500 dark:text-gray-400"></i> Sin compras</span>`;
        }
    } else {
        if (isFrecuente && isActivo) {
            return `<span class="cursor-help bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-200 border border-emerald-700/50 text-xs px-2.5 py-1 rounded font-bold shadow-sm" title="Proveedor principal con pedidos continuos en el último mes"><i class="fa-solid fa-handshake mr-1 text-emerald-600 dark:text-emerald-400"></i> Proveedor Frecuente</span>`;
        } else if (isActivo) {
            return `<span class="cursor-help bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-200 border border-blue-700/50 text-xs px-2.5 py-1 rounded font-bold shadow-sm" title="Relación comercial activa con pedidos atendidos recientemente"><i class="fa-solid fa-check mr-1 text-blue-600 dark:text-blue-400"></i> Relación Activa</span>`;
        } else if (frecuencia > 0) {
            return `<span class="cursor-help bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-200 border border-amber-700/50 text-xs px-2.5 py-1 rounded font-bold shadow-sm" title="Sin pedidos de abastecimiento en los últimos 30 días"><i class="fa-solid fa-clock-rotate-left mr-1 text-amber-600 dark:text-amber-400"></i> Inactivo este mes</span>`;
        } else {
            return `<span class="cursor-help bg-gray-100 text-gray-700 dark:bg-gray-700/80 dark:text-gray-200 border border-gray-600 text-xs px-2.5 py-1 rounded font-bold shadow-sm" title="Proveedor registrado sin historial de abastecimiento"><i class="fa-solid fa-truck-ramp-box mr-1 text-gray-500 dark:text-gray-400"></i> Sin pedidos</span>`;
        }
    }
}

async function fetchData(query = '') {
    tableLoading.classList.remove('hidden');
    tableEmpty.classList.add('hidden');
    tableBody.innerHTML = '';
    
    try {
        const endpoint = currentTab === 'clientes' ? '/actores/clientes' : '/actores/proveedores';
        const params = query ? { q: query } : {};
        dataList = await ApiClient.get(endpoint, params);
        
        if (!query) updateMetrics(dataList);
        
        if (dataList.length === 0) {
            tableEmpty.classList.remove('hidden');
        } else {
            dataList.forEach(item => {
                const tr = document.createElement('tr');
                const id = currentTab === 'clientes' ? item.idCliente : item.idProveedor;
                tr.className = "hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors border-b border-gray-100 dark:border-gray-800/60 cursor-pointer";
                tr.onclick = (e) => {
                    if (e.target.closest('button')) return;
                    openOffCanvas(id);
                };
                
                const esCliente = currentTab === 'clientes';
                const badgeHtml = getBadgeHtml(item.frecuencia, item.ultima_transaccion, esCliente);
                const nombreMain = esCliente ? `${item.nombres} ${item.apellidos}` : item.nombreRazonSocial;
                
                const accion = item.accion_recomendada || { texto: 'Sin recomendación', explicacion: '', badge_class: 'bg-gray-100 text-gray-700' };

                tr.innerHTML = `
                    <td class="py-3.5 px-4 whitespace-nowrap text-sm font-mono">
                        <span class="font-bold text-gray-900 dark:text-gray-100 text-sm">${item.numeroDocumento}</span> 
                        <div class="text-xs text-gray-500 dark:text-gray-400 font-semibold uppercase mt-0.5">${item.tipoDocumento}</div>
                    </td>
                    <td class="py-3.5 px-4">
                        <div class="font-bold text-gray-900 dark:text-gray-100 text-sm">${nombreMain}</div>
                        <div class="text-xs text-gray-600 dark:text-gray-300 flex items-center gap-3 mt-1 font-medium">
                            <span><i class="fa-solid fa-phone text-xs mr-1 text-gray-400"></i>${item.telefono}</span>
                            <span><i class="fa-solid fa-envelope text-xs mr-1 text-gray-400"></i>${item.correoElectronico}</span>
                        </div>
                    </td>
                    <td class="py-3.5 px-4 whitespace-nowrap">${badgeHtml}</td>
                    <td class="py-3.5 px-4 whitespace-nowrap text-sm">
                        <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-100 text-purple-800 dark:bg-purple-900/60 dark:text-purple-200 border border-purple-700/50 shadow-sm">
                            <i class="fa-solid fa-tag text-[10px] mr-1.5 text-purple-600 dark:text-purple-300"></i> ${item.especialidad}
                        </span>
                    </td>
                    <td class="py-3.5 px-4 whitespace-nowrap text-sm">
                        ${tiempoRelativo(item.ultima_transaccion)}
                    </td>
                    <td class="py-3.5 px-4 whitespace-nowrap">
                        <span class="cursor-help inline-flex items-center px-3 py-1 rounded-lg text-xs font-bold ${accion.badge_class} shadow-sm" title="${accion.explicacion}">
                            <i class="fa-solid fa-lightbulb text-amber-500 dark:text-amber-400 mr-1.5"></i> ${accion.texto}
                        </span>
                    </td>
                    <td class="py-3.5 px-4 whitespace-nowrap text-right text-sm">
                        <button onclick="editActor(${id})" class="bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-100 border border-gray-300 dark:border-gray-600 transition-colors px-3 py-1.5 rounded-lg font-bold shadow-sm text-xs flex items-center gap-1.5 ml-auto">
                            <i class="fa-solid fa-pen-to-square text-blue-600 dark:text-blue-400"></i> Editar
                        </button>
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

searchInput.addEventListener('input', debounce(() => {
    fetchData(searchInput.value.trim());
}, 350));

// -------------------------------------------------------------
// PANEL OFF-CANVAS ANALÍTICO
// -------------------------------------------------------------
function openOffCanvas(id) {
    const item = dataList.find(i => (currentTab === 'clientes' ? i.idCliente : i.idProveedor) === id);
    if (!item) return;

    const overlay = document.getElementById('offcanvas-overlay');
    const panel = document.getElementById('offcanvas-panel');
    const esCliente = currentTab === 'clientes';

    // Rellenar Header
    document.getElementById('offcanvas-badge-container').innerHTML = getBadgeHtml(item.frecuencia, item.ultima_transaccion, esCliente);
    document.getElementById('offcanvas-title').textContent = esCliente ? `${item.nombres} ${item.apellidos}` : item.nombreRazonSocial;
    document.getElementById('offcanvas-subtitle').textContent = `${item.tipoDocumento}: ${item.numeroDocumento}`;

    // Rellenar Contacto
    document.getElementById('offcanvas-phone').textContent = (item.telefono && item.telefono !== "-") ? item.telefono : 'Sin teléfono';
    document.getElementById('offcanvas-email').textContent = (item.correoElectronico && item.correoElectronico !== "-") ? item.correoElectronico : 'Sin correo electrónico';
    
    const addressRow = document.getElementById('offcanvas-address-row');
    if (!esCliente) {
        addressRow.classList.remove('hidden');
        document.getElementById('offcanvas-address').textContent = (item.direccion && item.direccion !== "-") ? item.direccion : 'Sin dirección registrada';
    } else {
        addressRow.classList.add('hidden');
    }

    // Rellenar Métricas
    document.getElementById('offcanvas-metric-1-label').textContent = esCliente ? 'Compras' : 'Órdenes';
    document.getElementById('offcanvas-metric-1-value').textContent = item.frecuencia || 0;
    
    document.getElementById('offcanvas-metric-2-label').textContent = esCliente ? 'Ticket Promedio' : 'Compra Promedio';
    document.getElementById('offcanvas-metric-2-value').textContent = fmt(item.ticket_promedio || 0);

    document.getElementById('offcanvas-especialidad').textContent = item.especialidad || 'Sin registro';

    // Sugerencia
    const accion = item.accion_recomendada || { texto: 'N/A', explicacion: 'Sin información suficiente' };
    document.getElementById('offcanvas-accion-title').textContent = accion.texto;
    document.getElementById('offcanvas-accion-desc').textContent = accion.explicacion;
    document.getElementById('offcanvas-accion').className = `p-4 rounded-xl border ${accion.badge_class}`;

    // Footer Action (Deep Linking)
    const btnAction = document.getElementById('offcanvas-main-action');
    if (esCliente) {
        document.getElementById('offcanvas-action-text').textContent = 'Registrar Venta';
        btnAction.onclick = () => window.location.href = `/pos?tab=venta&select_client_id=${item.idCliente}`;
    } else {
        document.getElementById('offcanvas-action-text').textContent = 'Registrar Compra';
        btnAction.onclick = () => window.location.href = `/compras?tab=planificacion&select_supplier_id=${item.idProveedor}`;
    }

    // Mostrar
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
// GESTIÓN DEL MODAL
// -------------------------------------------------------------
function openModal(item = null) {
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
    
    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        modal.firstElementChild.classList.remove('scale-95');
    }, 10);
}

function closeModal() {
    modal.classList.add('opacity-0');
    modal.firstElementChild.classList.add('scale-95');
    setTimeout(() => {
        modal.classList.add('hidden');
    }, 300);
}

function editActor(id) {
    const item = dataList.find(i => (currentTab==='clientes' ? i.idCliente : i.idProveedor) === id);
    if(item) openModal(item);
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
    btnSave.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Guardando...`;
    
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
        closeModal();
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
