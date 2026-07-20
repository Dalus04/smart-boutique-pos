/**
 * Smart POS - Core System Script
 * Handles global UI interactions like Theme Toggling, Navigation, and Clock.
 */
document.addEventListener('DOMContentLoaded', () => {
    // Set active nav link
    const currentPath = window.location.pathname;
    if (currentPath.includes('/inventario')) {
        const nav = document.getElementById('nav-inventario');
        if (nav) nav.className = "flex items-center gap-3 px-4 py-3 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 rounded-lg font-medium";
    } else if (currentPath.includes('/pos')) {
        const nav = document.getElementById('nav-pos');
        if (nav) nav.className = "flex items-center gap-3 px-4 py-3 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 rounded-lg font-medium";
    } else if (currentPath.includes('/actores')) {
        const nav = document.getElementById('nav-actores');
        if (nav) nav.className = "flex items-center gap-3 px-4 py-3 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 rounded-lg font-medium";
    } else if (currentPath.includes('/compras')) {
        const nav = document.getElementById('nav-compras');
        if (nav) nav.className = "flex items-center gap-3 px-4 py-3 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 rounded-lg font-medium";
    } else {
        const nav = document.getElementById('nav-dashboard');
        if (nav) nav.className = "flex items-center gap-3 px-4 py-3 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 rounded-lg font-medium";
    }

    // Configuración de Tema
    const themeToggleBtn = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    const htmlElement = document.documentElement;

    if (themeToggleBtn && themeIcon) {
        // Comprobar preferencia guardada
        if (localStorage.getItem('theme') === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            htmlElement.classList.add('dark');
            themeIcon.classList.remove('fa-moon');
            themeIcon.classList.add('fa-sun');
        } else {
            htmlElement.classList.remove('dark');
        }

        themeToggleBtn.addEventListener('click', () => {
            htmlElement.classList.toggle('dark');
            if (htmlElement.classList.contains('dark')) {
                localStorage.setItem('theme', 'dark');
                themeIcon.classList.remove('fa-moon');
                themeIcon.classList.add('fa-sun');
            } else {
                localStorage.setItem('theme', 'light');
                themeIcon.classList.remove('fa-sun');
                themeIcon.classList.add('fa-moon');
            }
            // Disparar evento para actualizar gráficos si es necesario
            window.dispatchEvent(new Event('themeChanged'));
        });
    }

    // Reloj
    const clockElement = document.getElementById('current-time');
    if (clockElement) {
        setInterval(() => {
            clockElement.textContent = new Date().toLocaleString('es-ES', { 
                dateStyle: 'medium', timeStyle: 'short' 
            });
        }, 1000);
    }
});
