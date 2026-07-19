/**
 * Lógica Reactiva para Actores Comerciales (CRUD)
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

// -------------------------------------------------------------
// NAVEGACIÓN Y RENDERIZADO
// -------------------------------------------------------------
async function switchTab(tab) {
    currentTab = tab;
    
    // UI Update Tabs
    const btnC = document.getElementById('tab-clientes');
    const btnP = document.getElementById('tab-proveedores');
    
    if (tab === 'clientes') {
        btnC.className = "px-6 py-2 rounded-lg font-bold transition-colors bg-primary text-white";
        btnP.className = "px-6 py-2 rounded-lg font-bold transition-colors text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800";
        btnNuevoTexto.textContent = "Nuevo Cliente";
        renderTableHeaders(['Documento', 'Nombres', 'Apellidos', 'Teléfono', 'Acciones']);
    } else {
        btnP.className = "px-6 py-2 rounded-lg font-bold transition-colors bg-primary text-white";
        btnC.className = "px-6 py-2 rounded-lg font-bold transition-colors text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800";
        btnNuevoTexto.textContent = "Nuevo Proveedor";
        renderTableHeaders(['RUC', 'Razón Social', 'Teléfono', 'Dirección', 'Acciones']);
    }
    
    await fetchData();
}

function renderTableHeaders(headers) {
    tableHead.innerHTML = headers.map(h => 
        `<th class="py-3 px-4 text-xs font-bold text-gray-500 uppercase tracking-wider ${h==='Acciones'?'text-right':''}">${h}</th>`
    ).join('');
}

async function fetchData() {
    tableLoading.classList.remove('hidden');
    tableEmpty.classList.add('hidden');
    tableBody.innerHTML = '';
    
    try {
        const endpoint = currentTab === 'clientes' ? '/actores/clientes' : '/actores/proveedores';
        dataList = await ApiClient.get(endpoint);
        
        if (dataList.length === 0) {
            tableEmpty.classList.remove('hidden');
        } else {
            dataList.forEach(item => {
                const tr = document.createElement('tr');
                tr.className = "hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors";
                
                const id = currentTab === 'clientes' ? item.idCliente : item.idProveedor;
                
                if (currentTab === 'clientes') {
                    tr.innerHTML = `
                        <td class="py-3 px-4 whitespace-nowrap text-sm text-gray-500 font-mono">
                            <span class="font-bold text-gray-800 dark:text-gray-200">${item.numeroDocumento}</span> 
                            <span class="text-xs">(${item.tipoDocumento})</span>
                        </td>
                        <td class="py-3 px-4 whitespace-nowrap font-medium text-gray-900 dark:text-gray-100">${item.nombres}</td>
                        <td class="py-3 px-4 whitespace-nowrap font-medium text-gray-900 dark:text-gray-100">${item.apellidos}</td>
                        <td class="py-3 px-4 whitespace-nowrap text-sm text-gray-500">${item.telefono}</td>
                        <td class="py-3 px-4 whitespace-nowrap text-right text-sm font-medium">
                            <button onclick="editActor(${id})" class="text-primary hover:text-blue-700 transition-colors p-2"><i class="fa-solid fa-pen-to-square"></i></button>
                        </td>
                    `;
                } else {
                    tr.innerHTML = `
                        <td class="py-3 px-4 whitespace-nowrap text-sm text-gray-500 font-mono font-bold text-gray-800 dark:text-gray-200">
                            ${item.numeroDocumento}
                        </td>
                        <td class="py-3 px-4 font-medium text-gray-900 dark:text-gray-100 line-clamp-1" title="${item.nombreRazonSocial}">${item.nombreRazonSocial}</td>
                        <td class="py-3 px-4 whitespace-nowrap text-sm text-gray-500">${item.telefono}</td>
                        <td class="py-3 px-4 text-sm text-gray-500 line-clamp-1" title="${item.direccion}">${item.direccion}</td>
                        <td class="py-3 px-4 whitespace-nowrap text-right text-sm font-medium">
                            <button onclick="editActor(${id})" class="text-primary hover:text-blue-700 transition-colors p-2"><i class="fa-solid fa-pen-to-square"></i></button>
                        </td>
                    `;
                }
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
// GESTIÓN DEL MODAL
// -------------------------------------------------------------
function openModal(item = null) {
    // Reset validations
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
        
        // Options update
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
    // Pequeño delay para la transición de opacidad/escala
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
    // 1. Validaciones HTML Nativas
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    // 2. Validación Estricta de Documento (JS Frontend Requirement)
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
    
    // 3. Preparar Payload
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
