/**
 * Motor Reactivo - POS Inteligente (v5.0)
 */

// Estado (Memoria)
let cart = [];
let mediosPago = [];
let checkoutTimerStart = 0;
let timeToCheckout = 0;
let selectedCliente = null;
let activeCategoryId = null;

let historialPage = 1;
let historialPages = 1;

// DOM Elements - Left Column
const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('search-results');
const searchResultsContainer = document.getElementById('search-results-container');
const categoryChips = document.getElementById('category-chips'); // New

// Tabs & History
const tabVenta = document.getElementById('tab-venta');
const tabHistorial = document.getElementById('tab-historial');
const contentVenta = document.getElementById('content-venta');
const contentHistorial = document.getElementById('content-historial');
const historialBody = document.getElementById('historial-body');
const toastContainer = document.getElementById('toast-container');
const historialPaginationInfo = document.getElementById('historial-pagination-info');
const btnHistorialPrev = document.getElementById('btn-historial-prev');
const btnHistorialNext = document.getElementById('btn-historial-next');

// DOM Elements - Right Column (Cart & Asistente)
const cartItems = document.getElementById('cart-items');
const cartEmpty = document.getElementById('cart-empty');
const summarySubtotal = document.getElementById('summary-subtotal');
const summaryItems = document.getElementById('summary-items');
const summaryTotal = document.getElementById('summary-total');
const selectPago = document.getElementById('select-pago');
const inputPago = document.getElementById('input-pago');
const vueltoContainer = document.getElementById('vuelto-container');
const summaryVuelto = document.getElementById('summary-vuelto');
const btnPreCheckout = document.getElementById('btn-pre-checkout');
const btnClearCart = document.getElementById('btn-clear-cart');
const checkoutLoading = document.getElementById('checkout-loading');

const crossSellItems = document.getElementById('cross-sell-items');
const assistantEmpty = document.getElementById('assistant-empty');
const assistantNoRules = document.getElementById('assistant-no-rules');

// DOM Elements - Cliente
const searchCliente = document.getElementById('search-cliente');
const clienteResults = document.getElementById('cliente-results');
const clienteContext = document.getElementById('cliente-context');
const ctxTicket = document.getElementById('ctx-ticket');
const ctxVisita = document.getElementById('ctx-visita');
const ctxClasificacion = document.querySelector('#ctx-clasificacion span');
const inputClienteId = document.getElementById('selected-cliente-id');



// Formatter
const fmt = (val) => `S/ ${Number(val).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits:2})}`;

const parseLocalDate = (isoString) => {
    if (!isoString) return new Date();
    let s = isoString;
    if (!s.includes('Z') && !/[+-]\d{2}:\d{2}$/.test(s)) {
        s = s + 'Z';
    }
    return new Date(s);
};

// Debounce
function debounce(func, delay = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => { func.apply(this, args); }, delay);
    };
}

// -------------------------------------------------------------
// INICIALIZACIÓN
// -------------------------------------------------------------
async function init() {
    try {
        mediosPago = await ApiClient.get('/pos/medios-pago');
        mediosPago.forEach(mp => {
            const option = document.createElement('option');
            option.value = mp.id;
            option.textContent = mp.nombre;
            selectPago.appendChild(option);
        });
        
        loadCategorias();
        setupTabs();
        setupHistorialPagination();
        loadHistorial(1);
        setupShortcuts();

        // -------------------------------------------------------------
        // DEEP LINKING: Interceptar parámetros URL
        // -------------------------------------------------------------
        const params = new URLSearchParams(window.location.search);
        if (params.get('tab') === 'historial' && tabHistorial) {
            tabHistorial.click();
        } else if (tabVenta) {
            tabVenta.click();
        }

        const selectClientId = params.get('select_client_id');
        if (selectClientId) {
            // Cargar clientes en background para auto-seleccionar
            ApiClient.get('/actores/clientes').then(clientes => {
                const c = clientes.find(x => x.idCliente == selectClientId);
                if (c) {
                    // Adaptar campos al formato esperado por el POS
                    c.frecuencia_compra = c.frecuencia;
                    c.ultima_compra = c.ultima_transaccion;
                    
                    let clas = "Nuevo";
                    if (c.frecuencia >= 10) clas = "VIP";
                    else if (c.frecuencia >= 3) clas = "Frecuente";
                    else if (c.frecuencia > 0) clas = "Regular";
                    c.clasificacion = clas;

                    selectClient(c);
                }
            }).catch(() => {});
        }

    } catch (e) {
        // Inicialización completada con manejo silencioso
    }
}

function setupShortcuts() {
    document.addEventListener('keydown', (e) => {
        if (e.key === 'F2') {
            e.preventDefault();
            searchInput.focus();
        } else if (e.key === 'F4') {
            e.preventDefault();
            searchCliente.focus();
        } else if (e.key === 'F8') {
            e.preventDefault();
            if (!btnPreCheckout.disabled) {
                btnPreCheckout.click();
            }
        } else if (e.key === 'Escape') {
            e.preventDefault();
            if (cart.length > 0) {
                if(confirm("¿Vaciar ticket?")) clearCart();
            }
        }
    });
}

// -------------------------------------------------------------
// UI & TABS & TOAST & CATEGORÍAS & HISTORIAL
// -------------------------------------------------------------
function setupTabs() {
    if (!tabVenta || !tabHistorial) return;
    tabVenta.addEventListener('click', () => {
        tabVenta.classList.add('text-primary', 'border-primary');
        tabVenta.classList.remove('text-gray-500', 'border-transparent');
        tabHistorial.classList.add('text-gray-500', 'border-transparent');
        tabHistorial.classList.remove('text-primary', 'border-primary');
        contentVenta.classList.remove('hidden');
        contentHistorial.classList.add('hidden');
        if (searchInput) searchInput.focus();
    });

    tabHistorial.addEventListener('click', () => {
        tabHistorial.classList.add('text-primary', 'border-primary');
        tabHistorial.classList.remove('text-gray-500', 'border-transparent');
        tabVenta.classList.add('text-gray-500', 'border-transparent');
        tabVenta.classList.remove('text-primary', 'border-primary');
        contentHistorial.classList.remove('hidden');
        contentVenta.classList.add('hidden');
        loadHistorial();
    });
}

function showToast(message, type = 'success') {
    if (!toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `px-4 py-3 rounded-lg shadow-lg font-bold text-sm transform transition-all duration-300 translate-y-4 opacity-0 flex items-center gap-2 ${
        type === 'success' ? 'bg-green-500 text-white' : 'bg-red-500 text-white'
    }`;
    toast.innerHTML = type === 'success' ? `<i class="fa-solid fa-check-circle"></i> ${message}` : `<i class="fa-solid fa-exclamation-circle"></i> ${message}`;
    
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.remove('translate-y-4', 'opacity-0');
    }, 10);
    
    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-x-4');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

async function loadCategorias() {
    try {
        const categorias = await ApiClient.get('/pos/categorias');
        if (!categoryChips) return;
        categoryChips.innerHTML = '';
        
        // Chip "Todos"
        const chipTodos = document.createElement('button');
        chipTodos.className = "category-pill active px-3 py-1 bg-primary text-white rounded-full text-xs font-bold transition-colors shrink-0 shadow-sm";
        chipTodos.textContent = "Todos";
        chipTodos.onclick = () => selectCategory(null, chipTodos);
        categoryChips.appendChild(chipTodos);
        
        categorias.forEach(cat => {
            const pill = document.createElement('button');
            pill.className = "category-pill px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full text-xs font-medium hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors shrink-0";
            pill.textContent = cat.nombre;
            pill.onclick = () => selectCategory(cat.id, pill);
            categoryChips.appendChild(pill);
        });
    } catch(e) {
        // Manejo silencioso de carga de categorías
    }
}

function selectCategory(id, el) {
    activeCategoryId = id;
    document.querySelectorAll('.category-pill').forEach(p => {
        p.className = "category-pill px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full text-xs font-medium hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors shrink-0";
    });
    if (el) {
        el.className = "category-pill active px-3 py-1 bg-primary text-white rounded-full text-xs font-bold transition-colors shrink-0 shadow-sm";
    }
    performSearch();
}

async function loadHistorial(page = 1) {
    try {
        const res = await ApiClient.get('/pos/historial', { page, size: 10 });
        if (!historialBody) return;
        historialBody.innerHTML = '';
        
        const ventas = res.items || [];
        historialPage = res.page || 1;
        historialPages = res.pages || 1;
        
        ventas.forEach(v => {
            const tr = document.createElement('tr');
            tr.className = "hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors group";
            tr.innerHTML = `
                <td class="py-2.5 px-3 font-mono font-bold text-primary text-sm">#${v.idVenta}</td>
                <td class="py-2.5 px-3 text-sm text-gray-600 dark:text-gray-400">${parseLocalDate(v.fecha).toLocaleString('es-PE')}</td>
                <td class="py-2.5 px-3 text-sm font-medium text-gray-800 dark:text-gray-200">${v.cliente}</td>
                <td class="py-2.5 px-3 text-sm text-center font-bold text-gray-600 dark:text-gray-300">${v.articulos}</td>
                <td class="py-2.5 px-3 text-sm font-bold text-right text-gray-900 dark:text-gray-100 font-mono">${fmt(v.montoTotal)}</td>
                <td class="py-2.5 px-3 text-center">
                    <button onclick="openDetalleVenta(${v.idVenta})" class="px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-900/30 dark:hover:bg-indigo-900/50 text-indigo-600 dark:text-indigo-300 rounded text-xs font-bold transition-colors inline-flex items-center gap-1 shadow-sm">
                        <i class="fa-solid fa-eye"></i> Detalle
                    </button>
                </td>
            `;
            historialBody.appendChild(tr);
        });

        if (historialPaginationInfo) {
            historialPaginationInfo.textContent = `Página ${historialPage} de ${historialPages || 1}`;
        }
        if (btnHistorialPrev) {
            btnHistorialPrev.disabled = (historialPage <= 1);
        }
        if (btnHistorialNext) {
            btnHistorialNext.disabled = (historialPage >= historialPages);
        }
    } catch(e) {
        // Manejo silencioso de error en historial
    }
}

function setupHistorialPagination() {
    if (btnHistorialPrev) {
        btnHistorialPrev.addEventListener('click', () => {
            if (historialPage > 1) {
                loadHistorial(historialPage - 1);
            }
        });
    }
    if (btnHistorialNext) {
        btnHistorialNext.addEventListener('click', () => {
            if (historialPage < historialPages) {
                loadHistorial(historialPage + 1);
            }
        });
    }
}

async function openDetalleVenta(idVenta) {
    const modal = document.getElementById('detalleVentaModal');
    if (!modal) return;
    
    try {
        const data = await ApiClient.get(`/pos/historial/${idVenta}`);
        
        document.getElementById('modal-detalle-titulo').textContent = `Ticket #${data.idVenta}`;
        document.getElementById('modal-detalle-cliente').textContent = data.cliente;
        document.getElementById('modal-detalle-fecha').textContent = parseLocalDate(data.fecha).toLocaleString('es-PE');
        document.getElementById('modal-detalle-pago').textContent = data.medioPago;
        document.getElementById('modal-detalle-utilidad').textContent = fmt(data.utilidad);
        document.getElementById('modal-detalle-total').textContent = fmt(data.montoTotal);
        
        const itemsBody = document.getElementById('modal-detalle-items');
        itemsBody.innerHTML = '';
        
        data.detalles.forEach(d => {
            const tr = document.createElement('tr');
            tr.className = "hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors";
            tr.innerHTML = `
                <td class="p-2.5 font-bold text-gray-800 dark:text-gray-200">${d.nombreProducto}</td>
                <td class="p-2.5 text-center font-mono">${d.cantidad}</td>
                <td class="p-2.5 text-right font-mono text-gray-600 dark:text-gray-400">${fmt(d.precioUnitario)}</td>
                <td class="p-2.5 text-right font-mono font-bold text-gray-800 dark:text-gray-200">${fmt(d.subtotal)}</td>
            `;
            itemsBody.appendChild(tr);
        });
        
        modal.classList.remove('hidden');
        setTimeout(() => {
            modal.classList.remove('opacity-0');
            modal.querySelector('div').classList.remove('scale-95');
        }, 10);
        
    } catch (e) {
        showToast(e.message || "Error al cargar detalle de venta", "error");
    }
}

function closeDetalleModal() {
    const modal = document.getElementById('detalleVentaModal');
    if (!modal) return;
    modal.classList.add('opacity-0');
    modal.querySelector('div').classList.add('scale-95');
    setTimeout(() => modal.classList.add('hidden'), 300);
}


let currentSearchProducts = [];

const performSearch = async () => {
    const q = searchInput.value.trim();
    if (!q && !activeCategoryId) {
        searchResultsContainer.classList.add('hidden');
        return;
    }
    
    try {
        const params = {};
        if (q) params.q = q;
        if (activeCategoryId) params.categoria = activeCategoryId;
        const resultados = await ApiClient.get('/pos/productos', params);
        currentSearchProducts = resultados;
        renderSearchResults(resultados);
    } catch (e) {
        // Manejo silencioso de búsqueda
    }
};

function renderSearchResults(productos) {
    searchResults.innerHTML = '';
    
    if (productos.length === 0) {
        searchResults.innerHTML = '<div class="text-gray-500 text-center py-4 text-sm">No se encontraron resultados.</div>';
    } else {
        productos.forEach(prod => {
            let stockColor = "bg-green-500";
            if(prod.estado_stock === "Crítico") stockColor = "bg-red-500 animate-pulse";
            else if(prod.estado_stock === "Bajo") stockColor = "bg-yellow-400";

            const row = document.createElement('div');
            row.className = "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-2.5 cursor-pointer hover:border-primary hover:shadow-md transition-all flex items-center justify-between gap-3 group";
            row.innerHTML = `
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-0.5">
                        <span class="text-[10px] text-gray-400 font-mono">${prod.codigoBarras || prod.idProducto}</span>
                    </div>
                    <div class="font-bold text-sm text-gray-800 dark:text-gray-200 truncate group-hover:text-primary transition-colors" title="${prod.nombre}">${prod.nombre}</div>
                </div>
                <div class="flex items-center gap-2 shrink-0">
                    <button onclick="event.stopPropagation(); openProductoDetailModalByObj(${prod.idProducto})" class="p-1 text-gray-400 hover:text-primary text-xs" title="Ver ficha técnica de producto">
                        <i class="fa-solid fa-circle-info"></i>
                    </button>
                    <div class="text-xs text-gray-500 flex items-center gap-1 font-bold bg-gray-50 dark:bg-gray-700/50 px-2 py-1 rounded">
                        <span class="w-2 h-2 rounded-full ${stockColor}"></span> 
                        ${prod.stock} un.
                    </div>
                    <div class="text-primary font-bold text-sm font-mono">${fmt(prod.precio)}</div>
                    <button class="bg-gray-100 dark:bg-gray-700 group-hover:bg-primary group-hover:text-white text-gray-600 dark:text-gray-300 font-bold px-2.5 py-1 rounded text-xs transition-colors flex items-center gap-1 shadow-sm">
                        <i class="fa-solid fa-plus text-[10px]"></i>
                    </button>
                </div>
            `;
            row.onclick = () => addToCart(prod);
            searchResults.appendChild(row);
        });
    }
    searchResultsContainer.classList.remove('hidden');
}

searchInput.addEventListener('input', debounce(performSearch, 300));
searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        const cards = searchResults.children;
        if (cards.length > 0 && !cards[0].classList.contains('col-span-full')) {
            cards[0].click();
        }
    }
});

// -------------------------------------------------------------
// BUSCADOR DE CLIENTES
// -------------------------------------------------------------
const searchClients = async () => {
    const q = searchCliente.value.trim();
    if (!q) {
        clienteResults.classList.add('hidden');
        return;
    }
    try {
        const clientes = await ApiClient.get('/pos/clientes', { q });
        renderClientResults(clientes);
    } catch (e) {
        // Manejo silencioso de búsqueda de clientes
    }
};

function renderClientResults(clientes) {
    clienteResults.innerHTML = '';
    if (clientes.length === 0) {
        const queryVal = searchCliente.value.trim();
        clienteResults.innerHTML = `
            <div class="p-3 text-center">
                <p class="text-xs text-gray-500 mb-2">Cliente no encontrado</p>
                <button onclick="openQuickClienteModal('${queryVal.replace(/'/g, "\\'")}')" class="px-3 py-1.5 bg-primary text-white text-xs font-bold rounded-lg hover:bg-blue-600 transition-colors shadow-sm inline-flex items-center gap-1">
                    <i class="fa-solid fa-user-plus"></i> Registrar Cliente Rápido
                </button>
            </div>
        `;
    } else {
        clientes.forEach(c => {
            const item = document.createElement('div');
            item.className = "p-3 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer border-b border-gray-100 dark:border-gray-700 last:border-0";
            item.innerHTML = `
                <div class="font-bold text-sm text-gray-800 dark:text-gray-200">${c.nombres} ${c.apellidos}</div>
                <div class="text-xs text-gray-500 font-mono">DNI: ${c.numeroDocumento}</div>
            `;
            item.onclick = () => selectClient(c);
            clienteResults.appendChild(item);
        });
    }
    clienteResults.classList.remove('hidden');
}

function openQuickClienteModal(prefillValue = '') {
    const modal = document.getElementById('quickClienteModal');
    if (!modal) return;
    
    const dniInput = document.getElementById('quick-cli-dni');
    const nombresInput = document.getElementById('quick-cli-nombres');
    const apellidosInput = document.getElementById('quick-cli-apellidos');
    
    // Simplificado: Limpiar campos o rellenar de forma directa y básica
    dniInput.value = '';
    nombresInput.value = '';
    apellidosInput.value = '';
    
    if (prefillValue) {
        if (/^\d+$/.test(prefillValue)) {
            dniInput.value = prefillValue;
        } else {
            nombresInput.value = prefillValue;
        }
    }
    
    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        modal.querySelector('div').classList.remove('scale-95');
        if (!dniInput.value) {
            dniInput.focus();
        } else {
            nombresInput.focus();
        }
    }, 10);
}

function closeQuickClienteModal() {
    const modal = document.getElementById('quickClienteModal');
    if (!modal) return;
    modal.classList.add('opacity-0');
    modal.querySelector('div').classList.add('scale-95');
    setTimeout(() => modal.classList.add('hidden'), 300);
}

async function handleQuickClienteSubmit(e) {
    e.preventDefault();
    const numeroDocumento = document.getElementById('quick-cli-dni').value.trim();
    const nombres = document.getElementById('quick-cli-nombres').value.trim();
    const apellidos = document.getElementById('quick-cli-apellidos').value.trim();
    
    if (!numeroDocumento || !nombres || !apellidos) {
        showToast("Por favor completa DNI, Nombres y Apellidos", "error");
        return;
    }
    
    try {
        const cliente = await ApiClient.post('/pos/clientes', {
            numeroDocumento,
            nombres,
            apellidos
        });
        
        closeQuickClienteModal();
        selectClient(cliente);
        showToast(`Cliente ${cliente.nombres} ${cliente.apellidos} registrado exitosamente.`);
        
    } catch(err) {
        showToast(err.message || "Error al registrar cliente", "error");
    }
}

function selectClient(cliente) {
    selectedCliente = cliente;
    searchCliente.value = `${cliente.nombres} ${cliente.apellidos}`;
    inputClienteId.value = cliente.idCliente;
    clienteResults.classList.add('hidden');
    
    // Inyectar contexto
    ctxTicket.textContent = fmt(cliente.ticket_promedio);
    if(cliente.ultima_compra) {
        ctxVisita.textContent = parseLocalDate(cliente.ultima_compra).toLocaleDateString('es-PE');
    } else {
        ctxVisita.textContent = "Nuevo";
    }
    
    if(ctxClasificacion) {
        ctxClasificacion.textContent = `${cliente.clasificacion} (${cliente.frecuencia_compra} compras)`;
    }

    clienteContext.classList.remove('hidden');
    fetchContextoComercial(); // Actualizar contexto global
}

searchCliente.addEventListener('input', debounce(searchClients, 300));
// Hide results when clicking outside
document.addEventListener('click', (e) => {
    if (!searchCliente.contains(e.target) && !clienteResults.contains(e.target)) {
        clienteResults.classList.add('hidden');
    }
});

// -------------------------------------------------------------
// MOTOR REACTIVO DEL CARRITO
// -------------------------------------------------------------
function addToCart(producto) {
    // Iniciar cronómetro si es el primer item
    if (cart.length === 0) {
        checkoutTimerStart = Date.now();
    }

    const existingIndex = cart.findIndex(item => item.idProducto === producto.idProducto);
    
    if (existingIndex >= 0) {
        if (cart[existingIndex].cantidad < producto.stock) {
            cart[existingIndex].cantidad += 1;
        } else {
            alert(`Stock máximo alcanzado para: ${producto.nombre}`);
        }
    } else {
        cart.push({
            ...producto,
            cantidad: 1
        });
    }
    
    
    searchInput.value = '';
    searchResultsContainer.classList.add('hidden');
    searchInput.focus();
    
    updateCartUI();
    fetchContextoComercial();
}

function removeFromCart(idProducto) {
    cart = cart.filter(item => item.idProducto !== idProducto);
    updateCartUI();
    fetchContextoComercial();
    if (cart.length === 0) checkoutTimerStart = 0;
}

function changeQuantity(idProducto, delta) {
    const item = cart.find(i => i.idProducto === idProducto);
    if (!item) return;
    
    const newQty = item.cantidad + delta;
    if (newQty <= 0) {
        removeFromCart(idProducto);
    } else if (newQty <= item.stock) {
        item.cantidad = newQty;
        updateCartUI();
    } else {
        alert("Stock insuficiente");
    }
}

function getCartTotals() {
    let subtotal = 0;
    let itemsCount = 0;
    let expectedUtilidad = 0;
    
    cart.forEach(item => {
        subtotal += (item.precio * item.cantidad);
        itemsCount += item.cantidad;
        expectedUtilidad += ((item.precio - item.costo) * item.cantidad);
    });
    
    return { subtotal, itemsCount, total: subtotal, utilidad: expectedUtilidad };
}

function updateCartUI() {
    cartItems.innerHTML = '';
    
    if (cart.length === 0) {
        cartEmpty.classList.remove('hidden');
        btnPreCheckout.disabled = true;
    } else {
        cartEmpty.classList.add('hidden');
        btnPreCheckout.disabled = false;
        
        cart.forEach(item => {
            const li = document.createElement('li');
            li.className = "bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-lg p-3 flex justify-between items-center shadow-sm";
            
            li.innerHTML = `
                <div class="flex-1 min-w-0 pr-2">
                    <h4 class="font-bold text-sm text-gray-800 dark:text-gray-200 truncate">${item.nombre}</h4>
                    <div class="text-xs text-gray-500">${fmt(item.precio)} x ${item.cantidad}</div>
                </div>
                
                <div class="flex items-center gap-3 shrink-0">
                    <div class="flex items-center bg-gray-100 dark:bg-gray-700 rounded text-sm">
                        <button onclick="changeQuantity(${item.idProducto}, -1)" class="w-7 h-7 flex items-center justify-center hover:bg-gray-200 dark:hover:bg-gray-600 rounded-l transition-colors"><i class="fa-solid fa-minus text-xs"></i></button>
                        <span class="w-6 text-center font-mono font-bold">${item.cantidad}</span>
                        <button onclick="changeQuantity(${item.idProducto}, 1)" class="w-7 h-7 flex items-center justify-center hover:bg-gray-200 dark:hover:bg-gray-600 rounded-r transition-colors"><i class="fa-solid fa-plus text-xs"></i></button>
                    </div>
                    
                    <div class="font-bold text-right w-16 font-mono text-sm">${fmt(item.precio * item.cantidad)}</div>
                    
                    <button onclick="removeFromCart(${item.idProducto})" class="text-red-400 hover:text-red-600 p-2 transition-colors">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>
            `;
            cartItems.appendChild(li);
        });
    }
    
    const totals = getCartTotals();
    summarySubtotal.textContent = fmt(totals.subtotal);
    summaryItems.textContent = totals.itemsCount;
    summaryTotal.textContent = fmt(totals.total);
    
    calculateVuelto();
}

function clearCart() {
    cart = [];
    inputPago.value = '';
    searchCliente.value = '';
    inputClienteId.value = '';
    selectedCliente = null;
    clienteContext.classList.add('hidden');
    checkoutTimerStart = 0;
    updateCartUI();
    fetchContextoComercial();
}

btnClearCart.addEventListener('click', () => {
    if(confirm("¿Estás seguro de vaciar el ticket?")) clearCart();
});

// -------------------------------------------------------------
// ASISTENTE COMERCIAL (ANALIZAR TICKET)
// -------------------------------------------------------------
async function fetchContextoComercial() {
    if (cart.length === 0) {
        assistantEmpty.classList.remove('hidden');
        assistantNoRules.classList.add('hidden');
        crossSellItems.classList.add('hidden');
        return;
    }
    
    const carrito_ids = cart.map(i => i.idProducto);
    const idCliente = inputClienteId.value ? parseInt(inputClienteId.value) : null;
    
    try {
        const contexto = await ApiClient.post('/pos/analizar-ticket', { carrito_ids, idCliente });
        
        if (contexto.cross_sell && contexto.cross_sell.length > 0) {
            assistantEmpty.classList.add('hidden');
            assistantNoRules.classList.add('hidden');
            crossSellItems.classList.remove('hidden');
            crossSellItems.innerHTML = '';
            
            contexto.cross_sell.forEach(sug => {
                const just = sug.justificacion;
                const item = document.createElement('div');
                
                const pctConfianza = Math.round((just.confianza || 0.75) * 100);
                const badgeText = "Se compra junto";
                const badgeClass = "text-indigo-600 bg-indigo-50 dark:text-indigo-400 dark:bg-indigo-900/30";
                const borderClass = "border-indigo-400";
                
                item.className = `bg-white dark:bg-gray-800 border-l-4 ${borderClass} rounded-lg p-3 w-full shadow-sm cursor-pointer hover:shadow-md hover:border-primary transition-all group relative`;
                
                item.title = "Añadir sugerencia al Ticket";
                
                item.onclick = async () => {
                    const detail = await ApiClient.get('/pos/productos', { q: sug.idProducto.toString() });
                    if(detail.length > 0) addToCart(detail[0]);
                };
                
                item.innerHTML = `
                    <div class="flex justify-between items-start mb-1.5">
                        <div class="text-[10px] font-bold px-1.5 py-0.5 rounded flex items-center gap-1 ${badgeClass}">${badgeText}</div>
                        <div class="text-[9px] text-gray-400 uppercase font-medium">${sug.tipo_recomendacion}</div>
                    </div>
                    <div class="font-bold text-sm truncate text-gray-800 dark:text-gray-100" title="${sug.nombre}">${sug.nombre}</div>
                    <div class="text-[11px] text-gray-500 line-clamp-2 mt-1 mb-1 border-b border-gray-100 dark:border-gray-700 pb-1.5">${just.texto}</div>
                    <div class="text-[10px] font-semibold text-indigo-600 dark:text-indigo-400 mb-2">${pctConfianza}% de las ventas incluyen este producto</div>
                    <div class="flex justify-between items-center mt-1">
                        <span class="font-mono text-primary font-bold text-sm">${fmt(sug.precio)}</span>
                        <button class="bg-gray-100 dark:bg-gray-700 group-hover:bg-primary group-hover:text-white text-gray-600 dark:text-gray-300 font-bold px-3 py-1 rounded text-xs transition-colors flex items-center gap-1 shadow-sm">
                            <i class="fa-solid fa-plus text-[10px]"></i> Añadir
                        </button>
                    </div>
                `;
                crossSellItems.appendChild(item);
            });
        } else {
            assistantEmpty.classList.add('hidden');
            crossSellItems.classList.add('hidden');
            assistantNoRules.classList.remove('hidden');
        }
    } catch (e) {
        // Manejo silencioso de contexto comercial
    }
}

// -------------------------------------------------------------
// CHECKOUT & VUELTO (SILENT)
// -------------------------------------------------------------
function calculateVuelto() {
    const pago = parseFloat(inputPago.value);
    const total = getCartTotals().total;
    
    if (!isNaN(pago) && pago > 0) {
        vueltoContainer.classList.remove('hidden');
        const vuelto = pago - total;
        if (vuelto >= 0) {
            summaryVuelto.textContent = fmt(vuelto);
            summaryVuelto.className = "text-xl font-bold text-green-400 font-mono";
            btnPreCheckout.disabled = false;
        } else {
            summaryVuelto.textContent = "Faltante";
            summaryVuelto.className = "text-xl font-bold text-red-500 font-mono";
            btnPreCheckout.disabled = true;
        }
    } else {
        vueltoContainer.classList.add('hidden');
        btnPreCheckout.disabled = cart.length === 0;
    }
}

inputPago.addEventListener('input', calculateVuelto);

// Ejecuta Check-out al Backend de forma Silenciosa
btnPreCheckout.addEventListener('click', async () => {
    if (cart.length === 0) return;
    const totals = getCartTotals();
    const pagoIngresado = parseFloat(inputPago.value);
    
    if (!isNaN(pagoIngresado) && pagoIngresado > 0 && pagoIngresado < totals.total) {
        showToast("El monto ingresado es menor al total.", "error");
        return;
    }

    checkoutLoading.classList.remove('hidden');
    
    const payload = {
        items: cart.map(i => ({
            idProducto: i.idProducto,
            cantidad: i.cantidad,
            precioUnitario: i.precio,
            costoUnitario: i.costo
        })),
        idMedioPago: parseInt(selectPago.value),
        montoTotal: totals.total,
        idCliente: inputClienteId.value ? parseInt(inputClienteId.value) : null
    };
    
    try {
        const response = await ApiClient.post('/pos/checkout', payload);
        checkoutLoading.classList.add('hidden');
        
        showToast(`Ticket #${response.idVenta} procesado exitosamente.`);

        if (response.productos_afectados && response.productos_afectados.length > 0) {
            response.productos_afectados.forEach(prod => {
                showToast(`Venta completada. Stock actual de ${prod.nombre}: ${prod.stock_actual} un.`);
            });
        }

        clearCart();
        searchInput.focus();
        
    } catch (e) {
        checkoutLoading.classList.add('hidden');
        showToast(e.message || "Error procesando la venta", "error");
    }
});

// Arrancar
document.addEventListener('DOMContentLoaded', init);

// -------------------------------------------------------------
// MODALES BAJO DEMANDA (CLIENTE & PRODUCTO)
// -------------------------------------------------------------
function openClienteDetailModal() {
    if (!selectedCliente) {
        showToast("Selecciona un cliente primero para ver su ficha", "error");
        return;
    }
    const modal = document.getElementById('clienteDetailModal');
    if (!modal) return;

    document.getElementById('cli-modal-nombre').textContent = `${selectedCliente.nombres} ${selectedCliente.apellidos}`;
    document.getElementById('cli-modal-dni').textContent = `DNI: ${selectedCliente.numeroDocumento || '--'}`;
    document.getElementById('cli-modal-badge').textContent = selectedCliente.clasificacion || 'Regular';
    document.getElementById('cli-modal-frecuencia').textContent = `${selectedCliente.frecuencia_compra || 0} compras`;
    document.getElementById('cli-modal-ticket').textContent = fmt(selectedCliente.ticket_promedio || 0);
    document.getElementById('cli-modal-visita').textContent = selectedCliente.ultima_compra ? parseLocalDate(selectedCliente.ultima_compra).toLocaleDateString('es-PE') : 'Nueva visita';
    
    const totalComprado = (selectedCliente.frecuencia_compra || 0) * (selectedCliente.ticket_promedio || 0);
    document.getElementById('cli-modal-total-comprado').textContent = fmt(totalComprado);
    document.getElementById('cli-modal-favoritos').textContent = "General";

    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        modal.querySelector('div').classList.remove('scale-95');
    }, 10);
}

function closeClienteDetailModal() {
    const modal = document.getElementById('clienteDetailModal');
    if (!modal) return;
    modal.classList.add('opacity-0');
    modal.querySelector('div').classList.add('scale-95');
    setTimeout(() => modal.classList.add('hidden'), 300);
}

function openProductoDetailModalByObj(idProducto) {
    const prod = currentSearchProducts.find(p => p.idProducto === idProducto);
    if (prod) openProductoDetailModal(prod);
}

function openProductoDetailModal(prod) {
    const modal = document.getElementById('productoDetailModal');
    if (!modal) return;

    document.getElementById('prod-modal-nombre').textContent = prod.nombre;
    document.getElementById('prod-modal-codigo').textContent = `Código: ${prod.codigoBarras || prod.idProducto}`;
    document.getElementById('prod-modal-stock').textContent = `${prod.stock} un.`;
    document.getElementById('prod-modal-costo').textContent = fmt(prod.costo || 0);
    document.getElementById('prod-modal-margen').textContent = `${Math.round(prod.margen || 0)}%`;
    
    let abcClass = "Clase A";
    if (prod.margen < 20) abcClass = "Clase C";
    else if (prod.margen < 40) abcClass = "Clase B";
    document.getElementById('prod-modal-abc').textContent = abcClass;
    
    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        modal.querySelector('div').classList.remove('scale-95');
    }, 10);
}

function closeProductoDetailModal() {
    const modal = document.getElementById('productoDetailModal');
    if (!modal) return;
    modal.classList.add('opacity-0');
    modal.querySelector('div').classList.add('scale-95');
    setTimeout(() => modal.classList.add('hidden'), 300);
}
