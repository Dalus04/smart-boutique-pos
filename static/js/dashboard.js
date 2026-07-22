/**
 * Dashboard Logic — Analytical Decoupling Edition
 *
 * Contract: ALL calculations (health score, regression, projections, variations)
 * arrive pre-computed in the API payload. This file is a pure renderer.
 */

// ─── Global Chart Instances ────────────────────────────────────────────────
let chartTendencia, chartCategorias, chartRanking;

// ─── Global state snapshot (for modals) ───────────────────────────────────
let _dashData   = null;
let _dashPeriodo = '7_dias';

// ═══════════════════════════════════════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════════════════════════════════════

/** Animate a DOM element's numeric text from start to end over `duration` ms. */
function animateValue(obj, start, end, duration, formatFn) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = formatFn(progress * (end - start) + start);
        if (progress < 1) window.requestAnimationFrame(step);
        else obj.innerHTML = formatFn(end);
    };
    window.requestAnimationFrame(step);
}

/** Human-readable label for a period key. */
function periodoLabel(periodo) {
    if (periodo === 'custom') {
        const start = document.getElementById('date-start')?.value;
        const end = document.getElementById('date-end')?.value;
        return start && end ? `${start} a ${end}` : 'Rango personalizado';
    }
    return { hoy: 'Hoy', '7_dias': 'Últimos 7 días', mes: 'Último mes', anio: 'Último año', todo: 'Todo el período' }[periodo] || periodo;
}

/** Approximate day count for a period key (used for KPI modal context). */
function periodoDias(periodo) {
    if (periodo === 'custom') {
        const start = document.getElementById('date-start')?.value;
        const end = document.getElementById('date-end')?.value;
        if (start && end) {
            const diff = (new Date(end) - new Date(start)) / (1000 * 60 * 60 * 24);
            return Math.max(Math.round(diff) + 1, 1);
        }
        return 1;
    }
    return { hoy: 1, '7_dias': 7, mes: 30, anio: 365, todo: 365 }[periodo] || 7;
}

// ─── Theme colours (reactive to dark-mode toggle) ─────────────────────────
const themeColors = {
    get text() { return document.documentElement.classList.contains('dark') ? '#e5e7eb' : '#374151'; },
    get grid() { return document.documentElement.classList.contains('dark') ? '#374151' : '#e5e7eb'; },
    get emptyText() { return document.documentElement.classList.contains('dark') ? '#6b7280' : '#9ca3af'; },
    primary:   '#2a82da',
    secondary: '#27ae60',
};

// fmtCurrency disponible desde utils.js (cargado en base.html)

// ═══════════════════════════════════════════════════════════════════════════
// EMPTY-STATE CHART PLUGIN
// A Chart.js plugin that draws a centred watermark when there is no data.
// ═══════════════════════════════════════════════════════════════════════════
const emptyStatePlugin = {
    id: 'emptyState',
    afterDraw(chart) {
        const isEmpty = chart.data.datasets.every(ds =>
            !ds.data || ds.data.length === 0 || ds.data.every(v => v === 0 || v == null)
        );
        if (!isEmpty) return;

        const { ctx, chartArea: { left, top, width, height } } = chart;
        ctx.save();

        // Background pill
        const cx = left + width / 2;
        const cy = top  + height / 2;
        ctx.fillStyle = document.documentElement.classList.contains('dark')
            ? 'rgba(55, 65, 81, 0.5)'
            : 'rgba(243, 244, 246, 0.8)';
        const pw = Math.min(width * 0.75, 280);
        const ph = 52;
        ctx.beginPath();
        ctx.roundRect(cx - pw / 2, cy - ph / 2, pw, ph, 10);
        ctx.fill();

        // Icon
        ctx.fillStyle = themeColors.emptyText;
        ctx.font = '18px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('📭', cx, cy - 9);

        // Text
        ctx.font = '600 11px Inter, system-ui, sans-serif';
        ctx.fillText('Sin transacciones en este período', cx, cy + 13);

        ctx.restore();
    }
};
Chart.register(emptyStatePlugin);

// ═══════════════════════════════════════════════════════════════════════════
// MAIN LOAD FUNCTION
// ═══════════════════════════════════════════════════════════════════════════
async function loadDashboardData(period = '7_dias', fechaInicio = null, fechaFin = null) {
    _dashPeriodo = period;

    // Show loader, hide charts
    document.getElementById('chart-loading').classList.remove('hidden');
    document.getElementById('chart-container').classList.add('opacity-0');
    document.getElementById('chart-fallback').classList.add('hidden');

    try {
        const params = { periodo: period };
        if (period === 'custom' && fechaInicio && fechaFin) {
            params.fecha_inicio = fechaInicio;
            params.fecha_fin = fechaFin;
        }

        const data = await ApiClient.get('/dashboard/metrics', params);
        _dashData = data;

        const { kpis, health, salud_inventario, proyeccion_mes, proyeccion_fin_mes, charts } = data;
        const proy = proyeccion_fin_mes ?? proyeccion_mes ?? 0;

        // ── 1. KPI Cards ─────────────────────────────────────────────────
        animateValue(document.getElementById('kpi-ventas-val'),     0, kpis.ventas.valor,   500, v => fmtCurrency(v));
        animateValue(document.getElementById('kpi-utilidad-val'),   0, kpis.utilidad.valor, 500, v => fmtCurrency(v));
        animateValue(document.getElementById('kpi-margen-val'),     0, kpis.margen.valor,   500, v => `${v.toFixed(1)}%`);
        animateValue(document.getElementById('kpi-clientes-val'),   0, kpis.clientes.valor, 500, v => Math.floor(v).toString());
        animateValue(document.getElementById('kpi-proyeccion-val'), 0, proy,                500, v => fmtCurrency(v));

        const progProy = proy > 0 ? Math.min((kpis.ventas.valor / proy) * 100, 100) : 0;
        document.getElementById('kpi-proyeccion-bar').style.width = `${progProy}%`;

        const setVar = (elId, val) => {
            const el = document.getElementById(elId);
            if (period === 'todo') {
                el.innerText = 'Histórico total';
                el.className = 'text-xs text-slate-400 dark:text-slate-500 mt-1 font-semibold';
            } else if (Math.abs(val) < 0.1) {
                el.innerText  = '≈ 0.00%';
                el.className  = 'text-xs text-slate-400 dark:text-slate-500 mt-1 font-semibold';
            } else {
                const isUp = val > 0;
                el.innerText = `${isUp ? '↑' : '↓'} ${Math.abs(val).toFixed(2)}% vs Anterior`;
                el.className = `text-xs ${isUp ? 'text-green-500' : 'text-red-500'} mt-1 font-bold`;
            }
        };
        setVar('kpi-ventas-var',     kpis.ventas.var);
        setVar('kpi-utilidad-var',   kpis.utilidad.var);
        setVar('kpi-margen-var',     kpis.margen.var);
        setVar('kpi-clientes-var',   kpis.clientes.var);
        // Proyección usa la variación de ventas como proxy
        setVar('kpi-proyeccion-var', kpis.ventas.var);

        // ── 2. Health Score — leer desde data.health ──────────────────────
        const { score, estado: estadoTxt } = health;

        const estadoColor = score >= 80 ? 'text-green-500' : score >= 50 ? 'text-orange-500' : 'text-red-500';
        const hEstado = document.getElementById('health-status');
        hEstado.innerText = estadoTxt;
        hEstado.className = `font-bold text-2xl ${estadoColor}`;
        document.getElementById('health-bar').style.width  = `${score}%`;
        document.getElementById('health-score').innerText  = `${score}/100`;

        // Snapshot para el modal (ya viene del servidor, no se recalcula)
        window._healthSnapshot = health;

        // ── 3. Centro de Operaciones ──────────────────────────────────────
        const criticos  = (salud_inventario['Crítico'] || {}).items || 0;
        const compCount = data.compras_pendientes || 0;
        const cliCount  = data.clientes_nuevos_mes || 0;

        document.getElementById('ops-inventario-count').textContent = criticos;
        document.getElementById('ops-inventario-desc').textContent  =
            criticos === 1 ? ' producto requiere reposición inmediata' : ' productos requieren reposición inmediata';

        document.getElementById('ops-compras-count').textContent = compCount;
        document.getElementById('ops-compras-desc').textContent  =
            compCount === 1 ? ' orden espera confirmación o recepción' : ' órdenes esperan confirmación o recepción';

        document.getElementById('ops-ventas-count').textContent = cliCount;
        document.getElementById('ops-ventas-desc').textContent  =
            cliCount === 1 ? ' cliente registrado este mes' : ' clientes registrados este mes';

        // ── 4. Charts ─────────────────────────────────────────────────────
        if (chartTendencia)  chartTendencia.destroy();
        if (chartCategorias) chartCategorias.destroy();
        if (chartRanking)    chartRanking.destroy();

        // Always make the chart container visible — empty state handled by plugin
        document.getElementById('chart-container').classList.remove('opacity-0');

        // ── 4a. Tendencia — línea de regresión viene del servidor ─────────
        const hasTendencia = charts.tendencia && charts.tendencia.length > 0;
        const labels        = hasTendencia ? charts.tendencia.map(t => t.mes)          : [];
        const dataVentas    = hasTendencia ? charts.tendencia.map(t => t.total_vendido) : [];
        const dataTend      = hasTendencia ? (charts.tendencia_regresion || [])         : [];

        chartTendencia = new Chart(document.getElementById('chartTendencia'), {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Ventas',
                        data: dataVentas,
                        borderColor: themeColors.primary,
                        backgroundColor: 'rgba(42,130,218,0.08)',
                        tension: 0.3,
                        borderWidth: 2,
                        pointRadius: 4,
                        fill: true,
                    },
                    {
                        label: 'Tendencia',
                        data: dataTend,
                        borderColor: '#e74c3c',
                        borderDash: [5, 5],
                        borderWidth: 1.5,
                        pointRadius: 0,
                        tension: 0,
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: {
                    x: { grid: { display: false }, ticks: { color: themeColors.text, font: { size: 10 } } },
                    y: { grid: { color: themeColors.grid }, ticks: { color: themeColors.text, font: { size: 10 } } }
                },
                plugins: {
                    legend: { labels: { color: themeColors.text, font: { size: 10 }, boxWidth: 12 } },
                    title:  { display: true, text: '📈 Recaudación y Tendencia', color: themeColors.text, font: { size: 12, weight: 'bold' }, padding: { bottom: 10 } },
                }
            }
        });

        // ── 4b. Categorías (doughnut) ──────────────────────────────────────
        const hasCat   = charts.categorias && charts.categorias.length > 0;
        const catLabels = hasCat ? charts.categorias.map(c => c.categoria)   : [];
        const catData   = hasCat ? charts.categorias.map(c => c.precio_total) : [];

        chartCategorias = new Chart(document.getElementById('chartCategorias'), {
            type: 'doughnut',
            data: {
                labels: catLabels,
                datasets: [{
                    data: catData,
                    backgroundColor: ['#2a82da', '#27ae60', '#f39c12', '#8e44ad', '#e74c3c', '#16a085']
                }]
            },
            options: {
                onClick: (e, elements) => {
                    if (!hasCat || elements.length === 0) return;
                    const cat = charts.categorias[elements[0].index];
                    openCategoriaModal(cat.categoria, cat.precio_total, cat.margen_ponderado);
                },
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { color: themeColors.text, font: { size: 10 }, boxWidth: 10 } }
                }
            }
        });

        // ── 4c. Top Productos (horizontal bar) ─────────────────────────────
        const hasRanking   = charts.ranking && charts.ranking.length > 0;
        const rankLabels   = hasRanking ? charts.ranking.map(r => r.nombre)           : [];
        const rankData     = hasRanking ? charts.ranking.map(r => r.cantidad_vendida)  : [];

        chartRanking = new Chart(document.getElementById('chartRanking'), {
            type: 'bar',
            data: {
                labels: rankLabels,
                datasets: [{
                    label: 'Unidades Vendidas',
                    data: rankData,
                    backgroundColor: themeColors.secondary
                }]
            },
            options: {
                onClick: (e, elements) => {
                    if (!hasRanking || elements.length === 0) return;
                    const r = charts.ranking[elements[0].index];
                    openTopProductoModal(r.nombre, r.cantidad_vendida, r.total_recaudado);
                },
                indexAxis: 'y',
                responsive: true, maintainAspectRatio: false,
                scales: {
                    x: { grid: { color: themeColors.grid }, ticks: { color: themeColors.text, font: { size: 10 } } },
                    y: { grid: { display: false }, ticks: { color: themeColors.text, font: { size: 10 } } }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label(context) {
                                if (!hasRanking) return '';
                                const r   = charts.ranking[context.dataIndex];
                                const rec = fmtCurrency(r.total_recaudado);
                                return ` Ingreso: ${rec} (${r.cantidad_vendida} unds)`;
                            },
                            labelColor() { return { borderColor: '#22c55e', backgroundColor: '#22c55e' }; }
                        }
                    }
                }
            }
        });

    } catch (error) {
        console.error('[Dashboard] Error loading metrics:', error);
        // Show non-blocking inline error message
        const fallback = document.getElementById('chart-fallback');
        const msg      = document.getElementById('fallback-msg');
        if (fallback && msg) {
            msg.innerHTML = `<span class="text-red-500 font-bold">⚠ Error de red</span><br>
                             <span class="text-sm">No se pudo conectar al servidor. Intenta recargar la página.</span>`;
            fallback.classList.remove('hidden');
        }
    } finally {
        document.getElementById('chart-loading').classList.add('hidden');
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// FILTER BUTTONS & CUSTOM DATE RANGE
// ═══════════════════════════════════════════════════════════════════════════
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', e => {
        const target = e.currentTarget;
        const period = target.dataset.period;

        if (period === 'custom') {
            const customBar = document.getElementById('custom-date-bar');
            const isHidden = customBar.classList.contains('hidden');
            if (isHidden) {
                customBar.classList.remove('hidden');
                // Establecer valores por defecto (ej. mes actual)
                const today = new Date().toISOString().split('T')[0];
                if (!document.getElementById('date-end').value) document.getElementById('date-end').value = today;
                if (!document.getElementById('date-start').value) {
                    const d = new Date();
                    d.setDate(d.getDate() - 30);
                    document.getElementById('date-start').value = d.toISOString().split('T')[0];
                }
            } else {
                customBar.classList.add('hidden');
            }
            return;
        } else {
            document.getElementById('custom-date-bar')?.classList.add('hidden');
        }

        document.querySelectorAll('.filter-btn').forEach(b => {
            b.classList.remove('active', 'text-white', 'bg-primary');
            b.classList.add('text-slate-600', 'dark:text-slate-300');
        });

        target.classList.add('active', 'text-white', 'bg-primary');
        target.classList.remove('text-slate-600', 'dark:text-slate-300');
        loadDashboardData(period);
    });
});

function applyCustomDateFilter() {
    const start = document.getElementById('date-start').value;
    const end = document.getElementById('date-end').value;

    if (!start || !end) {
        alert('Por favor selecciona una fecha de inicio y una fecha de fin.');
        return;
    }

    if (start > end) {
        alert('La fecha de inicio no puede ser posterior a la fecha de fin.');
        return;
    }

    document.querySelectorAll('.filter-btn').forEach(b => {
        b.classList.remove('active', 'text-white', 'bg-primary');
        b.classList.add('text-slate-600', 'dark:text-slate-300');
    });

    const customBtn = document.getElementById('custom-date-toggle');
    if (customBtn) {
        customBtn.classList.add('active', 'text-white', 'bg-primary');
        customBtn.classList.remove('text-slate-600', 'dark:text-slate-300');
    }

    loadDashboardData('custom', start, end);
}

function closeCustomDateBar() {
    document.getElementById('custom-date-bar')?.classList.add('hidden');
}

// Theme change → reload charts with correct colours
window.addEventListener('themeChanged', () => {
    const activeBtn = document.querySelector('.filter-btn.active');
    if (activeBtn) {
        const period = activeBtn.dataset.period;
        if (period === 'custom') {
            applyCustomDateFilter();
        } else {
            loadDashboardData(period);
        }
    }
});

// Init on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    loadDashboardData('7_dias');
});

// ═══════════════════════════════════════════════════════════════════════════
// MODAL HELPERS
// ═══════════════════════════════════════════════════════════════════════════
function _openModal(id) {
    const modal = document.getElementById(id);
    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        modal.firstElementChild.classList.remove('scale-95');
    }, 10);
}

function _closeModal(id) {
    const modal = document.getElementById(id);
    modal.classList.add('opacity-0');
    modal.firstElementChild.classList.add('scale-95');
    setTimeout(() => modal.classList.add('hidden'), 300);
}

// ─── Health Modal — datos ya vienen del servidor ──────────────────────────
function openHealthModal() {
    const snap = window._healthSnapshot;
    if (!snap) return;

    const { score, estado, factores = [], contexto = [] } = snap;

    document.getElementById('health-modal-score').innerHTML =
        `${score}<span class="text-lg text-gray-400">/100</span>`;

    const badge = document.getElementById('health-modal-badge');
    badge.textContent = estado;
    badge.className = 'px-4 py-2 rounded-xl text-sm font-bold text-white ' +
        (score >= 80 ? 'bg-green-500' : score >= 50 ? 'bg-orange-500' : 'bg-red-500');

    const ul = document.getElementById('health-modal-factors');

    ul.innerHTML = factores.map(f => `
        <li class="flex items-start justify-between gap-3">
            <span class="flex items-center gap-2 ${f.ok ? 'text-green-700 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
                <i class="fa-solid ${f.ok ? 'fa-circle-check' : 'fa-triangle-exclamation'} text-base shrink-0"></i>
                <span class="text-sm">${f.label}</span>
            </span>
            <span class="text-xs font-mono font-bold shrink-0 ${f.ok ? 'text-green-600 dark:text-green-400' : 'text-gray-400'}">${f.pts}</span>
        </li>
    `).join('');

    if (contexto.length > 0) {
        ul.innerHTML += '<li class="border-t border-gray-100 dark:border-gray-700 pt-2 mt-1 space-y-2">' +
            contexto.map(c => `
                <div class="flex items-center gap-2 ${c.warn ? 'text-amber-600 dark:text-amber-400' : 'text-gray-500 dark:text-gray-400'}">
                    <i class="fa-solid ${c.warn ? 'fa-circle-exclamation' : 'fa-circle-check'} text-sm shrink-0"></i>
                    <span class="text-xs">${c.label}</span>
                </div>
            `).join('') + '</li>';
    }

    _openModal('HealthModal');
}
function closeHealthModal() { _closeModal('HealthModal'); }

// ─── KPI Modal ────────────────────────────────────────────────────────────
const KPI_CONFIG = {
    ventas: {
        title: 'Ventas del Período',
        icon: 'fa-coins',
        color: 'from-blue-50 to-indigo-50 dark:from-gray-800 dark:to-gray-800/80',
        iconColor: 'text-blue-500',
        mainLabel: 'Total Recaudado',
        rows(d, periodo) {
            const dias    = periodoDias(periodo);
            const promDia = dias > 0 ? d.kpis.ventas.valor / dias : 0;
            const varVal  = d.kpis.ventas.var;
            const list = [];
            if (periodo !== 'todo') {
                list.push({ label: 'Variación vs período anterior', value: `${varVal >= 0 ? '↑' : '↓'} ${Math.abs(varVal).toFixed(2)}%`, warn: varVal < 0 });
            }
            list.push({ label: 'Promedio diario estimado',      value: fmtCurrency(promDia) });
            list.push({ label: 'Período analizado',             value: periodoLabel(periodo) });
            return list;
        },
        mainValue(d) { return fmtCurrency(d.kpis.ventas.valor); }
    },
    utilidad: {
        title: 'Utilidad Bruta',
        icon: 'fa-sack-dollar',
        color: 'from-green-50 to-emerald-50 dark:from-gray-800 dark:to-gray-800/80',
        iconColor: 'text-green-500',
        mainLabel: 'Utilidad Total',
        rows(d, periodo) {
            const participacion = d.kpis.ventas.valor > 0
                ? (d.kpis.utilidad.valor / d.kpis.ventas.valor * 100) : 0;
            const varVal = d.kpis.utilidad.var;
            const list = [
                { label: 'Margen obtenido',            value: `${d.kpis.margen.valor.toFixed(1)}%` },
                { label: 'Participación sobre ventas', value: `${participacion.toFixed(1)}%` }
            ];
            if (periodo !== 'todo') {
                list.push({ label: 'Variación vs período anterior', value: `${varVal >= 0 ? '↑' : '↓'} ${Math.abs(varVal).toFixed(2)}%`, warn: varVal < 0 });
            }
            return list;
        },
        mainValue(d) { return fmtCurrency(d.kpis.utilidad.valor); }
    },
    margen: {
        title: 'Margen Bruto',
        icon: 'fa-percent',
        color: 'from-orange-50 to-amber-50 dark:from-gray-800 dark:to-gray-800/80',
        iconColor: 'text-orange-500',
        mainLabel: 'Margen del Período',
        rows(d, periodo) {
            const varVal = d.kpis.margen.var;
            const list = [];
            if (periodo !== 'todo') {
                list.push({ label: 'Variación en pp vs anterior', value: `${varVal >= 0 ? '+' : ''}${varVal.toFixed(2)} pp`, warn: varVal < 0 });
            }
            list.push({ label: 'Umbral de alerta', value: '< 30%' });
            list.push({ label: 'Estado',           value: d.kpis.margen.valor >= 30 ? '✔ Saludable' : '⚠ Por debajo del umbral', warn: d.kpis.margen.valor < 30 });
            return list;
        },
        mainValue(d) { return `${d.kpis.margen.valor.toFixed(1)}%`; }
    },
    clientes: {
        title: 'Nuevos Clientes',
        icon: 'fa-users',
        color: 'from-purple-50 to-violet-50 dark:from-gray-800 dark:to-gray-800/80',
        iconColor: 'text-purple-500',
        mainLabel: 'Clientes únicos atendidos',
        rows(d, periodo) {
            const varVal = d.kpis.clientes.var;
            const list = [{ label: 'Período evaluado', value: periodoLabel(periodo) }];
            if (periodo !== 'todo') {
                list.push({ label: 'Variación vs período anterior', value: `${varVal >= 0 ? '↑' : '↓'} ${Math.abs(varVal).toFixed(2)}%`, warn: varVal < 0 });
            }
            return list;
        },
        mainValue(d) { return String(d.kpis.clientes.valor); }
    },
    proyeccion: {
        title: 'Proyección Mensual',
        icon: 'fa-calendar-day',
        color: 'from-teal-50 to-cyan-50 dark:from-gray-800 dark:to-gray-800/80',
        iconColor: 'text-teal-500',
        mainLabel: 'Proyección al cierre del mes',
        rows(d) {
            const ventas   = d.kpis.ventas.valor;
            const proy     = d.proyeccion_fin_mes ?? d.proyeccion_mes ?? 0;
            const progreso = proy > 0 ? Math.min((ventas / proy) * 100, 100) : 0;
            return [
                { label: 'Ventas acumuladas (mes actual)', value: fmtCurrency(ventas) },
                { label: 'Progreso hacia la proyección',   value: `${progreso.toFixed(1)}%` },
                { label: 'Método de cálculo',              value: 'Promedio diario × días del mes' },
            ];
        },
        mainValue(d) { return fmtCurrency(d.proyeccion_fin_mes ?? d.proyeccion_mes ?? 0); }
    }
};

function openKpiModal(kpi) {
    if (!_dashData) return;
    const cfg = KPI_CONFIG[kpi];
    if (!cfg) return;

    // Header gradient + icon
    document.getElementById('kpi-modal-header').className =
        `p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center bg-gradient-to-r ${cfg.color}`;
    document.getElementById('kpi-modal-title').innerHTML =
        `<i class="fa-solid ${cfg.icon} ${cfg.iconColor}"></i> ${cfg.title}`;

    // Main value
    document.getElementById('kpi-modal-main-label').textContent = cfg.mainLabel;
    document.getElementById('kpi-modal-main-value').textContent = cfg.mainValue(_dashData);

    // Detail rows
    const rows = cfg.rows(_dashData, _dashPeriodo);
    document.getElementById('kpi-modal-rows').innerHTML = rows.map(r => `
        <div class="flex items-center justify-between py-2 border-b border-gray-50 dark:border-gray-800 last:border-0">
            <span class="text-sm text-gray-600 dark:text-gray-400">${r.label}</span>
            <span class="text-sm font-bold ${r.warn ? 'text-red-500' : 'text-gray-800 dark:text-white'}">${r.value}</span>
        </div>
    `).join('');

    _openModal('KpiModal');
}
function closeKpiModal() { _closeModal('KpiModal'); }

// ─── Chart Click Modals ────────────────────────────────────────────────────
function openTopProductoModal(nombre, ventas, ingresos) {
    document.getElementById('top-prod-nombre').innerText   = nombre;
    document.getElementById('top-prod-ventas').innerText   = `${ventas} unidades`;
    document.getElementById('top-prod-ingresos').innerText = fmtCurrency(ingresos);
    _openModal('TopProductoModal');
}
function closeTopProductoModal() { _closeModal('TopProductoModal'); }

function openCategoriaModal(nombre, ventas, margen) {
    document.getElementById('cat-nombre').innerText = nombre;
    document.getElementById('cat-ventas').innerText = fmtCurrency(ventas);
    document.getElementById('cat-margen').innerText = `${Number(margen).toFixed(1)}%`;
    _openModal('CategoriaModal');
}
function closeCategoriaModal() { _closeModal('CategoriaModal'); }
