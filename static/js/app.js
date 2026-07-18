

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

const tabsContainer = document.getElementById('tabs-container');
const scrollBtns = document.querySelectorAll('.scroll-btn');
const scrollControls = document.getElementById('tab-scroll-controls');
const SIDEBAR_BREAKPOINT = 1280;

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(updateTabScrollIndicators, 100);
    if (tabsContainer) {
        tabsContainer.addEventListener('scroll', updateTabScrollIndicators, { passive: true });
        if (window.innerWidth <= 767) setupTouchScroll(tabsContainer);
    }
});

function updateTabScrollIndicators() {
    if (!tabsContainer) return;

    const canScrollLeft = tabsContainer.scrollLeft > 0;
    const canScrollRight = tabsContainer.scrollLeft + tabsContainer.clientWidth < tabsContainer.scrollWidth - 10;
    const needsScroll = canScrollLeft || canScrollRight;

    if (scrollControls) {
        if (needsScroll) {
            scrollControls.classList.remove('hidden');
            scrollControls.classList.add('md:flex');
        } else {
            scrollControls.classList.add('hidden');
            scrollControls.classList.remove('md:flex');
        }
    }

    if (scrollBtns && scrollBtns.length >= 2) {
        scrollBtns[0].style.opacity = canScrollLeft ? '1' : '0.3';
        scrollBtns[1].style.opacity = canScrollRight ? '1' : '0.3';
        
        scrollBtns.forEach(btn => {
            btn.style.display = needsScroll ? 'flex' : 'none';
        });
    }
}

function scrollTabs(direction) {
    if (!tabsContainer) return;

    const scrollAmount = window.innerWidth <= 374 ? 120 : 
                        window.innerWidth <= 767 ? 140 : 
                        window.innerWidth <= 1023 ? 200 : 260;

    const target = direction === 'left' 
        ? Math.max(0, tabsContainer.scrollLeft - scrollAmount)
        : Math.min(tabsContainer.scrollWidth - tabsContainer.clientWidth, tabsContainer.scrollLeft + scrollAmount);

    if (tabsContainer.scrollLeft !== target) {
        tabsContainer.scrollTo({ left: target, behavior: 'smooth' });
    }
}

function setupTouchScroll(container) {
    let startX = 0;
    let isScrolling = false;
    let resizeTimeout;

    container.addEventListener('touchstart', (e) => {
        startX = e.touches[0].clientX;
        isScrolling = setTimeout(() => isScrolling = false, 300);
    }, { passive: true });

    container.addEventListener('touchmove', (e) => {
        if (!isScrolling) return;
        
        const diff = e.touches[0].clientX - startX;
        if (Math.abs(diff) > 50) {
            container.scrollBy({ left: diff > 0 ? -120 : 120, behavior: 'smooth' });
            startX = e.touches[0].clientX;
            clearTimeout(isScrolling);
            isScrolling = false;
        }
    }, { passive: true });

    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            updateTabScrollIndicators();
            if (window.innerWidth <= 767) setupTouchScroll(container);
        }, 150);
    });
}

if (tabsContainer) {
    setInterval(updateTabScrollIndicators, 500);
}

if (tabsContainer && window.innerWidth >= 768) {
    tabsContainer.addEventListener('wheel', (e) => {
        if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
            e.preventDefault();
            tabsContainer.scrollLeft += e.deltaX;
        }
    }, { passive: false });
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
        content.appendChild(document.importNode(htmlOrElement, true));
    }

    const scripts = content.querySelectorAll('script');
    scripts.forEach(oldScript => {
        const newScript = document.createElement('script');
        Array.from(oldScript.attributes).forEach(attr => newScript.setAttribute(attr.name, attr.value));
        newScript.appendChild(document.createTextNode(oldScript.innerHTML));
        oldScript.parentNode.replaceChild(newScript, oldScript);
    });

    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

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

    let targetUrl = form.getAttribute('action');
    if (!targetUrl || targetUrl === 'undefined' || targetUrl.includes('undefined')) {
        targetUrl = '/pacientes/nuevo/';
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (form.dataset.submitting === 'true') {
            return;
        }
        form.dataset.submitting = 'true';

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
            let currentActionUrl = form.getAttribute('action') || targetUrl;
            if (!currentActionUrl || currentActionUrl === 'undefined' || currentActionUrl.includes('undefined')) {
                currentActionUrl = targetUrl;
            }
            const resp = await fetch(currentActionUrl, {
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

                const successDiv = doc.getElementById('paciente-form-success');
                const formContent = doc.getElementById('paciente-form-content');

                if (successDiv) {
                    const pk = successDiv.getAttribute('data-pk');
                    closeModal();
                    if (pk) {
                        window.location.href = `/pacientes/${pk}/`;
                    } else {
                        refreshListaPacientes();
                    }
                } else if (formContent) {
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
            delete form.dataset.submitting;
        }
    });
}

async function toggleEstado(pk) {
    try {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || window.CSRF_TOKEN || '';

        const resp = await fetch(`/pacientes/${pk}/toggle/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
            },
        });

        if (resp.ok || resp.redirected) {
            if (document.getElementById('paciente-detail-content')) {
                window.location.reload();
            } else {
                refreshListaPacientes();
            }
        }
    } catch (err) {
        console.error('Error al cambiar estado:', err);
    }
}

let refreshCounter = 0;
async function refreshListaPacientes() {
    const oldContainer = document.getElementById('pacientes-list-container');
    const oldTable = document.getElementById('pacientes-table-body');

    if (!oldContainer && !oldTable) {
        location.reload();
        return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    refreshCounter++;
    urlParams.set('_refresh', refreshCounter);
    const url = '/pacientes/?' + urlParams.toString();

    try {
        const resp = await fetch(url);
        const html = await resp.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');

        const newContainer = doc.querySelector('#pacientes-list-container');
        const newTable = doc.querySelector('#pacientes-table-body');
        const newPagination = doc.querySelector('#pacientes-pagination');
        const newCounts = doc.querySelector('#pacientes-counts');
        const newTotalCount = doc.querySelector('#pacientes-total-count');
        const newActivosCount = doc.querySelector('#pacientes-activos-count');
        const newInactivosCount = doc.querySelector('#pacientes-inactivos-count');

        const oldPagination = document.getElementById('pacientes-pagination');
        const oldCounts = document.getElementById('pacientes-counts');
        const oldTotalCount = document.getElementById('pacientes-total-count');
        const oldActivosCount = document.getElementById('pacientes-activos-count');
        const oldInactivosCount = document.getElementById('pacientes-inactivos-count');

        if (oldContainer && newContainer) {
            oldContainer.replaceWith(document.importNode(newContainer, true));
        } else {

            if (oldTable && newTable) oldTable.replaceWith(document.importNode(newTable, true));
            if (oldPagination && newPagination) oldPagination.replaceWith(document.importNode(newPagination, true));
        }

        if (oldCounts && newCounts) {
            oldCounts.replaceWith(document.importNode(newCounts, true));
        }

        if (oldTotalCount && newTotalCount) oldTotalCount.textContent = newTotalCount.textContent;
        if (oldActivosCount && newActivosCount) oldActivosCount.textContent = newActivosCount.textContent;
        if (oldInactivosCount && newInactivosCount) oldInactivosCount.textContent = newInactivosCount.textContent;

        if (typeof lucide !== 'undefined') lucide.createIcons();
    } catch (err) {
        console.error('Error al refrescar lista:', err);
        location.reload();
    }
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');
    if (!sidebar) return;
    const isOpen = !sidebar.classList.contains('-translate-x-full');
    sidebar.classList.toggle('-translate-x-full');
    if (backdrop) {
        backdrop.classList.toggle('hidden', isOpen);
    }
    document.body.classList.toggle('overflow-hidden', !isOpen && window.innerWidth < SIDEBAR_BREAKPOINT);
    if (window.innerWidth < SIDEBAR_BREAKPOINT) {
        sidebar.dataset.mobileOpen = (!isOpen).toString();
    }
}

function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');
    if (!sidebar) return;
    sidebar.classList.add('-translate-x-full');
    sidebar.dataset.mobileOpen = 'false';
    if (backdrop) {
        backdrop.classList.add('hidden');
    }
    document.body.classList.remove('overflow-hidden');
}

document.addEventListener('DOMContentLoaded', () => {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    const menuBtn = document.getElementById('menu-btn');
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');
    const sidebarLinks = sidebar ? sidebar.querySelectorAll('a') : [];

    if (menuBtn && sidebar) {

        menuBtn.addEventListener('click', () => {
            toggleSidebar();
        });

        sidebarLinks.forEach(link => {
            link.addEventListener('click', () => {

                if (window.innerWidth < SIDEBAR_BREAKPOINT) {
                    closeSidebar();
                }
            });
        });
    }

    if (backdrop) {
        backdrop.addEventListener('click', closeSidebar);
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const sidebar = document.getElementById('sidebar');
            if (sidebar && !sidebar.classList.contains('-translate-x-full') && window.innerWidth < 1024) {
                closeSidebar();
            }
        }
    });

    window.addEventListener('resize', () => {
        const sidebar = document.getElementById('sidebar');
        const backdrop = document.getElementById('sidebar-backdrop');
        if (window.innerWidth >= SIDEBAR_BREAKPOINT) {
            if (sidebar) {
                sidebar.classList.remove('-translate-x-full');
                sidebar.dataset.mobileOpen = 'false';
            }
            if (backdrop) backdrop.classList.add('hidden');
            document.body.classList.remove('overflow-hidden');
        } else if (sidebar) {
            const mobileOpen = sidebar.dataset.mobileOpen === 'true';
            if (backdrop) backdrop.classList.toggle('hidden', !mobileOpen);
        }
    });

    const modalOverlay = document.getElementById('modal-overlay');
    if (modalOverlay) {
        let mousedownTarget = null;
        modalOverlay.addEventListener('mousedown', (e) => {
            mousedownTarget = e.target;
        });
        modalOverlay.addEventListener('click', (e) => {

            if (e.target === modalOverlay && mousedownTarget === modalOverlay && !window.getSelection().toString()) {
                closeModal();
            }
        });
    }
});

