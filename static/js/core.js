/**
 * Smart POS - Core System Script
 * Handles global UI interactions like Theme Toggling, Navigation, and Clock.
 */
document.addEventListener('DOMContentLoaded', () => {
    // Set active nav link
    const ACTIVE_NAV_CLASS = "flex items-center gap-3 px-4 py-3 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 rounded-lg font-medium";
    const currentPath = window.location.pathname;
    
    const navMap = [
        { path: '/inventario', id: 'nav-inventario' },
        { path: '/pos', id: 'nav-pos' },
        { path: '/actores', id: 'nav-actores' },
        { path: '/compras', id: 'nav-compras' },
        { path: '/dashboard', id: 'nav-dashboard' },
    ];

    let activeNavId = 'nav-dashboard';
    for (const item of navMap) {
        if (currentPath.includes(item.path)) {
            activeNavId = item.id;
            break;
        }
    }
    const activeNav = document.getElementById(activeNavId);
    if (activeNav) activeNav.className = ACTIVE_NAV_CLASS;

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
