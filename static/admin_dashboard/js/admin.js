const API_BASE = '/api/marketplace';
const SCRAPE_API = '/api/scrape';

// ─── App State ────────────────────────────────────────────────────────────────
let state = {
    vendors: [],
    products: [],
    categories: [],
    customers: [],
    guests: [],
    favorites: [],
    analytics: null,
    activeView: 'dashboard',
    kycVendorId: null,
    pageSize: 10,
    currentPage: {}
};

// ─── Bootstrap ───────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    await fetchData();
    renderDashboard();
    lucide.createIcons();
    setupEventListeners();
    setupAutoDiscount();
});

// ─── Fetch all data ───────────────────────────────────────────────────────────
async function fetchData() {
    const token = localStorage.getItem('auth_token');
    const authHdr = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };

    try {
        const [vendorRes, productRes, catRes, customerRes, guestRes, favRes, analyticsRes] = await Promise.all([
            fetch(`${API_BASE}/admin/vendors/`, { headers: authHdr }),
            fetch(`${API_BASE}/admin/products/`, { headers: authHdr }),
            fetch(`${API_BASE}/admin/categories/`, { headers: authHdr }),
            fetch(`${API_BASE}/admin/customers/`, { headers: authHdr }),
            fetch(`${API_BASE}/admin/guests/`, { headers: authHdr }),
            fetch(`${API_BASE}/admin/favorites/`, { headers: authHdr }),
            fetch(`${API_BASE}/admin/analytics/`, { headers: authHdr })
        ]);

        if (vendorRes.status === 401) {
            localStorage.removeItem('auth_token');
            window.location.href = '/admin/login/';
            return;
        }

        state.vendors = (await vendorRes.json()).sort((a, b) => a.id - b.id);
        state.products = (productRes.ok ? await productRes.json() : []).sort((a, b) => a.id - b.id);
        state.categories = (catRes.ok ? await catRes.json() : []).sort((a, b) => a.id - b.id);
        state.customers = (customerRes.ok ? await customerRes.json() : []).sort((a, b) => a.id - b.id);
        state.guests = (guestRes.ok ? await guestRes.json() : []);
        state.favorites = (favRes.ok ? await favRes.json() : []);
        state.analytics = (analyticsRes.ok ? await analyticsRes.json() : null);

        updateStats();
        if (state.analytics) renderCharts();
    } catch (err) {
        console.error('fetchData error:', err);
        showToast('Failed to load data from server', 'error');
    }
}

// ─── Stats ────────────────────────────────────────────────────────────────────
function updateStats() {
    if (!state.analytics) {
        document.getElementById('count-vendors').textContent = state.vendors.length;
        document.getElementById('count-products').textContent = state.products.length;
        document.getElementById('count-pending').textContent = state.vendors.filter(v => !v.is_approved).length;
        return;
    }
    const s = state.analytics.stats;
    document.getElementById('count-vendors').textContent = s.total_vendors;
    document.getElementById('count-active-vendors').textContent = s.active_vendors;
    document.getElementById('count-pending').textContent = s.pending_kyc;
    document.getElementById('count-products').textContent = s.total_products;
    document.getElementById('count-customers').textContent = s.total_customers;
    document.getElementById('count-guests').textContent = s.total_guests;
}

// ─── Charts ──────────────────────────────────────────────────────────────────
let charts = {};
function renderCharts() {
    if (!state.analytics) return;
    const ctxV = document.getElementById('vendorGrowthChart')?.getContext('2d');
    const ctxP = document.getElementById('productPostsChart')?.getContext('2d');
    const ctxU = document.getElementById('userGrowthChart')?.getContext('2d');

    if (charts.vendor) charts.vendor.destroy();
    if (charts.product) charts.product.destroy();
    if (charts.user) charts.user.destroy();

    const config = (label, labels, data) => ({
        type: 'line',
        data: { labels, datasets: [{ label, data, borderColor: '#6366f1', tension: 0.4, fill: true, backgroundColor: 'rgba(99,102,241,0.1)' }] },
        options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
    });

    if (ctxV) charts.vendor = new Chart(ctxV, config('Vendors', state.analytics.vendor_growth.map(g => g.month), state.analytics.vendor_growth.map(g => g.count)));
    if (ctxP) charts.product = new Chart(ctxP, config('Products', state.analytics.product_posts.map(g => g.day), state.analytics.product_posts.map(g => g.count)));
    if (ctxU) {
        charts.user = new Chart(ctxU, {
            type: 'bar',
            data: {
                labels: state.analytics.user_growth.map(g => g.month),
                datasets: [
                    { label: 'Customers', data: state.analytics.user_growth.map(g => g.customers), backgroundColor: '#6366f1' },
                    { label: 'Guests', data: state.analytics.user_growth.map(g => g.guests), backgroundColor: '#94a3b8' }
                ]
            },
            options: { responsive: true, scales: { y: { beginAtZero: true } } }
        });
    }
}

// ─── Pagination Helper ───────────────────────────────────────────────────────
function renderPagination(containerId, totalItems, viewKey) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const totalPages = Math.ceil(totalItems / state.pageSize);
    const currentPage = state.currentPage[viewKey] || 1;

    if (totalPages <= 1) {
        container.innerHTML = '';
        container.style.display = 'none';
        return;
    }

    container.style.display = 'flex';
    const start = (currentPage - 1) * state.pageSize + 1;
    const end = Math.min(currentPage * state.pageSize, totalItems);

    const chevLeft = `<svg viewBox="0 0 24 24"><polyline points="15 18 9 12 15 6"/></svg>`;
    const chevRight = `<svg viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6"/></svg>`;

    const pages = [];
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 1 && i <= currentPage + 1)) {
            pages.push(i);
        } else if (i === currentPage - 2 || i === currentPage + 2) {
            pages.push('...');
        }
    }

    let btns = '';
    let lastWasEllipsis = false;
    pages.forEach(p => {
        if (p === '...') {
            if (!lastWasEllipsis) btns += `<span class="pagination-ellipsis">···</span>`;
            lastWasEllipsis = true;
        } else {
            lastWasEllipsis = false;
            btns += `<button class="page-btn ${p === currentPage ? 'active' : ''}" onclick="changePage('${viewKey}', ${p})">${p}</button>`;
        }
    });

    container.innerHTML = `
        <div class="pagination-info">Showing <span>${start}</span> to <span>${end}</span> of <span>${totalItems}</span> results</div>
        <div class="pagination-controls">
            <button class="page-btn" ${currentPage === 1 ? 'disabled' : ''} onclick="changePage('${viewKey}', ${currentPage - 1})">${chevLeft}</button>
            ${btns}
            <button class="page-btn" ${currentPage === totalPages ? 'disabled' : ''} onclick="changePage('${viewKey}', ${currentPage + 1})">${chevRight}</button>
        </div>`;

    lucide.createIcons();
}

function changePage(viewKey, newPage) {
    state.currentPage[viewKey] = newPage;

    const renderMap = {
        'recent': renderDashboard,
        'kyc': renderKYC,
        'vendors': renderVendors,
        'products': renderProducts,
        'customers': renderCustomers,
        'guests': renderGuests,
        'categories': renderCategories,
        'favorites': renderFavorites
    };

    if (renderMap[viewKey]) {
        renderMap[viewKey]();
    }
}

// ─── Render: Dashboard ────────────────────────────────────────────────────────
function renderDashboard() {
    const tbody = document.querySelector('#recent-vendors-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const page = state.currentPage['recent'] || 1;
    const start = (page - 1) * state.pageSize;
    const items = state.vendors.slice(start, start + state.pageSize);

    items.forEach(v => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>
                <div class="vendor-info">
                    <div class="vendor-avatar">${(v.brand_name || 'V')[0]}</div>
                    <div>
                        <div style="font-weight:600">${v.brand_name || 'N/A'}</div>
                        <div style="font-size:0.75rem;color:var(--text-secondary)">Joined ${new Date(v.created_at).toLocaleDateString()}</div>
                    </div>
                </div>
            </td>
            <td>${v.email}</td>
            <td><span class="status-badge ${v.is_approved ? 'status-approved' : 'status-pending'}">
                ${v.is_approved ? 'Approved' : 'Pending'}</span></td>
            <td>
                <button onclick="switchView('vendors')" class="btn btn-secondary">Manage</button>
            </td>`;
        tbody.appendChild(tr);
    });
    renderPagination('recent-vendors-pagination', state.vendors.length, 'recent');
}

// ─── Render: KYC ──────────────────────────────────────────────────────────────
function renderKYC() {
    const tbody = document.querySelector('#pending-kyc-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    const pending = state.vendors.filter(v => v.kyc_status === 'PENDING' && !v.is_approved);

    if (!pending.length) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">No pending requests</td></tr>';
        document.getElementById('kyc-pagination').style.display = 'none';
        return;
    }

    const page = state.currentPage['kyc'] || 1;
    const start = (page - 1) * state.pageSize;
    const items = pending.slice(start, start + state.pageSize);

    items.forEach(v => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${v.brand_name || 'N/A'}</td>
            <td>${v.email}</td>
            <td>${v.phone || 'N/A'}</td>
            <td>${new Date(v.created_at).toLocaleDateString()}</td>
            <td>
                <button onclick="openKYCModal(${v.id})" class="btn btn-primary">Review Profile</button>
            </td>`;
        tbody.appendChild(tr);
    });
    renderPagination('kyc-pagination', pending.length, 'kyc');
}

// openKYCModal moved to bottom to avoid duplication and match HTML

// ─── Render: Vendors ──────────────────────────────────────────────────────────
function renderVendors() {
    const tbody = document.querySelector('#all-vendors-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const page = state.currentPage['vendors'] || 1;
    const start = (page - 1) * state.pageSize;
    const items = state.vendors.slice(start, start + state.pageSize);

    items.forEach(v => {
        const tr = document.createElement('tr');
        const logoUrl = v.logo || '';
        const avatarHtml = logoUrl 
            ? `<img src="${logoUrl}" class="vendor-avatar" style="object-fit:cover;">`
            : `<div class="vendor-avatar">${(v.brand_name || 'V')[0]}</div>`;
            
        tr.innerHTML = `
            <td>${v.id}</td>
            <td>
                <div class="vendor-info">
                    ${avatarHtml}
                    <span>${v.brand_name || 'N/A'}</span>
                </div>
            </td>
            <td>${v.email}</td>
            <td>
                <span class="status-badge ${v.is_approved ? 'status-approved' : 'status-pending'}">KYC: ${v.is_approved ? 'Appr' : 'Pend'}</span>
                <span class="status-badge ${v.is_active ? 'status-active' : 'status-pending'}" style="margin-left:4px">${v.is_active ? 'Active' : 'Banned'}</span>
            </td>
            <td>${v.product_count || 0}</td>
            <td>
                <div style="display:flex;gap:.5rem;">
                    <button onclick="toggleVendorActive(${v.id})" class="btn ${v.is_active ? 'btn-secondary' : 'btn-primary'}">${v.is_active ? 'Ban' : 'Activate'}</button>
                    <button onclick="openEditVendorModal(${v.id})" class="btn btn-secondary">Edit</button>
                </div>
            </td>`;
        tbody.appendChild(tr);
    });
    renderPagination('vendors-pagination', state.vendors.length, 'vendors');
}

// ─── Render: Products ─────────────────────────────────────────────────────────
function renderProducts() {
    const tbody = document.querySelector('#all-products-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const page = state.currentPage['products'] || 1;
    const start = (page - 1) * state.pageSize;
    const items = state.products.slice(start, start + state.pageSize);

    items.forEach(p => {
        const tr = document.createElement('tr');
        const catText = p.subcategory_name 
            ? `${p.category_name} > <small>${p.subcategory_name}</small>` 
            : (p.category_name || 'Uncategorized');
            
        tr.innerHTML = `
            <td><strong>${p.name || 'N/A'}</strong></td>
            <td>${p.vendor_name || 'System'}</td>
            <td>$${parseFloat(p.price || 0).toFixed(2)}</td>
            <td>${catText}</td>
            <td><span class="status-badge ${p.is_active ? 'status-approved' : 'status-pending'}">${p.is_active ? 'Active' : 'Hidden'}</span></td>
            <td>
                <div style="display:flex;gap:.5rem;">
                    <button onclick="toggleProduct(${p.id})" class="btn btn-secondary">${p.is_active ? 'Hide' : 'Show'}</button>
                    <button onclick="deleteProduct(${p.id})" class="btn btn-secondary" style="color:var(--danger)">Delete</button>
                </div>
            </td>`;
        tbody.appendChild(tr);
    });
    renderPagination('products-pagination', state.products.length, 'products');
}

// ─── Render: Customers ────────────────────────────────────────────────────────
function renderCustomers() {
    const tbody = document.querySelector('#all-customers-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const page = state.currentPage['customers'] || 1;
    const start = (page - 1) * state.pageSize;
    const items = state.customers.slice(start, start + state.pageSize);

    items.forEach(c => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${c.id}</td>
            <td>${c.first_name} ${c.last_name}</td>
            <td>${c.email}</td>
            <td>${new Date(c.signup_date).toLocaleDateString()}</td>
            <td><span class="status-badge ${c.is_active ? 'status-approved' : 'status-pending'}">${c.is_active ? 'Active' : 'Blocked'}</span></td>
            <td>
                <button onclick="blockCustomer(${c.id})" class="btn ${c.is_active ? 'btn-secondary' : 'btn-primary'}">
                    ${c.is_active ? 'Block' : 'Unblock'}
                </button>
            </td>`;
        tbody.appendChild(tr);
    });
    renderPagination('customers-pagination', state.customers.length, 'customers');
}

// ─── Render: Guests ───────────────────────────────────────────────────────────
function renderGuests() {
    const tbody = document.querySelector('#all-guests-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const page = state.currentPage['guests'] || 1;
    const start = (page - 1) * state.pageSize;
    const items = state.guests.slice(start, start + state.pageSize);

    items.forEach(g => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td title="${g.device_id}">${g.device_id.substring(0, 8)}...</td>
            <td>${new Date(g.first_visit).toLocaleDateString()}</td>
            <td>${g.last_active ? new Date(g.last_active).toLocaleString() : '—'}</td>
            <td>${g.favorites_count}</td>`;
        tbody.appendChild(tr);
    });
    renderPagination('guests-pagination', state.guests.length, 'guests');
}

// ─── Render: Favorites ────────────────────────────────────────────────────────
function renderFavorites() {
    const tbody = document.querySelector('#all-favorites-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const page = state.currentPage['favorites'] || 1;
    const start = (page - 1) * state.pageSize;
    const items = state.favorites.slice(start, start + state.pageSize);

    items.forEach(f => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${f.name}</td>
            <td>${f.vendor_name}</td>
            <td><strong>${f.favorites_count}</strong></td>
            <td>${f.unique_users_count}</td>`;
        tbody.appendChild(tr);
    });
    renderPagination('favorites-pagination', state.favorites.length, 'favorites');
}

// ─── Render: Categories ───────────────────────────────────────────────────────
function renderCategories() {
    const tbody = document.querySelector('#all-categories-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const page = state.currentPage['categories'] || 1;
    const start = (page - 1) * state.pageSize;
    const items = state.categories.slice(start, start + state.pageSize);

    items.forEach(cat => {
        const subcatTags = (cat.subcategories || []).map(sc => `
            <div style="display:flex; align-items:center; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.1); padding:0.25rem 0.5rem; border-radius:4px; gap:0.5rem;">
                <span style="flex:1; font-size:0.85rem;">${sc.name}</span>
                <button onclick="openEditSubcategoryModal(${sc.id})" class="btn btn-secondary" style="padding:0.2rem 0.4rem; font-size:0.7rem;" title="Edit Subcategory">Edit</button>
                <button onclick="deleteSubcategory(${sc.id})" class="btn btn-secondary" style="padding:0.2rem 0.4rem; font-size:0.7rem; color:var(--danger);" title="Delete Subcategory">Delete</button>
            </div>
        `).join('') || '<span style="color:var(--text-secondary);font-size:0.8rem;">No subcategories</span>';

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${cat.id}</td>
            <td><strong>${cat.name}</strong></td>
            <td>
                <div style="display:flex; flex-direction:column; gap:0.25rem;">
                    ${subcatTags}
                </div>
            </td>
            <td><span class="status-badge ${cat.is_active ? 'status-approved' : 'status-pending'}">${cat.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>
                <div style="display:flex;gap:.5rem;">
                    <button onclick="toggleCategory(${cat.id})" class="btn ${cat.is_active ? 'btn-secondary' : 'btn-primary'}">${cat.is_active ? 'Disable' : 'Enable'}</button>
                    <button onclick="openSubModalFor(${cat.id})" class="btn btn-primary" title="Add Subcategory">
                        <i data-lucide="plus-circle" style="width:14px;height:14px;"></i>
                    </button>
                    <button onclick="openEditCategoryModal(${cat.id})" class="btn btn-secondary">Edit</button>
                    <button onclick="deleteCategory(${cat.id})" class="btn btn-secondary" style="color:var(--danger)">Delete</button>
                </div>
            </td>`;
        tbody.appendChild(tr);
    });
    renderPagination('categories-pagination', state.categories.length, 'categories');
    if (window.lucide) lucide.createIcons();
}

// ─── View switcher ────────────────────────────────────────────────────────────
function switchView(view) {
    state.activeView = view;
    document.querySelectorAll('.nav-item').forEach(el => {
        el.classList.toggle('active', el.getAttribute('data-view') === view);
    });
    document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
    document.getElementById(`${view}-view`).classList.add('active');

    // Update Header Title
    const titleMap = {
        'dashboard': 'Dashboard Overview',
        'kyc': 'KYC Verification',
        'vendors': 'Vendor Management',
        'products': 'Product Catalog',
        'categories': 'Category Management',
        'customers': 'Customer Base',
        'guests': 'Guest Sessions',
        'analytics': 'System Analytics',
        'settings': 'Global Settings'
    };
    const headerTitle = document.querySelector('.header-left h1');
    if (headerTitle && titleMap[view]) {
        headerTitle.textContent = titleMap[view];
    }

    if (view === 'dashboard') renderDashboard();
    if (view === 'vendors') renderVendors();
    if (view === 'kyc') renderKYC();
    if (view === 'products') renderProducts();
    if (view === 'categories') renderCategories();
    if (view === 'customers') renderCustomers();
    if (view === 'guests') renderGuests();
    if (view === 'favorites') renderFavorites();
    if (view === 'analytics') renderCharts();
    if (view === 'settings') loadSettings();

    lucide.createIcons();
}

async function openEditVendorModal(id) {
    const v = state.vendors.find(v => v.id === id);
    if (!v) return;
    const m = document.getElementById('editVendorModal');
    const f = document.getElementById('editVendorForm');
    f.vendor_id.value = v.id;
    f.brand_name.value = v.brand_name || '';
    f.email.value = v.email || '';
    f.phone.value = v.phone || '';
    f.business_address.value = v.business_address || '';
    m.style.display = 'flex';
    lucide.createIcons();
}

// ─── Actions: Vendors ─────────────────────────────────────────────────────────
async function toggleVendorActive(id) {
    const token = localStorage.getItem('auth_token');
    const res = await fetch(`${API_BASE}/admin/vendors/${id}/toggle/`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } });
    if (res.ok) { showToast('Vendor status updated'); await fetchData(); renderVendors(); }
}

async function deleteVendor(id) {
    if (!confirm('Delete this vendor?')) return;
    const token = localStorage.getItem('auth_token');
    const res = await fetch(`${API_BASE}/admin/vendors/${id}/delete/`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } });
    if (res.ok) { showToast('Vendor deleted'); await fetchData(); renderVendors(); }
}

// ─── Actions: Products ────────────────────────────────────────────────────────
async function toggleProduct(id) {
    const token = localStorage.getItem('auth_token');
    const res = await fetch(`${API_BASE}/admin/products/${id}/toggle/`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } });
    if (res.ok) { showToast('Product visibility updated'); await fetchData(); renderProducts(); }
}

// ─── Actions: Customers ───────────────────────────────────────────────────────
async function blockCustomer(id) {
    const token = localStorage.getItem('auth_token');
    const res = await fetch(`/api/auth/admin/customers/${id}/block/`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } });
    if (res.ok) { showToast('Customer status updated'); await fetchData(); renderCustomers(); }
}

// ─── Actions: Categories ──────────────────────────────────────────────────────
async function toggleCategory(id) {
    const token = localStorage.getItem('auth_token');
    const res = await fetch(`${API_BASE}/admin/categories/${id}/toggle/`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } });
    if (res.ok) { showToast('Category status updated'); await fetchData(); renderCategories(); }
}

async function deleteCategory(id) {
    if (!confirm('Delete this category?')) return;
    try {
        const res = await fetch(`${API_BASE}/admin/categories/${id}/delete/`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } });
        if (res.ok) { showToast('Category deleted'); await fetchData(); renderCategories(); }
    } catch (e) { showToast('Error deleting category', 'error'); }
}

async function deleteSubcategory(id) {
    if (!confirm('Delete this subcategory?')) return;
    const token = localStorage.getItem('auth_token');
    try {
        const res = await fetch(`${API_BASE}/admin/subcategories/${id}/delete/`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            showToast('Subcategory deleted');
            const m = document.getElementById('editSubcategoryModal');
            if (m) m.style.display = 'none';
            await fetchData();
            renderCategories();
        } else {
            showToast('Failed to delete subcategory', 'error');
        }
    } catch (ex) { showToast('Network error', 'error'); }
}

function openSubModalFor(categoryId) {
    const subcatCategorySel = document.getElementById('subcategory-category-select');
    if (subcatCategorySel) {
        subcatCategorySel.innerHTML = '<option value="">-- Select Category --</option>';
        state.categories.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id; opt.textContent = c.name;
            if (String(c.id) === String(categoryId)) opt.selected = true;
            subcatCategorySel.appendChild(opt);
        });
    }
    const subcatModal = document.getElementById('createSubcategoryModal');
    if (subcatModal) subcatModal.style.display = 'flex';
    if (window.lucide) lucide.createIcons();
}

// ─── Analytics & Export ───────────────────────────────────────────────────────
function exportReport(type) {
    const token = localStorage.getItem('auth_token');
    window.location.href = `${API_BASE}/admin/export/${type}/?auth_token=${token}`;
}

// ─── Settings ─────────────────────────────────────────────────────────────────
async function loadSettings() {
    const token = localStorage.getItem('auth_token');
    const [sysRes, popRes] = await Promise.all([
        fetch('/api/auth/admin/system-settings/', { headers: { 'Authorization': `Bearer ${token}` } }),
        fetch('/api/auth/admin/popup-settings/', { headers: { 'Authorization': `Bearer ${token}` } })
    ]);
    if (sysRes.ok) {
        const sys = await sysRes.json();
        const f = document.getElementById('systemSettingsForm');
        f.platform_name.value = sys.platform_name;
    }
    if (popRes.ok) {
        const pop = await popRes.json();
        const f = document.getElementById('popupSettingsForm');
        f.popup_delay_days.value = pop.popup_delay_days;
        f.message.value = pop.message;
        f.cta_text.value = pop.cta_text;
        f.enabled.value = pop.enabled.toString();
    }
}

// ─── Approve / Revoke Vendor ──────────────────────────────────────────────────
// ─── Approve / Reject Vendor ──────────────────────────────────────────────────
async function approveVendor(vendorId, status, reason = '') {
    const token = localStorage.getItem('auth_token');
    const btn = document.getElementById('kyc-approve-btn');

    if (btn) { btn.disabled = true; btn.textContent = 'Processing...'; }

    try {
        const res = await fetch(`${API_BASE}/admin/approve-vendor/`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ vendor_id: vendorId, status, reason })
        });
        if (res.ok) {
            showToast(`Vendor ${status.toLowerCase()} successfully`);
            const modal = document.getElementById('kycModal');
            if (modal) modal.style.display = 'none';
            state.kycVendorId = null;
            await fetchData();
            renderDashboard();
            if (state.activeView === 'vendors') renderVendors();
            if (state.activeView === 'kyc') renderKYC();
        } else {
            showToast('Failed to update vendor status', 'error');
        }
    } catch (ex) {
        showToast('Network error', 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Approve Vendor'; }
    }
}

// ─── KYC Modal ────────────────────────────────────────────────────────────────
async function openKYCModal(vendorId) {
    state.kycVendorId = vendorId;
    const token = localStorage.getItem('auth_token');
    const modal = document.getElementById('kycModal');

    try {
        const res = await fetch(`${API_BASE}/admin/vendors/${vendorId}/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) { showToast('Failed to load KYC data', 'error'); return; }
        const data = await res.json();

        // Match HTML IDs exactly
        document.getElementById('kyc-brand-name').textContent = data.brand_name || 'N/A';
        document.getElementById('kyc-email').textContent = data.kyc?.email || data.email || 'N/A';
        document.getElementById('kyc-phone').textContent = data.kyc?.phone || 'N/A';
        document.getElementById('kyc-address').textContent = data.kyc?.address || 'N/A';

        // Logo handling
        const logoImg = document.getElementById('kyc-logo-preview');
        const noLogo = document.getElementById('kyc-no-logo');
        if (data.kyc?.logo) {
            logoImg.src = data.kyc.logo;
            logoImg.style.display = 'block';
            if (noLogo) noLogo.style.display = 'none';
        } else {
            logoImg.style.display = 'none';
            if (noLogo) noLogo.style.display = 'block';
        }

        // Action Buttons
        const approveBtn = document.getElementById('kyc-approve-btn');
        const rejectBtn = document.getElementById('kyc-reject-btn');

        approveBtn.dataset.vendorId = vendorId;
        rejectBtn.dataset.vendorId = vendorId;

        // Update button text based on current status
        approveBtn.textContent = data.is_approved ? 'Already Approved' : 'Approve Vendor';
        approveBtn.disabled = data.is_approved;

        modal.style.display = 'flex';
        lucide.createIcons();
    } catch (e) {
        console.error('KYC Load Error:', e);
        showToast('Error loading KYC details', 'error');
    }
}

// ─── Add Product Modal ────────────────────────────────────────────────────────
function openAddProductModal(preselectedVendorId = null) {
    // Populate vendor dropdown
    const vendorSel = document.getElementById('product-vendor-select');
    vendorSel.innerHTML = '<option value="">-- Select Vendor --</option>';
    state.vendors.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v.id;
        opt.textContent = `${v.brand_name || v.username} (ID: ${v.id})`;
        vendorSel.appendChild(opt);
    });
    if (preselectedVendorId) vendorSel.value = preselectedVendorId;

    const catSel = document.getElementById('product-category-select');
    const subcatGroup = document.getElementById('product-subcategory-group');
    const subcatSel = document.getElementById('product-subcategory-select');
    const addForm = document.getElementById('addProductForm');

    const populateSubcategories = (categoryId) => {
        const category = state.categories.find(c => String(c.id) === String(categoryId));
        subcatSel.innerHTML = '<option value="">-- Select Subcategory --</option>';
        if (category && Array.isArray(category.subcategories) && category.subcategories.length) {
            category.subcategories.forEach(sc => {
                const opt = document.createElement('option');
                opt.value = sc.id;
                opt.textContent = sc.name;
                subcatSel.appendChild(opt);
            });
            subcatSel.required = true;
            subcatGroup.style.display = 'block';
        } else {
            subcatSel.required = false;
            subcatGroup.style.display = 'none';
        }
    };

    catSel.innerHTML = '<option value="">-- Select Category --</option>';
    state.categories.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.id;
        opt.textContent = c.name;
        catSel.appendChild(opt);
    });

    catSel.onchange = () => populateSubcategories(catSel.value);

    if (addForm) {
        addForm.reset();
    }
    subcatSel.innerHTML = '<option value="">-- Select Subcategory --</option>';
    subcatSel.required = false;
    subcatGroup.style.display = 'none';

    if (preselectedVendorId) {
        vendorSel.value = preselectedVendorId;
    }

    document.getElementById('kycModal').style.display = 'none';
    document.getElementById('addProductModal').style.display = 'flex';
    lucide.createIcons();
}

// ─── Auto-compute discount % ──────────────────────────────────────────────────
function setupAutoDiscount() {
    const form = document.getElementById('addProductForm');
    function recalc() {
        const orig = parseFloat(form.querySelector('[name=original_price]').value);
        const disc = parseFloat(form.querySelector('[name=price]').value);
        if (orig > 0 && disc > 0 && disc < orig) {
            form.querySelector('[name=discount]').value =
                ((orig - disc) / orig * 100).toFixed(2);
        }
    }
    form.querySelector('[name=original_price]').addEventListener('input', recalc);
    form.querySelector('[name=price]').addEventListener('input', recalc);
}

// ─── Delete Product ───────────────────────────────────────────────────────────
async function deleteProduct(productId) {
    if (!confirm('Delete this product? This cannot be undone.')) return;
    const token = localStorage.getItem('auth_token');
    try {
        const res = await fetch(`${API_BASE}/admin/products/${productId}/`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            showToast('Product deleted', 'success');
            await fetchData();
            renderProducts();
        } else {
            showToast('Failed to delete product', 'error');
        }
    } catch (e) {
        showToast('Network error', 'error');
    }
}

// ─── Toast ────────────────────────────────────────────────────────────────────
function showToast(msg, type = 'success') {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = `toast toast-${type} show`;
    setTimeout(() => t.classList.remove('show'), 3500);
}

// ─── Event listeners ──────────────────────────────────────────────────────────
function setupEventListeners() {
    const safeSetClick = (id, fn) => {
        const el = document.getElementById(id);
        if (el) el.onclick = fn;
    };
    const safeSetSubmit = (id, fn) => {
        const el = document.getElementById(id);
        if (el) el.onsubmit = fn;
    };

    // Navigation
    document.querySelectorAll('.nav-item').forEach(el =>
        el.addEventListener('click', () => {
            const view = el.getAttribute('data-view');
            if (view) {
                switchView(view);
                const sb = document.getElementById('sidebar');
                if (sb) sb.classList.remove('open');
            }
        })
    );

    // Sidebar Toggle for Mobile
    safeSetClick('menuToggle', () => {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) sidebar.classList.toggle('open');
    });

    // Set Current Date
    const dateDisplay = document.getElementById('current-date-display');
    if (dateDisplay) {
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        dateDisplay.textContent = new Date().toLocaleDateString(undefined, options);
    }

    // ── Create Vendor Modal ──
    safeSetClick('openCreateVendorBtn', () => {
        const vModal = document.getElementById('createVendorModal');
        if (vModal) { vModal.style.display = 'flex'; if (window.lucide) lucide.createIcons(); }
    });

    safeSetSubmit('createVendorForm', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const token = localStorage.getItem('auth_token');
        const btn = e.target.querySelector('[type=submit]');
        
        // Coordinates validation
        const lat = parseFloat(formData.get('latitude'));
        const lng = parseFloat(formData.get('longitude'));
        if (formData.get('latitude') && (isNaN(lat) || lat < -90 || lat > 90)) {
            showToast('Latitude must be between -90 and 90', 'error');
            return;
        }
        if (formData.get('longitude') && (isNaN(lng) || lng < -180 || lng > 180)) {
            showToast('Longitude must be between -180 and 180', 'error');
            return;
        }

        if (btn) { btn.disabled = true; btn.textContent = 'Creating…'; }
        try {
            const res = await fetch(`${API_BASE}/admin/create-vendor/`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }, // No Content-Type for FormData
                body: formData
            });
            if (res.ok) {
                showToast('Vendor created & auto-approved!', 'success');
                const vModal = document.getElementById('createVendorModal');
                if (vModal) vModal.style.display = 'none';
                e.target.reset();
                await fetchData();
                renderDashboard();
                if (state.activeView === 'vendors') renderVendors();
            } else {
                const err = await res.json();
                showToast('Error: ' + (err.error || JSON.stringify(err)), 'error');
            }
        } catch (ex) {
            showToast('Network error', 'error');
        } finally {
            if (btn) { btn.disabled = false; btn.textContent = 'Create & Auto-Approve'; }
        }
    });

    // ── Edit Vendor Modal ──
    safeSetSubmit('editVendorForm', async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target));
        const token = localStorage.getItem('auth_token');
        const btn = e.target.querySelector('[type=submit]');
        if (btn) { btn.disabled = true; btn.textContent = 'Saving...'; }
        try {
            const res = await fetch(`${API_BASE}/admin/vendors/${data.vendor_id}/edit/`, {
                method: 'PATCH',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (res.ok) {
                showToast('Vendor updated successfully');
                const evModal = document.getElementById('editVendorModal');
                if (evModal) evModal.style.display = 'none';
                await fetchData();
                renderVendors();
            } else {
                showToast('Failed to update vendor', 'error');
            }
        } catch (ex) { showToast('Network error', 'error'); }
        finally { if (btn) { btn.disabled = false; btn.textContent = 'Save Changes'; } }
    });

    // ── Add Product Modal ──
    safeSetClick('openAddProductBtn', () => openAddProductModal());

    safeSetSubmit('addProductForm', async (e) => {
        e.preventDefault();
        const raw = Object.fromEntries(new FormData(e.target));
        const token = localStorage.getItem('auth_token');
        const btn = e.target.querySelector('[type=submit]');

        const imagesRaw = (raw.images_raw || '').trim();
        const images = imagesRaw ? imagesRaw.split('\n').map(u => u.trim()).filter(Boolean) : [];
        delete raw.images_raw;
        raw.images = images;

        if (parseFloat(raw.price) >= parseFloat(raw.original_price)) {
            showToast('Discounted price must be lower than original price', 'error');
            return;
        }
        if (!raw.vendor_id) {
            showToast('Please select a vendor', 'error');
            return;
        }
        if (raw.category) {
            const selectedCategory = state.categories.find(c => String(c.id) === String(raw.category));
            if (selectedCategory?.subcategories?.length && !raw.subcategory) {
                showToast('Please select a subcategory for this category', 'error');
                return;
            }
        }
        if (!raw.subcategory) delete raw.subcategory;

        if (btn) { btn.disabled = true; btn.textContent = 'Posting…'; }
        try {
            const res = await fetch(`${API_BASE}/admin/post-on-behalf/`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify(raw)
            });
            if (res.ok) {
                showToast('Product posted successfully!');
                const pModal = document.getElementById('addProductModal');
                if (pModal) pModal.style.display = 'none';
                e.target.reset();
                await fetchData();
                if (state.activeView === 'products') renderProducts();
                updateStats();
            } else {
                const err = await res.json();
                showToast('Error: ' + JSON.stringify(err), 'error');
            }
        } catch (ex) {
            showToast('Network error', 'error');
        } finally {
            if (btn) { btn.disabled = false; btn.textContent = 'Post Product'; }
        }
    });

    // ── KYC Modal Actions ──
    safeSetClick('kyc-approve-btn', async function () {
        if (state.kycVendorId) await approveVendor(state.kycVendorId, 'APPROVED');
    });
    safeSetClick('kyc-reject-btn', async function () {
        const reason = document.getElementById('kyc-rejection-reason')?.value;
        if (!reason) {
            showToast('Please provide a reason for rejection', 'error');
            return;
        }
        if (state.kycVendorId) await approveVendor(state.kycVendorId, 'REJECTED', reason);
    });

    // ── Create Category Modal ──
    safeSetClick('openCreateCategoryBtn', () => {
        const catModal = document.getElementById('createCategoryModal');
        if (catModal) { catModal.style.display = 'flex'; if (window.lucide) lucide.createIcons(); }
    });

    safeSetSubmit('createCategoryForm', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = {
            name: formData.get('name'),
            subcategories: formData.getAll('subcategories[]').filter(s => s.trim() !== '')
        };
        const token = localStorage.getItem('auth_token');
        const btn = e.target.querySelector('[type=submit]');
        if (btn) { btn.disabled = true; btn.textContent = 'Creating…'; }
        try {
            const res = await fetch(`${API_BASE}/categories/create/`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (res.ok) {
                showToast('Category created!');
                const catModal = document.getElementById('createCategoryModal');
                if (catModal) catModal.style.display = 'none';
                e.target.reset();
                
                // Reset subcategory inputs to one empty row
                const container = document.getElementById('subcategory-inputs-container');
                if (container) {
                    const rows = container.querySelectorAll('.subcategory-row');
                    rows.forEach((row, idx) => {
                        if (idx > 0) row.remove();
                        else {
                            const inp = row.querySelector('input');
                            if (inp) inp.value = '';
                            const rb = row.querySelector('.remove-sub-btn');
                            if (rb) rb.style.display = 'none';
                        }
                    });
                }

                await fetchData();
                if (state.activeView === 'categories') renderCategories();
            } else {
                const err = await res.json();
                showToast('Error: ' + (err.error || JSON.stringify(err)), 'error');
            }
        } catch (ex) {
            showToast('Network error', 'error');
        } finally {
            if (btn) { btn.disabled = false; btn.textContent = 'Create Category'; }
        }
    });

    // Create Subcategory Modal
    const openSubBtn = document.getElementById('openCreateSubcategoryBtn');
    if (openSubBtn) {
        openSubBtn.addEventListener('click', () => {
            const subcatCategorySel = document.getElementById('subcategory-category-select');
            if (subcatCategorySel) {
                subcatCategorySel.innerHTML = '<option value="">-- Select Category --</option>';
                state.categories.forEach(c => {
                    const opt = document.createElement('option');
                    opt.value = c.id; opt.textContent = c.name;
                    subcatCategorySel.appendChild(opt);
                });
            }
            const subcatModal = document.getElementById('createSubcategoryModal');
            if (subcatModal) subcatModal.style.display = 'flex';
            if (window.lucide) lucide.createIcons();
        });
    }

    safeSetSubmit('createSubcategoryForm', async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target));
        const token = localStorage.getItem('auth_token');
        const btn = e.target.querySelector('[type=submit]');
        if (!data.category) {
            showToast('Please select a category', 'error');
            return;
        }
        if (btn) { btn.disabled = true; btn.textContent = 'Creating…'; }
        try {
            const res = await fetch(`${API_BASE}/admin/categories/${data.category}/subcategories/`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: data.name })
            });
            if (res.ok) {
                showToast('Subcategory created!');
                const subcatModal = document.getElementById('createSubcategoryModal');
                if (subcatModal) subcatModal.style.display = 'none';
                e.target.reset();
                await fetchData();
                if (state.activeView === 'categories') renderCategories();
            } else {
                const err = await res.json();
                showToast('Error: ' + (err.error || JSON.stringify(err)), 'error');
            }
        } catch (ex) {
            showToast('Network error', 'error');
        } finally {
            if (btn) { btn.disabled = false; btn.textContent = 'Create Subcategory'; }
        }
    });

    // ── Notifications ──
    safeSetSubmit('sendNotificationForm', async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target));
        const token = localStorage.getItem('auth_token');
        try {
            const res = await fetch('/api/auth/admin/notifications/', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (res.ok) {
                showToast('Notification sent successfully');
                e.target.reset();
            } else {
                showToast('Failed to send notification', 'error');
            }
        } catch (err) { showToast('Network error', 'error'); }
    });

    // ── Settings ──
    safeSetSubmit('systemSettingsForm', async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target));
        const token = localStorage.getItem('auth_token');
        try {
            const res = await fetch('/api/auth/admin/system-settings/save/', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (res.ok) showToast('System settings saved');
        } catch (err) { showToast('Network error', 'error'); }
    });

    safeSetSubmit('popupSettingsForm', async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target));
        data.enabled = data.enabled === 'true';
        data.popup_delay_days = parseInt(data.popup_delay_days);
        const token = localStorage.getItem('auth_token');
        try {
            const res = await fetch('/api/auth/admin/popup-settings/save/', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (res.ok) showToast('Popup settings saved');
        } catch (err) { showToast('Network error', 'error'); }
    });

    // ── Dynamic Subcategory Inputs ──
    const addSubBtn = document.getElementById('add-sub-input-btn');
    const subContainer = document.getElementById('subcategory-inputs-container');
    if (addSubBtn && subContainer) {
        addSubBtn.onclick = () => {
            const row = document.createElement('div');
            row.className = 'subcategory-row';
            row.style.display = 'flex';
            row.style.gap = '0.5rem';
            row.style.marginBottom = '0.5rem';
            row.innerHTML = `
                <input type="text" name="subcategories[]" placeholder="Subcategory name" style="flex:1;">
                <button type="button" class="btn btn-secondary remove-sub-btn" style="padding:0.4rem;">
                    <i data-lucide="minus"></i>
                </button>
            `;
            subContainer.appendChild(row);
            if (window.lucide) lucide.createIcons();
            
            // Show remove buttons if more than 1 row
            const rows = subContainer.querySelectorAll('.subcategory-row');
            rows.forEach(r => r.querySelector('.remove-sub-btn').style.display = 'block');
        };

        subContainer.onclick = (e) => {
            const removeBtn = e.target.closest('.remove-sub-btn');
            if (removeBtn) {
                const row = removeBtn.closest('.subcategory-row');
                row.remove();
                
                // Hide remove button if only 1 row left
                const rows = subContainer.querySelectorAll('.subcategory-row');
                if (rows.length === 1) {
                    const rb = rows[0].querySelector('.remove-sub-btn');
                    if (rb) rb.style.display = 'none';
                }
            }
        };
    }

    // ── Edit Category Modal ──
    safeSetSubmit('editCategoryForm', async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target));
        const token = localStorage.getItem('auth_token');
        const btn = e.target.querySelector('[type=submit]');
        if (btn) { btn.disabled = true; btn.textContent = 'Updating...'; }
        try {
            const res = await fetch(`${API_BASE}/admin/categories/${data.category_id}/edit/`, {
                method: 'PATCH',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: data.name })
            });
            if (res.ok) {
                showToast('Category updated');
                document.getElementById('editCategoryModal').style.display = 'none';
                await fetchData();
                renderCategories();
            } else {
                showToast('Failed to update category', 'error');
            }
        } catch (ex) { showToast('Network error', 'error'); }
        finally { if (btn) { btn.disabled = false; btn.textContent = 'Update Category'; } }
    });

    // ── Edit Subcategory Modal ──
    safeSetSubmit('editSubcategoryForm', async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target));
        const token = localStorage.getItem('auth_token');
        const btn = e.target.querySelector('[type=submit]');
        if (btn) { btn.disabled = true; btn.textContent = 'Saving...'; }
        try {
            const res = await fetch(`${API_BASE}/admin/subcategories/${data.subcategory_id}/edit/`, {
                method: 'PATCH',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: data.name, category: data.category })
            });
            if (res.ok) {
                showToast('Subcategory updated');
                document.getElementById('editSubcategoryModal').style.display = 'none';
                await fetchData();
                renderCategories();
            } else {
                showToast('Failed to update subcategory', 'error');
            }
        } catch (ex) { showToast('Network error', 'error'); }
        finally { if (btn) { btn.disabled = false; btn.textContent = 'Save Changes'; } }
    });

    safeSetClick('deleteSubcategoryBtn', async () => {
        const subId = document.getElementById('editSubcategoryForm').subcategory_id.value;
        if (subId) await deleteSubcategory(subId);
    });

    // ── Close modals ──
    window.addEventListener('click', (e) => {
        // Close on backdrop click
        const modals = ['createVendorModal', 'addProductModal', 'kycModal', 'createCategoryModal', 'createSubcategoryModal', 'editVendorModal', 'editCategoryModal', 'editSubcategoryModal'];
        modals.forEach(id => {
            const m = document.getElementById(id);
            if (e.target === m) m.style.display = 'none';
        });

        // Global delegate for close button
        if (e.target.closest('.close-modal')) {
            const modal = e.target.closest('.modal');
            if (modal) {
                modal.style.display = 'none';
                if (modal.id === 'kycModal') state.kycVendorId = null;
            }
        }
    });

    // ── Logout ──
    safeSetClick('logoutBtn', () => {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user');
        window.location.href = '/admin/login/';
    });
}

// ── Open Edit Category Modal ──
function openEditCategoryModal(id) {
    const cat = state.categories.find(c => c.id === id);
    if (!cat) return;
    const m = document.getElementById('editCategoryModal');
    const f = document.getElementById('editCategoryForm');
    f.category_id.value = cat.id;
    f.name.value = cat.name;
    m.style.display = 'flex';
    if (window.lucide) lucide.createIcons();
}

// ── Open Edit Subcategory Modal ──
function openEditSubcategoryModal(id) {
    let sub = null;
    let parentCatId = null;
    state.categories.forEach(c => {
        const found = (c.subcategories || []).find(sc => sc.id === id);
        if (found) {
            sub = found;
            parentCatId = c.id;
        }
    });

    if (!sub) return;

    const m = document.getElementById('editSubcategoryModal');
    const f = document.getElementById('editSubcategoryForm');
    const sel = document.getElementById('edit-subcategory-parent-select');

    f.subcategory_id.value = sub.id;
    f.name.value = sub.name;

    // Populate category dropdown
    sel.innerHTML = '<option value="">-- Select Category --</option>';
    state.categories.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.id; opt.textContent = c.name;
        if (c.id === parentCatId) opt.selected = true;
        sel.appendChild(opt);
    });

    m.style.display = 'flex';
    if (window.lucide) lucide.createIcons();
}
