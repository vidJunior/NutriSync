// static/js/app.js
// Funciones globales de NutriSync: modales, carga AJAX de formularios/detalles.
// Todas las operaciones DOM usan métodos seguros (createElement, replaceChildren,
// cloneNode, importNode, replaceWith) para prevenir XSS.

// ─── Modal ──────────────────────────────────────────────────────────────────

function openModal(title) {
    const overlay = document.getElementById('modal-overlay');
    const container = document.getElementById('modal-container');
    document.getElementById('modal-title').textContent = title;
    _showLoading();
    overlay.classList.remove('hidden');
    overlay.classList.add('flex');
    requestAnimationFrame(() => {
        container.classList.remove('scale-95', 'opacity-0');
        container.classList.add('scale-100', 'opacity-100');
    });
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    const overlay = document.getElementById('modal-overlay');
    const container = document.getElementById('modal-container');
    container.classList.add('scale-95', 'opacity-0');
    container.classList.remove('scale-100', 'opacity-100');
    setTimeout(() => {
        overlay.classList.add('hidden');
        overlay.classList.remove('flex');
    }, 200);
    document.body.style.overflow = '';
}

function _showLoading() {
    const content = document.getElementById('modal-content');
    content.replaceChildren();

    const loaderDiv = document.createElement('div');
    loaderDiv.className = 'flex items-center justify-center py-12 text-slate-400';

    const icon = document.createElement('i');
    icon.setAttribute('data-lucide', 'loader');
    icon.className = 'w-6 h-6 animate-spin';

    const span = document.createElement('span');
    span.className = 'ml-2 text-sm';
    span.textContent = 'Cargando...';

    loaderDiv.appendChild(icon);
    loaderDiv.appendChild(span);
    content.appendChild(loaderDiv);

    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

function _showError(message) {
    const content = document.getElementById('modal-content');
    const p = document.createElement('p');
    p.className = 'text-red-500';
    p.textContent = message;
    content.replaceChildren(p);
}

function setModalContent(htmlOrElement) {
    const content = document.getElementById('modal-content');
    content.replaceChildren();

    if (typeof htmlOrElement === 'string') {
        const parser = new DOMParser();
        const doc = parser.parseFromString(htmlOrElement, 'text/html');
        Array.from(doc.body.childNodes).forEach(node => {
            content.appendChild(document.importNode(node, true));
        });
    } else if (htmlOrElement instanceof Element) {
        content.appendChild(htmlOrElement.cloneNode(true));
    }

    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

// ─── Carga de formulario (Nuevo / Editar) ──────────────────────────────────

async function openModalNuevo() {
    openModal('Nuevo Paciente');
    await loadFormContent('/pacientes/nuevo/?fragment=1');
}

async function openModalEditar(pk) {
    openModal('Editar Paciente');
    await loadFormContent(`/pacientes/${pk}/editar/?fragment=1`);
}

async function loadFormContent(url) {
    try {
        const resp = await fetch(url);
        const html = await resp.text();

        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const formContent = doc.getElementById('paciente-form-content');

        if (formContent) {
            setModalContent(formContent);
            const actionUrl = url.split('?')[0];
            const form = document.getElementById('paciente-form');
            if (form) form.dataset.actionUrl = actionUrl;
            bindFormSubmit();
        } else {
            _showError('Error al cargar el formulario.');
        }
    } catch (err) {
        _showError('Error de conexión.');
    }
}

function bindFormSubmit() {
    const form = document.getElementById('paciente-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const submitBtn = form.querySelector('button[type="submit"]');
        const savedChildren = [];
        while (submitBtn.firstChild) {
            savedChildren.push(submitBtn.removeChild(submitBtn.firstChild));
        }
        submitBtn.disabled = true;

        const spinner = document.createElement('i');
        spinner.setAttribute('data-lucide', 'loader');
        spinner.className = 'w-4 h-4 animate-spin';
        submitBtn.appendChild(spinner);
        submitBtn.appendChild(document.createTextNode(' Guardando...'));
        if (typeof lucide !== 'undefined') lucide.createIcons();

        try {
            const formData = new FormData(form);
            const actionUrl = form.dataset.actionUrl;
            const resp = await fetch(actionUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
            });

            if (resp.ok) {
                const html = await resp.text();
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');

                const formContent = doc.getElementById('paciente-form-content');
                if (formContent) {
                    setModalContent(formContent);
                    bindFormSubmit();
                } else {
                    closeModal();
                    refreshListaPacientes();
                }
            } else {
                _showError('Error del servidor (' + resp.status + ').');
            }
        } catch (err) {
            _showError('Error de conexión.');
        } finally {
            submitBtn.replaceChildren();
            savedChildren.forEach(child => submitBtn.appendChild(child));
            submitBtn.disabled = false;
        }
    });
}

// ─── Carga de detalle ───────────────────────────────────────────────────────

async function openModalDetalle(pk) {
    openModal('Ficha de Paciente');
    try {
        const resp = await fetch(`/pacientes/${pk}/?fragment=1`);
        const html = await resp.text();

        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const detailContent = doc.getElementById('paciente-detail-content');

        if (detailContent) {
            setModalContent(detailContent);
        } else {
            _showError('Error al cargar los datos del paciente.');
        }
    } catch (err) {
        _showError('Error de conexión.');
    }
}

// ─── Toggle estado (desde modal o desde lista) ──────────────────────────────

async function toggleEstado(pk) {
    try {
        const csrfToken = window.CSRF_TOKEN || '';

        const resp = await fetch(`/pacientes/${pk}/toggle/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken || '',
                'X-Requested-With': 'XMLHttpRequest',
            },
        });

        if (resp.ok || resp.redirected) {
            const overlay = document.getElementById('modal-overlay');
            if (!overlay.classList.contains('hidden')) {
                await openModalDetalle(pk);
            } else {
                refreshListaPacientes();
            }
        }
    } catch (err) {
        console.error('Error al cambiar estado:', err);
    }
}

// ─── Refrescar lista de pacientes (recarga la tabla sin recargar la página) ─

let refreshCounter = 0;
async function refreshListaPacientes() {
    const urlParams = new URLSearchParams(window.location.search);
    refreshCounter++;
    urlParams.set('_refresh', refreshCounter);
    const url = '/pacientes/?' + urlParams.toString();

    try {
        const resp = await fetch(url);
        const html = await resp.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');

        const newTable = doc.querySelector('#pacientes-table-body');
        const newPagination = doc.querySelector('#pacientes-pagination');
        const newCounts = doc.querySelector('#pacientes-counts');

        const oldTable = document.getElementById('pacientes-table-body');
        const oldPagination = document.getElementById('pacientes-pagination');
        const oldCounts = document.getElementById('pacientes-counts');

        if (oldTable && newTable) oldTable.replaceWith(newTable.cloneNode(true));
        if (oldPagination && newPagination) oldPagination.replaceWith(newPagination.cloneNode(true));
        if (oldCounts && newCounts) oldCounts.replaceWith(newCounts.cloneNode(true));

        if (typeof lucide !== 'undefined') lucide.createIcons();
    } catch (err) {
        console.error('Error al refrescar lista:', err);
        location.reload();
    }
}

// ─── Sidebar Responsive ────────────────────────────────────────────────────

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.classList.toggle('-translate-x-full');
    }
}

function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.classList.add('-translate-x-full');
    }
}

// ─── Inicialización al cargar la página ─────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    // Sidebar responsive toggle
    const menuBtn = document.getElementById('menu-btn');
    const sidebar = document.getElementById('sidebar');
    const sidebarLinks = sidebar ? sidebar.querySelectorAll('a') : [];

    if (menuBtn && sidebar) {
        // Toggle sidebar con el botón del menú
        menuBtn.addEventListener('click', () => {
            toggleSidebar();
        });

        // Cerrar sidebar cuando se hace clic en un enlace (en móvil)
        sidebarLinks.forEach(link => {
            link.addEventListener('click', () => {
                // Solo cerrar en dispositivos pequeños (menos de lg)
                if (window.innerWidth < 1024) {
                    closeSidebar();
                }
            });
        });
    }

    // Cerrar sidebar al cambiar el tamaño de la ventana a desktop
    window.addEventListener('resize', () => {
        const sidebar = document.getElementById('sidebar');
        if (sidebar && window.innerWidth >= 1024) {
            sidebar.classList.remove('-translate-x-full');
        }
    });
});
