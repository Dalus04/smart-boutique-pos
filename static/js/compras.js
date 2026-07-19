/**
 * Motor Reactivo - Compras y Abastecimiento
 */

let orderItems = [];
let proveedores = [];

// DOM Elements
const selProveedor = document.getElementById('select-proveedor');
const fechaActual = document.getElementById('fecha-actual');
const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('search-results');
const cartItems = document.getElementById('cart-items');
const cartEmpty = document.getElementById('cart-empty');
const sumItems = document.getElementById('summary-items');
const sumSubtotal = document.getElementById('summary-subtotal');
const sumTotal = document.getElementById('summary-total');
const btnProcesar = document.getElementById('btn-procesar');

const toast = document.getElementById('toast');
const toastMsg = document.getElementById('toast-msg');

const fmt = (val) => `$${Number(val).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits:2})}`;

// Debounce
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
// INICIALIZACIÓN
// -------------------------------------------------------------
async function init() {
    const today = new Date();
    fechaActual.textContent = today.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });
    
    try {
        proveedores = await ApiClient.get('/actores/proveedores');
        selProveedor.innerHTML = '<option value="">Seleccione un proveedor...</option>';
        proveedores.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.idProveedor;
            opt.textContent = `${p.numeroDocumento} - ${p.nombreRazonSocial}`;
            selProveedor.appendChild(opt);
        });
    } catch (e) {
        console.error("Error cargando proveedores", e);
        selProveedor.innerHTML = '<option value="">Error cargando proveedores</option>';
    }
}

// -------------------------------------------------------------
// BUSCADOR
// -------------------------------------------------------------
const performSearch = async () => {
    const q = searchInput.value.trim();
    if (!q) {
        searchResults.classList.add('hidden');
        return;
    }
    
    try {
        const resultados = await ApiClient.get('/pos/productos', { q }); // Reutilizamos endpoint
        renderSearchResults(resultados);
    } catch (e) {
        console.error(e);
    }
};

function renderSearchResults(productos) {
    searchResults.innerHTML = '';
    if (productos.length === 0) {
        searchResults.innerHTML = '<div class="p-4 text-gray-500 text-center">No se encontraron productos.</div>';
    } else {
        productos.forEach(prod => {
            const item = document.createElement('div');
            item.className = "p-3 border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer flex justify-between items-center transition-colors";
            item.innerHTML = `
                <div>
                    <div class="text-xs text-gray-400 font-mono">${prod.codigoBarras || '-'}</div>
                    <div class="font-bold text-gray-800 dark:text-gray-200">${prod.nombre}</div>
                </div>
                <div class="text-right">
                    <div class="text-sm font-bold text-gray-600 dark:text-gray-400">Stock: ${prod.stock}</div>
                    <div class="text-xs text-gray-400">Costo Ref: ${fmt(prod.costo)}</div>
                </div>
            `;
            item.onclick = () => {
                addToOrder(prod);
                searchInput.value = '';
                searchResults.classList.add('hidden');
                searchInput.focus();
            };
            searchResults.appendChild(item);
        });
    }
    searchResults.classList.remove('hidden');
}

searchInput.addEventListener('input', debounce(performSearch, 300));
document.addEventListener('click', (e) => {
    if(!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
        searchResults.classList.add('hidden');
    }
});

// -------------------------------------------------------------
// ORDEN DE COMPRA (CARRO)
// -------------------------------------------------------------
function addToOrder(prod) {
    const existing = orderItems.find(i => i.idProducto === prod.idProducto);
    if (existing) {
        existing.cantidad += 1;
    } else {
        orderItems.push({
            idProducto: prod.idProducto,
            codigoBarras: prod.codigoBarras,
            nombre: prod.nombre,
            stockActual: prod.stock,
            costoUnitario: prod.costo,
            cantidad: 1
        });
    }
    updateOrderUI();
}

function removeOrder(idProducto) {
    orderItems = orderItems.filter(i => i.idProducto !== idProducto);
    updateOrderUI();
}

function updateItem(idProducto, field, value) {
    const item = orderItems.find(i => i.idProducto === idProducto);
    if(item) {
        const val = parseFloat(value);
        if(!isNaN(val) && val >= 0) {
            item[field] = val;
            updateOrderUI();
        }
    }
}

function updateOrderUI() {
    cartItems.innerHTML = '';
    
    let subtotal = 0;
    let totalItems = 0;
    
    if (orderItems.length === 0) {
        cartEmpty.classList.remove('hidden');
        btnProcesar.disabled = true;
    } else {
        cartEmpty.classList.add('hidden');
        btnProcesar.disabled = !selProveedor.value;
        
        orderItems.forEach(item => {
            const itemSubtotal = item.cantidad * item.costoUnitario;
            subtotal += itemSubtotal;
            totalItems += item.cantidad;
            
            const tr = document.createElement('tr');
            tr.className = "hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors";
            tr.innerHTML = `
                <td class="py-3 px-4 text-sm text-gray-500 font-mono">${item.codigoBarras || '-'}</td>
                <td class="py-3 px-4 font-bold text-gray-800 dark:text-gray-200">${item.nombre}</td>
                <td class="py-3 px-4 text-center font-mono ${item.stockActual <= 5 ? 'text-red-500 font-bold' : 'text-gray-500'}">${item.stockActual}</td>
                <td class="py-3 px-4 text-center">
                    <div class="relative w-24 mx-auto">
                        <span class="absolute left-2 top-1/2 -translate-y-1/2 text-gray-500">$</span>
                        <input type="number" step="0.01" min="0" class="w-full pl-6 pr-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-[#1a1a1a] outline-none focus:border-primary text-right" value="${item.costoUnitario.toFixed(2)}" onchange="updateItem(${item.idProducto}, 'costoUnitario', this.value)">
                    </div>
                </td>
                <td class="py-3 px-4 text-center">
                    <input type="number" step="1" min="1" class="w-20 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-[#1a1a1a] outline-none focus:border-primary text-center font-bold" value="${item.cantidad}" onchange="updateItem(${item.idProducto}, 'cantidad', this.value)">
                </td>
                <td class="py-3 px-4 text-right font-mono font-bold text-gray-800 dark:text-gray-200">${fmt(itemSubtotal)}</td>
                <td class="py-3 px-4 text-center">
                    <button onclick="removeOrder(${item.idProducto})" class="text-red-400 hover:text-red-600 p-2"><i class="fa-solid fa-trash-can"></i></button>
                </td>
            `;
            cartItems.appendChild(tr);
        });
    }
    
    sumItems.textContent = totalItems;
    sumSubtotal.textContent = fmt(subtotal);
    sumTotal.textContent = fmt(subtotal); // No aplicamos impuestos extra para simplificar
}

selProveedor.addEventListener('change', () => {
    if(orderItems.length > 0) btnProcesar.disabled = !selProveedor.value;
});

// -------------------------------------------------------------
// CHECKOUT COMPRAS
// -------------------------------------------------------------
btnProcesar.addEventListener('click', async () => {
    if (orderItems.length === 0 || !selProveedor.value) return;
    
    const idProv = parseInt(selProveedor.value);
    const mTotal = orderItems.reduce((acc, i) => acc + (i.cantidad * i.costoUnitario), 0);
    
    btnProcesar.disabled = true;
    btnProcesar.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Registrando...`;
    
    const payload = {
        idProveedor: idProv,
        montoTotal: mTotal,
        items: orderItems.map(i => ({
            idProducto: i.idProducto,
            cantidad: i.cantidad,
            costoUnitario: i.costoUnitario
        }))
    };
    
    try {
        const res = await ApiClient.post('/compras/registrar', payload);
        showToast(`Orden #${res.idCompra} Registrada. Inventario actualizado.`);
        
        // Reset
        orderItems = [];
        selProveedor.value = '';
        updateOrderUI();
        
    } catch (e) {
        showToast(e.message || "Error al procesar el ingreso", true);
    } finally {
        btnProcesar.disabled = orderItems.length === 0;
        btnProcesar.innerHTML = `<i class="fa-solid fa-truck-ramp-box"></i> PROCESAR INGRESO`;
    }
});

// Arrancar
document.addEventListener('DOMContentLoaded', init);
