/**
 * Motor Reactivo - Compras y Abastecimiento (Refactor Arquitectónico v2)
 */

let orderItems = [];
let proveedores = [];
let sugerenciasOriginales = [];

// DOM Elements
const selProveedor = document.getElementById('select-proveedor');
const fechaActual = document.getElementById('fecha-actual');
const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('search-results');
const searchEmptyState = document.getElementById('search-empty-state');
const cartItems = document.getElementById('cart-items');
const cartEmpty = document.getElementById('cart-empty');
const sumItems = document.getElementById('summary-items');
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
// HUMANIZADOR DE LENGUAJE COMERCIAL
// -------------------------------------------------------------
function humanizarContexto(texto) {
    if (!texto) return "";
    let human = texto;
    human = human.replace(/Quiebre inminente/ig, "Riesgo de perder ventas hoy");
    human = human.replace(/Alto riesgo de quiebre/ig, "Quedan muy pocas unidades");
    human = human.replace(/Alta rentabilidad/ig, "Producto con alto margen de ganancia");
    human = human.replace(/Alta rotación/ig, "Este producto se vende constantemente");
    return human;
}

// -------------------------------------------------------------
// INICIALIZACIÓN Y SUGERENCIAS
// -------------------------------------------------------------
async function init() {
    const today = new Date();
    if(fechaActual) fechaActual.textContent = today.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });
    
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
        
        const data = await ApiClient.get('/compras/sugerencias');
        
        if (data.proveedorSugerido && selProveedor) {
            selProveedor.value = data.proveedorSugerido;
        }
        
        sugerenciasOriginales = data.sugerencias || [];
        renderSugerencias();
        
    } catch (e) {
        console.error("Error inicializando compras", e);
        if(selProveedor) selProveedor.innerHTML = '<option value="">Error cargando datos</option>';
    }
}

function renderSugerencias() {
    const container = document.getElementById('sugerencias-chips');
    if (!container) return;
    
    const sugerenciasActivas = [];
    
    sugerenciasOriginales.forEach(s => {
        const itemEnOrden = orderItems.find(i => i.idProducto === s.idProducto);
        const cantidadYaPedida = itemEnOrden ? itemEnOrden.cantidad : 0;
        const pendiente = s.sugerencia - cantidadYaPedida;
        
        if (pendiente > 0) {
            sugerenciasActivas.push({
                ...s,
                pendiente: pendiente,
                yaPedida: cantidadYaPedida
            });
        }
    });
    
    if (sugerenciasActivas.length === 0) {
        if (sugerenciasOriginales.length > 0 && orderItems.length > 0) {
            container.innerHTML = `
                <div class="p-6 text-center bg-green-50/50 dark:bg-green-900/10 rounded-xl border border-green-200 dark:border-green-800">
                    <i class="fa-solid fa-circle-check text-3xl text-green-600 dark:text-green-400 mb-2"></i>
                    <div class="text-green-800 dark:text-green-300 text-sm font-bold">¡Recomendaciones Cubiertas!</div>
                    <div class="text-gray-600 dark:text-gray-400 text-xs mt-1">Has añadido las cantidades sugeridas por el sistema a tu orden.</div>
                </div>`;
        } else {
            container.innerHTML = `
                <div class="p-6 text-center">
                    <i class="fa-solid fa-mug-hot text-3xl text-indigo-300 dark:text-indigo-500 mb-2"></i>
                    <div class="text-gray-600 dark:text-gray-300 text-sm font-medium">El inventario está estable. No hay urgencias detectadas.</div>
                </div>`;
        }
        return;
    }
    
    container.innerHTML = sugerenciasActivas.map(s => {
        const textoHumanizado = humanizarContexto(s.contexto);
        const stockCritico = s.stockActual <= 5;
        const textoBoton = s.yaPedida > 0 ? `Conviene pedir ${s.pendiente} unid. más` : `Conviene pedir ${s.sugerencia} unid.`;
        
        return `
        <div class="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 hover:shadow-md transition-all relative overflow-hidden group">
            
            <div class="flex justify-between items-start mb-2">
                <div class="font-bold text-gray-900 dark:text-gray-100 text-sm pr-2 leading-tight" title="${s.nombre}">${s.nombre}</div>
                <div class="text-xs font-bold px-2 py-0.5 rounded shrink-0 ${stockCritico ? 'bg-red-100 text-red-700 dark:bg-red-900/60 dark:text-red-200 border border-red-200 dark:border-red-700' : 'bg-orange-100 text-orange-700 dark:bg-orange-900/60 dark:text-orange-200 border border-orange-200 dark:border-orange-700'}">
                    Quedan ${s.stockActual}
                </div>
            </div>
            
            <div class="text-xs text-indigo-700 dark:text-indigo-200 font-semibold mb-1 flex items-start gap-1.5 leading-snug">
                <i class="fa-solid fa-lightbulb mt-0.5 text-indigo-500 dark:text-indigo-300"></i> <span>${textoHumanizado}</span>
            </div>
            <div class="text-xs text-gray-500 dark:text-gray-300 mb-3 ml-4">Demanda: <span class="font-semibold text-gray-700 dark:text-gray-200">${s.velocidadDiaria} u/día</span></div>
            
            <button onclick='addSugerenciaToOrder(${JSON.stringify(s).replace(/'/g, "&#39;")}, ${s.pendiente})' 
                    class="w-full py-2 bg-indigo-50 hover:bg-indigo-600 text-indigo-700 hover:text-white dark:bg-indigo-950 dark:hover:bg-indigo-600 dark:text-indigo-200 dark:hover:text-white border border-indigo-200 dark:border-indigo-800 transition-colors font-bold text-xs rounded-lg flex items-center justify-center gap-2">
                <i class="fa-solid fa-plus"></i> ${textoBoton}
            </button>
        </div>
    `}).join('');
}

function addSugerenciaToOrder(sug, cantidadPedir) {
    addToOrder({
        idProducto: sug.idProducto,
        codigoBarras: sug.codigoBarras,
        nombre: sug.nombre,
        stock: sug.stockActual,
        costo: sug.costo,
        precioLista: sug.precioLista,
        sugerencia: sug.sugerencia,
        contexto: sug.contexto
    }, cantidadPedir || sug.sugerencia);
}

// -------------------------------------------------------------
// BUSCADOR EN COLUMNA 1
// -------------------------------------------------------------
const performSearch = async () => {
    if(!searchInput || !searchResults || !searchEmptyState) return;
    
    const q = searchInput.value.trim();
    if (!q) {
        searchResults.classList.add('hidden');
        searchEmptyState.classList.remove('hidden');
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
                addToOrder(prod, 1);
                searchInput.value = '';
                searchResults.classList.add('hidden');
                searchEmptyState.classList.remove('hidden');
            };
            searchResults.appendChild(item);
        });
    }
    
    searchEmptyState.classList.add('hidden');
    searchResults.classList.remove('hidden');
}

if(searchInput) {
    searchInput.addEventListener('input', debounce(performSearch, 300));
}

// -------------------------------------------------------------
// ORDEN DE COMPRA (CARRO) EN COLUMNA 2
// -------------------------------------------------------------
function addToOrder(prod, cantidad = 1) {
    const existing = orderItems.find(i => i.idProducto === prod.idProducto);
    if (existing) {
        existing.cantidad += cantidad;
    } else {
        orderItems.push({
            idProducto: prod.idProducto,
            codigoBarras: prod.codigoBarras,
            nombre: prod.nombre,
            stockActual: prod.stock,
            costoUnitario: prod.costo || 0.0,
            precioLista: prod.precioLista || 0.0,
            cantidad: cantidad,
            contexto: prod.contexto || '',
            sugerencia: prod.sugerencia || 0
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

function actualizarFraseImpacto() {
    const fraseContainer = document.getElementById('frase-impacto');
    if (!fraseContainer) return;
    
    if (orderItems.length === 0) {
        fraseContainer.textContent = "Evaluando tu inventario... Comienza a armar la orden para ver el impacto comercial.";
        return;
    }
    
    let prodCriticos = orderItems.filter(i => i.contexto !== "").length;
    let frase = `Esta orden actualizará ${orderItems.length} producto(s).`;
    
    if (prodCriticos > 0) {
        frase += ` Con ella, resolverás ${prodCriticos} alertas comerciales.`;
    }
    
    let margenDestruido = orderItems.some(i => i.costoUnitario >= i.precioLista && i.precioLista > 0);
    if (margenDestruido) {
        frase = `<span class="text-red-600 font-bold dark:text-red-400"><i class="fa-solid fa-triangle-exclamation"></i> Alerta: El costo propuesto en algunos artículos anula la ganancia según tu precio de lista actual.</span>`;
        fraseContainer.innerHTML = frase;
        return;
    }
    
    fraseContainer.innerHTML = `<span class="text-indigo-700 dark:text-indigo-400 font-medium"><i class="fa-solid fa-check-circle"></i> ${frase}</span>`;
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
        if(btnProcesar) btnProcesar.disabled = !selProveedor.value;
        
        orderItems.forEach(item => {
            const itemSubtotal = item.cantidad * item.costoUnitario;
            subtotal += itemSubtotal;
            totalItems += item.cantidad;
            
            const isMargenDestruido = item.precioLista > 0 && item.costoUnitario >= item.precioLista;
            const bgClass = isMargenDestruido ? "bg-red-50/50 dark:bg-red-900/10" : "hover:bg-gray-50 dark:hover:bg-gray-800/30";
            const alertIcon = isMargenDestruido ? `<i class="fa-solid fa-triangle-exclamation text-red-500" title="Costo supera o iguala precio de venta"></i>` : '';
            
            const tr = document.createElement('tr');
            tr.className = `${bgClass} transition-colors border-b border-gray-100 dark:border-gray-700/50`;
            tr.innerHTML = `
                <td class="py-3 px-4">
                    <div class="font-bold text-gray-800 dark:text-gray-200 flex items-center gap-2 leading-tight">
                        ${item.nombre} ${alertIcon}
                    </div>
                    <div class="text-[10px] text-gray-400 font-mono mt-0.5">Stock Actual: ${item.stockActual}</div>
                </td>
                <td class="py-3 px-2 text-center w-20">
                    <input type="number" step="1" min="1" class="w-full px-1 py-1.5 border border-gray-300 bg-white dark:border-gray-600 dark:bg-gray-900 rounded focus:border-blue-500 text-center text-sm font-bold" value="${item.cantidad}" onchange="updateItem(${item.idProducto}, 'cantidad', this.value)">
                </td>
                <td class="py-3 px-2 text-center w-28">
                    <div class="relative group">
                        <span class="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400 text-xs">$</span>
                        <input type="number" step="0.01" min="0" class="w-full pl-5 pr-1 py-1.5 border ${isMargenDestruido ? 'border-red-300 bg-red-50 text-red-700 dark:border-red-700 dark:bg-red-900/30' : 'border-gray-300 bg-white dark:border-gray-600 dark:bg-gray-900'} rounded focus:border-blue-500 text-right text-sm transition-colors" value="${item.costoUnitario.toFixed(2)}" onchange="updateItem(${item.idProducto}, 'costoUnitario', this.value)">
                    </div>
                </td>
                <td class="py-3 px-4 text-right font-mono font-bold text-gray-800 dark:text-gray-200 w-24">
                    ${fmt(itemSubtotal)}
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
    
    actualizarFraseImpacto();
    renderSugerencias();
}

if(selProveedor) {
    selProveedor.addEventListener('change', () => {
        if(orderItems.length > 0 && btnProcesar) btnProcesar.disabled = !selProveedor.value;
    });
}

// -------------------------------------------------------------
// CHECKOUT COMPRAS
// -------------------------------------------------------------
if(btnProcesar) {
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
            showToast(`Ingreso de mercadería registrado exitosamente (ID: #${res.idCompra})`);
            
            // Reset
            orderItems = [];
            selProveedor.value = '';
            updateOrderUI();
            init(); // Recargar sugerencias para ver cambios!
            
        } catch (e) {
            showToast(e.message || "Error al procesar el ingreso", true);
        } finally {
            btnProcesar.disabled = orderItems.length === 0;
            btnProcesar.innerHTML = `<i class="fa-solid fa-check-double"></i> Aprobar Orden de Compra`;
        }
    });
}

// Arrancar
document.addEventListener('DOMContentLoaded', init);
