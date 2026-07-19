/**
 * Lógica Web para el Catálogo e Inventario
 */

// Elementos del DOM
const elSearchInput = document.getElementById('search-input');
const elFilterCategoria = document.getElementById('filter-categoria');
const elFilterEstado = document.getElementById('filter-estado');
const elTableBody = document.getElementById('table-body');
const elTableLoading = document.getElementById('table-loading');
const elTableEmpty = document.getElementById('table-empty');

// KPIs DOM
const kpiProductos = document.getElementById('kpi-productos');
const kpiStock = document.getElementById('kpi-stock');
const kpiRiesgo = document.getElementById('kpi-riesgo');
const kpiCategorias = document.getElementById('kpi-categorias');

// Función Debounce para proteger a la API de sobrecarga
function debounce(func, delay = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => { func.apply(this, args); }, delay);
    };
}

// Formateador de moneda
const fmtCurrency = (val) => `$${val.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits:2})}`;

// Cargar Categorías para el dropdown
async function loadCategorias() {
    try {
        const categorias = await ApiClient.get('/inventario/categorias');
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

// Generador de Badges Semánticos
function generateBadgeHtml(text, type) {
    let classes = "px-2 py-1 rounded-md text-xs font-bold ";
    let extraHtml = "";
    
    if (type === 'critico') {
        classes += "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 border border-red-200 dark:border-red-800";
        // Indicador animado pulsante para llamar la atención en Linux/Web
        extraHtml = `<span class="relative flex h-2 w-2 mr-1 inline-block">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
        </span>`;
    } else if (type === 'bajo') {
        classes += "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400 border border-orange-200 dark:border-orange-800";
    } else if (type === 'optimo') {
        // Desaturado para mitigar fatiga visual de alertas
        classes += "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 border border-transparent";
    }
    
    return `<div class="inline-flex items-center ${classes}">${extraHtml}${text}</div>`;
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
        
        // 1. Actualizar KPIs
        kpiProductos.textContent = data.kpis.productos_activos;
        kpiStock.textContent = data.kpis.stock_total.toLocaleString();
        kpiRiesgo.textContent = data.kpis.riesgo_alto_critico;
        kpiCategorias.textContent = data.kpis.categorias_activas;
        
        // 2. Renderizar Filas
        elTableBody.innerHTML = '';
        
        if (data.productos.length === 0) {
            elTableEmpty.classList.remove('hidden');
        } else {
            data.productos.forEach(prod => {
                const tr = document.createElement('tr');
                tr.className = "hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors";
                
                // Determinar el estilo de la fila si el riesgo es alto (Opcional, colorear sutilmente la fila entera)
                if (prod.riesgo === 'Riesgo Alto' || prod.estado_fisico === 'Crítico') {
                    tr.classList.add('bg-red-50/30', 'dark:bg-red-900/10');
                }
                
                // Mapear Tipos de Badge
                let badgeEstado = 'optimo';
                if (prod.estado_fisico === 'Crítico') badgeEstado = 'critico';
                else if (prod.estado_fisico === 'Bajo') badgeEstado = 'bajo';
                
                let badgeRiesgo = 'optimo';
                if (prod.riesgo === 'Riesgo Alto') badgeRiesgo = 'critico';
                else if (prod.riesgo === 'Riesgo Medio') badgeRiesgo = 'bajo';
                
                tr.innerHTML = `
                    <td class="py-3 px-4 whitespace-nowrap text-sm text-gray-500 font-mono">${prod.idProducto}</td>
                    <td class="py-3 px-4 whitespace-nowrap text-sm text-gray-500 font-mono">${prod.codigoBarras}</td>
                    <td class="py-3 px-4">
                        <div class="text-sm font-bold text-gray-900 dark:text-gray-100">${prod.nombre}</div>
                    </td>
                    <td class="py-3 px-4 whitespace-nowrap text-sm text-gray-500">${prod.categoria}</td>
                    <td class="py-3 px-4 whitespace-nowrap">
                        <div class="text-sm font-bold text-gray-900 dark:text-white">${fmtCurrency(prod.precio)}</div>
                        <div class="text-xs text-gray-400">Costo: ${fmtCurrency(prod.costo)}</div>
                    </td>
                    <td class="py-3 px-4 whitespace-nowrap text-center">
                        <div class="text-base font-bold ${prod.stock <= 5 ? 'text-red-500' : 'text-gray-700 dark:text-gray-300'}">${prod.stock}</div>
                    </td>
                    <td class="py-3 px-4 whitespace-nowrap text-center text-sm text-gray-600 dark:text-gray-400">
                        ${prod.velocidad}
                    </td>
                    <td class="py-3 px-4 whitespace-nowrap text-center space-y-1 flex flex-col items-center">
                        ${generateBadgeHtml(prod.estado_fisico, badgeEstado)}
                        ${generateBadgeHtml(prod.riesgo, badgeRiesgo)}
                    </td>
                    <td class="py-3 px-4 whitespace-nowrap text-right text-sm font-medium">
                        <button class="text-primary hover:text-blue-700 transition-colors p-2" title="Editar Stock">
                            <i class="fa-solid fa-pen-to-square"></i>
                        </button>
                    </td>
                `;
                
                elTableBody.appendChild(tr);
            });
        }
        
    } catch (e) {
        console.error("Error obteniendo datos del inventario", e);
        elTableBody.innerHTML = `<tr><td colspan="9" class="text-center text-red-500 p-4">Error cargando los datos. Ver consola.</td></tr>`;
    } finally {
        elTableLoading.classList.add('hidden');
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    loadCategorias().then(() => fetchAndRenderData());
    
    // Configurar Debounce (300ms) para la barra de búsqueda
    const debouncedSearch = debounce(() => {
        fetchAndRenderData();
    }, 300);
    
    elSearchInput.addEventListener('input', debouncedSearch);
    
    // Selectores reaccionan instantáneamente (no necesitan debounce agresivo)
    elFilterCategoria.addEventListener('change', fetchAndRenderData);
    elFilterEstado.addEventListener('change', fetchAndRenderData);
});
