/**
 * Dashboard Logic - Phase 1 Migration
 */

// Global Chart Instances
let chartTendencia, chartCategorias, chartRanking;

// Utility: Animar valores numéricos
function animateValue(obj, start, end, duration, formatFn) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const currentVal = progress * (end - start) + start;
        obj.innerHTML = formatFn(currentVal);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        } else {
            obj.innerHTML = formatFn(end);
        }
    };
    window.requestAnimationFrame(step);
}

// Utility: Regresión lineal simple
function linearRegression(y) {
    const n = y.length;
    let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;
    for (let i = 0; i < n; i++) {
        sumX += i;
        sumY += y[i];
        sumXY += i * y[i];
        sumXX += i * i;
    }
    const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
    const intercept = (sumY - slope * sumX) / n;
    return y.map((_, i) => intercept + slope * i);
}

const themeColors = {
    get text() { return document.documentElement.classList.contains('dark') ? '#e5e7eb' : '#374151'; },
    get grid() { return document.documentElement.classList.contains('dark') ? '#374151' : '#e5e7eb'; },
    primary: '#2a82da',
    secondary: '#27ae60'
};

// Cargar y renderizar datos
async function loadDashboardData(period = '7_dias') {
    // UI State: Loading
    document.getElementById('chart-loading').classList.remove('hidden');
    document.getElementById('chart-container').classList.add('opacity-0');
    document.getElementById('chart-fallback').classList.add('hidden');
    
    try {
        const data = await ApiClient.get('/dashboard/metrics', { periodo: period });
        const { kpis, salud_inventario, proyeccion_mes, insights, charts } = data;
        
        // --- 1. Tarjetas KPI ---
        animateValue(document.getElementById('kpi-ventas-val'), 0, kpis.ventas.valor, 500, val => `S/ ${val.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits:2})}`);
        animateValue(document.getElementById('kpi-utilidad-val'), 0, kpis.utilidad.valor, 500, val => `S/ ${val.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits:2})}`);
        animateValue(document.getElementById('kpi-margen-val'), 0, kpis.margen.valor, 500, val => `${val.toFixed(1)}%`);
        animateValue(document.getElementById('kpi-clientes-val'), 0, kpis.clientes.valor, 500, val => Math.floor(val).toString());
        animateValue(document.getElementById('kpi-proyeccion-val'), 0, proyeccion_mes, 500, val => `S/ ${val.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits:2})}`);
        
        const progProy = proyeccion_mes > 0 ? (kpis.ventas.valor / proyeccion_mes) * 100 : 0;
        document.getElementById('kpi-proyeccion-bar').style.width = `${Math.min(progProy, 100)}%`;

        const setVar = (elId, val, invert = false) => {
            const el = document.getElementById(elId);
            if (Math.abs(val) < 0.1) {
                el.innerText = '≈ 0.00%';
                el.className = 'text-xs text-gray-400 mt-1 font-medium';
            } else {
                const isUp = val > 0;
                let colorClass = isUp ? 'text-green-500' : 'text-red-500';
                if (invert) colorClass = !isUp ? 'text-green-500' : 'text-red-500';
                el.innerText = `${isUp ? '↑' : '↓'} ${Math.abs(val).toFixed(2)}% vs Anterior`;
                el.className = `text-xs ${colorClass} mt-1 font-bold`;
            }
        };

        setVar('kpi-ventas-var', kpis.ventas.var);
        setVar('kpi-utilidad-var', kpis.utilidad.var);
        setVar('kpi-margen-var', kpis.margen.var);
        setVar('kpi-clientes-var', kpis.clientes.var);
        setVar('kpi-proyeccion-var', kpis.proyeccion ? kpis.proyeccion.var : kpis.ventas.var);

        // --- 2. Salud del Negocio ---
        let score = 0;
        if (kpis.utilidad.valor > 0) score += 30;
        if (kpis.ventas.var >= 0) score += 30;
        
        const criticos = (salud_inventario['Crítico'] || {}).items || 0;
        if (criticos === 0) score += 40;
        else if (criticos <= 5) score += 20;

        let estadoTxt = "Atención Requerida";
        let estadoColor = "text-red-500";
        if (score >= 80) { estadoTxt = "Excelente"; estadoColor = "text-green-500"; }
        else if (score >= 50) { estadoTxt = "Regular"; estadoColor = "text-orange-500"; }
        
        const hEstado = document.getElementById('health-status');
        hEstado.innerText = estadoTxt;
        hEstado.className = `font-bold ${estadoColor}`;
        document.getElementById('health-bar').style.width = `${score}%`;
        document.getElementById('health-score').innerText = `${score}/100`;

        // --- 3. Insights Accionables ---
        const container = document.getElementById('insights-container');
        document.getElementById('insights-count').textContent = insights.length;
        container.innerHTML = ''; // Limpiar
        
        insights.forEach(inv => {
            const card = document.createElement('div');
            
            let bgClass = "bg-white dark:bg-gray-800";
            let borderClass = "border-gray-200 dark:border-gray-700";
            
            if (inv.tipo === 'resumen') { bgClass = "bg-blue-50 dark:bg-blue-900/20"; borderClass = "border-blue-400"; }
            else if (inv.tipo === 'oportunidad' || inv.tipo === 'oportunidad_apriori') { bgClass = "bg-green-50 dark:bg-green-900/20"; borderClass = "border-green-500"; }
            else if (inv.tipo === 'riesgo') { bgClass = "bg-red-50 dark:bg-red-900/20"; borderClass = "border-red-500"; }
            else if (inv.tipo === 'tarea') { bgClass = "bg-sky-50 dark:bg-sky-900/20"; borderClass = "border-sky-500"; }

            card.className = `${bgClass} border ${borderClass} rounded-lg p-3`;
            
            let btnHtml = '';
            // Data to be attached for the modal
            let insightDataStr = encodeURIComponent(JSON.stringify(inv));

            if (inv.accion_texto && inv.accion_target) {
                btnHtml = `
                    <div class="mt-3">
                        <button onclick="event.stopPropagation(); resolveAction('${inv.accion_target}')" class="w-full text-xs font-bold text-white bg-gray-800 hover:bg-black dark:bg-gray-700 dark:hover:bg-gray-600 px-3 py-2 rounded-lg transition-colors flex items-center justify-between">
                            <span>${inv.accion_texto}</span> <i class="fa-solid fa-arrow-right"></i>
                        </button>
                    </div>
                `;
            } else if (inv.tipo === 'oportunidad_apriori' && inv.apriori_data) {
                btnHtml = `
                    <div class="mt-3">
                        <button onclick="event.stopPropagation(); openModal(${inv.apriori_data.soporte}, ${inv.apriori_data.confianza}, ${inv.apriori_data.lift})" class="w-full text-xs font-bold text-white bg-purple-600 hover:bg-purple-700 px-3 py-2 rounded-lg transition-colors flex items-center justify-between">
                            <span>Ver Análisis IA</span> <i class="fa-solid fa-chart-simple"></i>
                        </button>
                    </div>
                `;
            }

            card.className = `${bgClass} border ${borderClass} rounded-lg p-4 cursor-pointer hover:shadow-md transition-shadow relative overflow-hidden group`;
            card.setAttribute("onclick", `openInsightModal(decodeURIComponent('${insightDataStr}'))`);
            
            // Un pequeño indicador visual al hover
            let hoverInd = `<div class="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity text-gray-400"><i class="fa-solid fa-chevron-right"></i></div>`;
            if (inv.accion_target || inv.apriori_data) {
                 hoverInd = ''; // Si tiene botón directo, no hace falta la flecha
            }

            card.innerHTML = `
                <div class="flex gap-3">
                    <div class="text-2xl mt-0.5">${inv.icono}</div>
                    <div class="flex-1">
                        <p class="text-sm ${inv.tipo === 'resumen' ? 'font-bold' : 'font-medium'} text-gray-800 dark:text-gray-200 leading-snug">${inv.mensaje}</p>
                        ${btnHtml}
                    </div>
                </div>
                ${hoverInd}
            `;
            container.appendChild(card);
        });

        // --- 4. Gráficos (Chart.js) ---
        if (chartTendencia) chartTendencia.destroy();
        if (chartCategorias) chartCategorias.destroy();
        if (chartRanking) chartRanking.destroy();

        if (charts.tendencia && charts.tendencia.length > 1) {
            // Mostrar gráficos
            document.getElementById('chart-container').classList.remove('opacity-0');
            
            // Tendencia
            const labels = charts.tendencia.map(t => t.mes);
            const dataVentas = charts.tendencia.map(t => t.total_vendido);
            const dataTendencia = linearRegression(dataVentas);

            chartTendencia = new Chart(document.getElementById('chartTendencia'), {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        { label: 'Ventas', data: dataVentas, borderColor: themeColors.primary, tension: 0.3, borderWidth: 2, pointRadius: 4 },
                        { label: 'Tendencia', data: dataTendencia, borderColor: '#e74c3c', borderDash: [5, 5], borderWidth: 1.5, pointRadius: 0 }
                    ]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: {
                        x: { grid: { display: false }, ticks: { color: themeColors.text, font: {size: 10} } },
                        y: { grid: { color: themeColors.grid }, ticks: { color: themeColors.text, font: {size: 10} } }
                    },
                    plugins: { 
                        legend: { labels: { color: themeColors.text, font: {size: 10}, boxWidth: 12 } },
                        title: { display: true, text: '📈 Proyección Tendencial', color: themeColors.text, font: {size: 12, weight: 'bold'}, padding: {bottom: 10} }
                    }
                }
            });

            // Categorías (Doughnut)
            if (charts.categorias.length > 0) {
                chartCategorias = new Chart(document.getElementById('chartCategorias'), {
                    type: 'doughnut',
                    data: {
                        labels: charts.categorias.map(c => c.categoria),
                        datasets: [{
                            data: charts.categorias.map(c => c.precio_total),
                            backgroundColor: ['#2a82da', '#27ae60', '#f39c12', '#8e44ad', '#e74c3c']
                        }]
                    },
                    options: {
                        onClick: (e, elements) => {
                             if (elements.length > 0) {
                                 const idx = elements[0].index;
                                 const label = chartCategorias.data.labels[idx];
                                 const val = chartCategorias.data.datasets[0].data[idx];
                                 alert(`Categoría ${label}: S/ ${val.toLocaleString('en-US')}`);
                             }
                        },
                        responsive: true, maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'bottom', labels: { color: themeColors.text, font: {size: 10}, boxWidth: 10 } }
                        }
                    }
                });
            }

            // Ranking (Bar Horizontal)
            if (charts.ranking.length > 0) {
                chartRanking = new Chart(document.getElementById('chartRanking'), {
                    type: 'bar',
                    data: {
                        labels: charts.ranking.map(r => r.nombre),
                        datasets: [{
                            label: 'Unidades Vendidas',
                            data: charts.ranking.map(r => r.cantidad_vendida),
                            backgroundColor: themeColors.secondary
                        }]
                    },
                    options: {
                        onClick: (e, elements) => {
                             if (elements.length > 0) {
                                 const idx = elements[0].index;
                                 const label = chartRanking.data.labels[idx];
                                 const val = chartRanking.data.datasets[0].data[idx];
                                 alert(`Producto Top: ${label} (${val} unidades)`);
                             }
                        },
                        indexAxis: 'y',
                        responsive: true, maintainAspectRatio: false,
                        scales: {
                            x: { grid: { color: themeColors.grid }, ticks: { color: themeColors.text, font: {size: 10} } },
                            y: { grid: { display: false }, ticks: { color: themeColors.text, font: {size: 10} } }
                        },
                        plugins: { 
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        // Context dataIndex -> charts.ranking[dataIndex].total_recaudado
                                        const r = charts.ranking[context.dataIndex];
                                        const usd = Number(r.total_recaudado || 0).toLocaleString('en-US', {style:'currency', currency:'USD'});
                                        return ` Ingreso: S/ {usd} (${r.cantidad_vendida} unds)`;
                                    },
                                    labelColor: function(context) {
                                        return { borderColor: '#22c55e', backgroundColor: '#22c55e' }; // Verde para el tooltip
                                    }
                                }
                            }
                        }
                    }
                });
            }
        } else {
            // Mostrar Fallback
            document.getElementById('chart-fallback').classList.remove('hidden');
            document.getElementById('fallback-msg').innerText = `Ventas consolidadas en este periodo: S/ ${kpis.ventas.valor.toLocaleString('en-US')}. Salud actual: ${estadoTxt}.`;
        }

    } catch (error) {
        console.error("Error loading dashboard data:", error);
        alert("Ocurrió un error al cargar las métricas. Revisa la consola.");
    } finally {
        document.getElementById('chart-loading').classList.add('hidden');
    }
}

// Filtros Event Listeners
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        // Quitar estado activo
        document.querySelectorAll('.filter-btn').forEach(b => {
            b.classList.remove('active', 'text-white', 'bg-primary');
            b.classList.add('text-gray-600', 'dark:text-gray-300');
        });
        // Poner estado activo
        const target = e.currentTarget;
        target.classList.add('active', 'text-white', 'bg-primary');
        target.classList.remove('text-gray-600', 'dark:text-gray-300');
        
        // Cargar
        loadDashboardData(target.dataset.period);
    });
});

// Reactividad al cambio de tema
window.addEventListener('themeChanged', () => {
    // Recargar gráficos para aplicar colores del tema
    const activeBtn = document.querySelector('.filter-btn.active');
    if (activeBtn) loadDashboardData(activeBtn.dataset.period);
});

// Init
document.addEventListener('DOMContentLoaded', () => {
    loadDashboardData('7_dias');
});

// Modal Logic
function openModal(soporte, confianza, lift) {
    document.getElementById('modal-soporte').innerText = (soporte * 100).toFixed(1) + '% de las ventas';
    document.getElementById('modal-confianza').innerText = (confianza * 100).toFixed(0) + '% de clientes';
    document.getElementById('modal-lift').innerText = lift.toFixed(1) + 'x más probable';
    
    const modal = document.getElementById('aprioriModal');
    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        modal.firstElementChild.classList.remove('scale-95');
    }, 10);
}

function closeModal() {
    const modal = document.getElementById('aprioriModal');
    modal.classList.add('opacity-0');
    modal.firstElementChild.classList.add('scale-95');
    setTimeout(() => {
        modal.classList.add('hidden');
    }, 300);
}

let currentTargetAction = '';

function resolveAction(target) {
    if (target) {
        window.location.href = target;
    }
}

function openInsightModal(dataStr) {
    try {
        const inv = JSON.parse(dataStr);
        document.getElementById('insight-modal-icon').innerText = inv.icono;
        document.getElementById('insight-modal-msg').innerText = inv.mensaje;
        
        // Asignar descripción basada en tipo
        let desc = "Revisar los detalles para tomar acción.";
        if (inv.tipo === 'riesgo') desc = "Es necesario tomar acción inmediata para mitigar este riesgo operativo.";
        if (inv.tipo === 'oportunidad' || inv.tipo === 'oportunidad_apriori') desc = "Aplicar esta sugerencia podría mejorar la utilidad o la experiencia del cliente.";
        if (inv.tipo === 'resumen') desc = "Resumen automatizado del periodo analizado.";
        document.getElementById('insight-modal-desc').innerText = desc;
        
        const extra = document.getElementById('insight-modal-extra');
        extra.innerHTML = '';
        extra.classList.add('hidden');
        
        if (inv.tipo === 'oportunidad_apriori' && inv.apriori_data) {
             extra.classList.remove('hidden');
             extra.innerHTML = `
                 <div class="space-y-2.5">
                     <h5 class="font-bold text-xs uppercase tracking-wider text-purple-700 dark:text-purple-300 flex items-center gap-1.5">
                         <i class="fa-solid fa-chart-line"></i> Diagnóstico de Venta Cruzada:
                     </h5>
                     <div class="space-y-2 text-xs">
                         <div class="flex justify-between items-center bg-white dark:bg-gray-800 p-2.5 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
                             <span class="text-gray-600 dark:text-gray-300">🎯 Certeza de compra en conjunto:</span>
                             <strong class="text-blue-600 dark:text-blue-400 font-mono text-sm">${(inv.apriori_data.confianza * 100).toFixed(0)}%</strong>
                         </div>
                         <div class="flex justify-between items-center bg-white dark:bg-gray-800 p-2.5 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
                             <span class="text-gray-600 dark:text-gray-300">🚀 Fuerza de la combinación:</span>
                             <strong class="text-purple-600 dark:text-purple-400 font-mono text-sm">${inv.apriori_data.lift.toFixed(1)}x más probable</strong>
                         </div>
                         <div class="flex justify-between items-center bg-white dark:bg-gray-800 p-2.5 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
                             <span class="text-gray-600 dark:text-gray-300">🛍️ Presencia en ventas globales:</span>
                             <strong class="text-green-600 dark:text-green-400 font-mono text-sm">${(inv.apriori_data.soporte * 100).toFixed(1)}% de tickets</strong>
                         </div>
                     </div>
                     <p class="text-[11px] text-purple-700 dark:text-purple-300 bg-purple-50 dark:bg-purple-950/40 p-2.5 rounded-lg border border-purple-100 dark:border-purple-900/50 leading-tight">
                         💡 <strong>Sugerencia Comercial:</strong> Ofrece estos productos juntos en el mostrador o promociona el combo en tus redes sociales.
                     </p>
                 </div>
             `;
        }

        const btn = document.getElementById('insight-modal-action-btn');
        if (inv.accion_target) {
            btn.classList.remove('hidden');
            currentTargetAction = inv.accion_target;
        } else {
            btn.classList.add('hidden');
            currentTargetAction = '';
        }

        const modal = document.getElementById('insightDetailModal');
        modal.classList.remove('hidden');
        setTimeout(() => {
            modal.classList.remove('opacity-0');
            modal.firstElementChild.classList.remove('scale-95');
        }, 10);
    } catch(e) {
        console.error("Error modal:", e);
    }
}

function closeInsightModal() {
    const modal = document.getElementById('insightDetailModal');
    modal.classList.add('opacity-0');
    modal.firstElementChild.classList.add('scale-95');
    setTimeout(() => {
        modal.classList.add('hidden');
    }, 300);
}

function executeModalAction() {
    if (currentTargetAction) {
        resolveAction(currentTargetAction);
    }
}
