/**
 * Motor Reactivo - POS Inteligente (v5.0)
 */

// Estado (Memoria)
let cart = [];
let mediosPago = [];
let checkoutTimerStart = 0;
let timeToCheckout = 0;
let selectedCliente = null;

// DOM Elements - Left Column
const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('search-results');
const searchResultsContainer = document.getElementById('search-results-container');
const recentItemsContainer = document.getElementById('recent-items');

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

// DOM Elements - Modales
const preCheckoutModal = document.getElementById('preCheckoutModal');
const modalPreItems = document.getElementById('modal-pre-items');
const modalPreTotal = document.getElementById('modal-pre-total');
const modalPreUtilidad = document.getElementById('modal-pre-utilidad');
const btnConfirmCheckout = document.getElementById('btn-confirm-checkout');

const postCheckoutModal = document.getElementById('postCheckoutModal');
const modalPostTicket = document.getElementById('modal-post-ticket');
const modalPostTiempo = document.getElementById('modal-post-tiempo');
const modalPostUtilidad = document.getElementById('modal-post-utilidad');

// Formatter
const fmt = (val) => `$${Number(val).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits:2})}`;

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
        loadRecentItems();
        setupShortcuts();
    } catch (e) {
        console.error("Error cargando inicio:", e);
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
                openPreCheckout();
            }
        } else if (e.key === 'Escape') {
            e.preventDefault();
            if (!preCheckoutModal.classList.contains('hidden')) {
                closePreCheckout();
            } else if (cart.length > 0) {
                if(confirm("¿Vaciar ticket?")) clearCart();
            }
        }
    });
}

// -------------------------------------------------------------
// PRODUCTOS RECIENTES (LOCALSTORAGE)
// -------------------------------------------------------------
function saveRecentItem(producto) {
    let recents = JSON.parse(localStorage.getItem('pos_recent_items') || '[]');
    recents = recents.filter(r => r.idProducto !== producto.idProducto);
    recents.unshift({ idProducto: producto.idProducto, nombre: producto.nombre });
    if (recents.length > 5) recents.pop();
    localStorage.setItem('pos_recent_items', JSON.stringify(recents));
    loadRecentItems();
}

function loadRecentItems() {
    const recents = JSON.parse(localStorage.getItem('pos_recent_items') || '[]');
    // Eliminar las pills anteriores
    const pills = recentItemsContainer.querySelectorAll('.recent-pill');
    pills.forEach(p => p.remove());
    
    recents.forEach(item => {
        const pill = document.createElement('button');
        pill.className = "recent-pill shrink-0 px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full text-xs font-medium hover:bg-primary hover:text-white transition-colors truncate max-w-[120px]";
        pill.textContent = item.nombre;
        pill.onclick = async () => {
            const res = await ApiClient.get('/pos/productos', { q: item.idProducto.toString() });
            if (res.length > 0) addToCart(res[0]);
        };
        recentItemsContainer.appendChild(pill);
    });
}

// -------------------------------------------------------------
// BUSCADOR DE PRODUCTOS E INTELIGENCIA
// -------------------------------------------------------------
const performSearch = async () => {
    const q = searchInput.value.trim();
    if (!q) {
        searchResultsContainer.classList.add('hidden');
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
        searchResults.innerHTML = '<div class="text-gray-500 text-center py-4 text-sm">No se encontraron resultados.</div>';
    } else {
        productos.forEach(prod => {
            let stockColor = "bg-green-500";
            if(prod.estado_stock === "Crítico") stockColor = "bg-red-500 animate-pulse";
            else if(prod.estado_stock === "Bajo") stockColor = "bg-yellow-400";

            let margenBadge = '';
            if (prod.margen >= 40) {
                margenBadge = `<span class="bg-green-100 text-green-700 text-[10px] px-1.5 py-0.5 rounded font-bold">⭐ Alta Rentabilidad</span>`;
            }

            const row = document.createElement('div');
            row.className = "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-2.5 cursor-pointer hover:border-primary hover:shadow-md transition-all flex items-center justify-between gap-3 group";
            row.innerHTML = `
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-0.5">
                        <span class="text-[10px] text-gray-400 font-mono">${prod.codigoBarras || prod.idProducto}</span>
                        ${margenBadge}
                    </div>
                    <div class="font-bold text-sm text-gray-800 dark:text-gray-200 truncate group-hover:text-primary transition-colors" title="${prod.nombre}">${prod.nombre}</div>
                </div>
                <div class="flex items-center gap-3 shrink-0">
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
        console.error("Error buscando clientes", e);
    }
};

function renderClientResults(clientes) {
    clienteResults.innerHTML = '';
    if (clientes.length === 0) {
        clienteResults.innerHTML = '<div class="p-3 text-sm text-gray-500 text-center">No encontrado.</div>';
    } else {
        clientes.forEach(c => {
            const item = document.createElement('div');
            item.className = "p-3 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer border-b border-gray-100 dark:border-gray-700 last:border-0";
            item.innerHTML = `
                <div class="font-bold text-sm">${c.nombres} ${c.apellidos}</div>
                <div class="text-xs text-gray-500 font-mono">${c.numeroDocumento}</div>
            `;
            item.onclick = () => selectClient(c);
            clienteResults.appendChild(item);
        });
    }
    clienteResults.classList.remove('hidden');
}

function selectClient(cliente) {
    selectedCliente = cliente;
    searchCliente.value = `${cliente.nombres} ${cliente.apellidos}`;
    inputClienteId.value = cliente.idCliente;
    clienteResults.classList.add('hidden');
    
    // Inyectar contexto
    ctxTicket.textContent = fmt(cliente.ticket_promedio);
    if(cliente.ultima_compra) {
        ctxVisita.textContent = new Date(cliente.ultima_compra).toLocaleDateString();
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
    
    saveRecentItem(producto);
    
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
                
                const isHighlyRecommended = just.confianza >= 0.70;
                const badgeText = isHighlyRecommended ? "🔥 Muy Recomendado" : "👍 Buen Complemento";
                const badgeClass = isHighlyRecommended ? "text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-900/30" : "text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-900/30";
                const borderClass = isHighlyRecommended ? "border-red-400" : "border-blue-400";
                
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
                    <div class="text-[11px] text-gray-500 line-clamp-2 mt-1 mb-2 border-b border-gray-100 dark:border-gray-700 pb-2">${just.texto}</div>
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
        console.error("Error obteniendo contexto comercial:", e);
    }
}

// -------------------------------------------------------------
// CHECKOUT & VUELTO & MODALES
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

// Abre Modal de Confirmación
function openPreCheckout() {
    if (cart.length === 0) return;
    const totals = getCartTotals();
    const pagoIngresado = parseFloat(inputPago.value);
    
    if (!isNaN(pagoIngresado) && pagoIngresado > 0 && pagoIngresado < totals.total) {
        alert("El monto ingresado es menor al total de la venta.");
        return;
    }

    // Calcular tiempo
    timeToCheckout = Math.floor((Date.now() - checkoutTimerStart) / 1000);

    modalPreItems.textContent = totals.itemsCount;
    modalPreTotal.textContent = fmt(totals.total);
    modalPreUtilidad.textContent = fmt(totals.utilidad);
    
    preCheckoutModal.classList.remove('hidden');
    // Pequeño delay para la animación
    setTimeout(() => {
        preCheckoutModal.classList.remove('opacity-0');
        preCheckoutModal.querySelector('div').classList.remove('scale-95');
    }, 10);
}

function closePreCheckout() {
    preCheckoutModal.classList.add('opacity-0');
    preCheckoutModal.querySelector('div').classList.add('scale-95');
    setTimeout(() => preCheckoutModal.classList.add('hidden'), 300);
}

// Ejecuta Check-out al Backend
btnConfirmCheckout.addEventListener('click', async () => {
    closePreCheckout();
    checkoutLoading.classList.remove('hidden');
    
    const totals = getCartTotals();
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
        
        // Populate Post Modal
        modalPostTicket.textContent = `Ticket #${response.idVenta}`;
        modalPostTiempo.textContent = `${timeToCheckout} seg`;
        modalPostUtilidad.textContent = fmt(response.utilidad_total);
        
        openPostCheckout();
        
    } catch (e) {
        checkoutLoading.classList.add('hidden');
        alert(e.message || "Error procesando la venta");
    }
});

btnPreCheckout.addEventListener('click', openPreCheckout);

// Modal Éxito
function openPostCheckout() {
    postCheckoutModal.classList.remove('hidden');
    setTimeout(() => {
        postCheckoutModal.classList.remove('opacity-0');
        postCheckoutModal.querySelector('div').classList.remove('scale-95');
    }, 10);
}

function closePostCheckout() {
    postCheckoutModal.classList.add('opacity-0');
    postCheckoutModal.querySelector('div').classList.add('scale-95');
    setTimeout(() => {
        postCheckoutModal.classList.add('hidden');
        clearCart();
        searchInput.focus();
    }, 300);
}

// Arrancar
document.addEventListener('DOMContentLoaded', init);
