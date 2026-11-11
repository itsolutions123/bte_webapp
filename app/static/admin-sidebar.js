// Shared admin sidebar behaviour. Used by every admin module. Do not duplicate in page templates.
// Requires: bootstrap bundle loaded first; _sidebar.html and _form_builder.html included in the page.
(function () {
    const ICONS = {
        delete: '<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z"/><path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z"/></svg>',
        rename: '<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168l10-10zM11.207 2.5 13.5 4.793 14.793 3.5 12.5 1.207 11.207 2.5zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.293l6.5-6.5zm-9.761 5.175-.106.106-1.528 3.821 3.821-1.528.106-.106A.5.5 0 0 1 5 12.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.468-.325z"/></svg>',
        archive: '<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M0 2a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1v7.5a2.5 2.5 0 0 1-2.5 2.5h-9A2.5 2.5 0 0 1 1 12.5V5a1 1 0 0 1-1-1V2zm2 3v7.5A1.5 1.5 0 0 0 3.5 14h9a1.5 1.5 0 0 0 1.5-1.5V5H2zm13-3H1v2h14V2zM5 7.5a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5z"/></svg>'
    };

    function menuItem(kind, label) {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'form-menu-item';
        b.dataset.action = kind;
        b.title = label;
        b.setAttribute('aria-label', label);
        b.innerHTML = ICONS[kind]; // static constant, never user data
        return b;
    }

    function formRow(f) {
        const row = document.createElement('div');
        row.className = 'form-row';
        row.dataset.formId = f.id;
        const a = document.createElement('a');
        a.href = '/admin/forms/' + f.id;
        a.textContent = f.name; // textContent: names are never parsed as HTML
        if (window.location.pathname === a.getAttribute('href')) {
            a.classList.add('active');
        }
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'form-menu-btn';
        btn.setAttribute('aria-label', 'Form options');
        btn.setAttribute('aria-haspopup', 'true');
        btn.setAttribute('aria-expanded', 'false');
        btn.innerHTML = '&#8942;';
        const menu = document.createElement('div');
        menu.className = 'form-menu';
        menu.hidden = true;
        menu.appendChild(menuItem('rename', 'Rename form'));
        menu.appendChild(menuItem('archive', 'Archive form'));
        row.append(a, btn, menu);
        return row;
    }

    function brandRow(b) {
        const row = document.createElement('div');
        row.className = 'brand-row';
        row.dataset.brandId = b.id;
        const a = document.createElement('a');
        a.href = '/admin/brands/' + encodeURIComponent(b.id);
        a.textContent = b.name; // textContent: names are never parsed as HTML
        if (window.location.pathname === a.getAttribute('href')) {
            a.classList.add('active');
        }
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'form-menu-btn';
        btn.setAttribute('aria-label', 'Brand options');
        btn.setAttribute('aria-haspopup', 'true');
        btn.setAttribute('aria-expanded', 'false');
        btn.innerHTML = '&#8942;';
        const menu = document.createElement('div');
        menu.className = 'form-menu';
        menu.hidden = true;
        menu.appendChild(menuItem('rename', 'Rename brand'));
        menu.appendChild(menuItem('delete', 'Delete brand'));
        row.append(a, btn, menu);
        return row;
    }

    function emptyNote(text) {
        const s = document.createElement('span');
        s.className = 'px-3 text-muted fw-bold';
        s.textContent = text;
        return s;
    }

    const UNIT_OPEN_KEY_PREFIX = 'bte.sidebar.unitOpen.';
    function storedUnitOpen(id) {
        try { return window.localStorage.getItem(UNIT_OPEN_KEY_PREFIX + id); } catch (err) { return null; }
    }
    function storeUnitOpen(id, open) {
        try { window.localStorage.setItem(UNIT_OPEN_KEY_PREFIX + id, open ? '1' : '0'); } catch (err) { /* storage unavailable: state is just not remembered */ }
    }

    function unitSection(u) {
        const wrap = document.createElement('div');
        wrap.className = 'business-unit';
        wrap.dataset.businessUnitId = u.id;
        const head = document.createElement('div');
        head.className = 'd-flex justify-content-between align-items-center ps-3 pe-0 mt-2';
        const title = document.createElement('span');
        title.className = 'business-unit-title';
        title.textContent = u.name; // textContent: names are never parsed as HTML
        const plus = document.createElement('span');
        plus.setAttribute('role', 'button');
        plus.dataset.bsToggle = 'modal';
        plus.dataset.bsTarget = '#addBrandModal';
        plus.dataset.businessUnitId = u.id;
        plus.className = 'business-unit-add';
        plus.setAttribute('aria-label', 'Add brand to ' + u.name);
        plus.textContent = '+';
        const toggle = document.createElement('span');
        toggle.className = 'business-unit-toggle d-flex align-items-center flex-grow-1';
        toggle.setAttribute('role', 'button');
        toggle.setAttribute('tabindex', '0');
        const chevron = document.createElement('span');
        chevron.className = 'business-unit-chevron';
        chevron.setAttribute('aria-hidden', 'true');
        chevron.textContent = '\u203A';
        toggle.append(chevron, title);
        head.append(toggle, plus);
        const list = document.createElement('div');
        list.className = 'nav flex-column ps-3';
        let hasActiveChild = false;
        if (u.brands && u.brands.length > 0) {
            u.brands.forEach(function (b) {
                const row = brandRow(b);
                if (row.querySelector('a.active')) hasActiveChild = true;
                list.appendChild(row);
            });
        } else {
            list.appendChild(emptyNote('No brands yet'));
        }
        if (hasActiveChild) wrap.classList.add('has-active-child');
        function setOpen(open) {
            list.classList.toggle('d-none', !open);
            wrap.classList.toggle('is-open', open);
            toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        }
        setOpen(hasActiveChild || storedUnitOpen(u.id) === '1');
        toggle.addEventListener('click', function () {
            const next = list.classList.contains('d-none');
            setOpen(next);
            storeUnitOpen(u.id, next);
        });
        toggle.addEventListener('keydown', function (ev) {
            if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); toggle.click(); }
        });
        plus.addEventListener('click', function () { storeUnitOpen(u.id, true); });
        wrap.append(head, list);
        return wrap;
    }

    function render(data) {
        const formBox = document.getElementById('form-list');
        const unitBox = document.getElementById('business-unit-list');
        if (unitBox) {
            unitBox.textContent = '';
            (data.business_units || []).forEach(function (u) { unitBox.appendChild(unitSection(u)); });
        }
        formBox.textContent = '';
        if (data.forms && data.forms.length > 0) {
            data.forms.forEach(function (f) { formBox.appendChild(formRow(f)); });
        } else {
            formBox.appendChild(emptyNote('No forms yet'));
        }
    }

    async function refreshSidebar() {
        try {
            const res = await fetch('/api/v1/admin/metadata/sidebar');
            if (!res.ok) return;
            render(await res.json());
        } catch (err) {
            console.error('Sidebar load failed:', err);
        }
    }
    window.refreshSidebar = refreshSidebar;

    // Form 3-dot menu: open/close only (the Rename and Archive handlers are below)
    document.addEventListener('click', function (e) {
        const btn = e.target.closest('.form-menu-btn');
        document.querySelectorAll('.form-menu').forEach(function (m) {
            const owner = m.parentElement.querySelector('.form-menu-btn');
            const open = !!btn && owner === btn && m.hidden;
            m.hidden = !open;
            owner.setAttribute('aria-expanded', open);
        });
    });

    // Rename form: the Edit button in a form's 3-dot menu opens a small modal; Save calls PATCH
    const renameModalEl = document.getElementById('renameFormModal');
    if (renameModalEl) {
        const renameInput = document.getElementById('rename-form-input');
        const renameError = document.getElementById('rename-form-error');
        const renameSaveBtn = document.getElementById('rename-form-save-btn');
        let renameFormId = null;
        let renameOriginal = '';

        const showRenameError = function (msg) {
            renameError.textContent = msg;
            renameError.classList.remove('d-none');
        };

        document.addEventListener('click', function (e) {
            const item = e.target.closest('.form-menu-item[data-action="rename"]');
            if (!item) return;
            const row = item.closest('.form-row');
            if (!row) return;
            renameFormId = row.dataset.formId;
            renameOriginal = row.querySelector('a').textContent;
            renameInput.value = renameOriginal;
            renameError.classList.add('d-none');
            bootstrap.Modal.getOrCreateInstance(renameModalEl).show();
        });

        renameModalEl.addEventListener('shown.bs.modal', function () {
            renameInput.focus();
            renameInput.select();
        });

        renameInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                renameSaveBtn.click();
            }
        });

        renameSaveBtn.addEventListener('click', async function () {
            const name = renameInput.value.trim();
            renameError.classList.add('d-none');
            if (!name) {
                showRenameError('Form name is required.');
                return;
            }
            if (name === renameOriginal) {
                bootstrap.Modal.getInstance(renameModalEl).hide();
                return;
            }
            renameSaveBtn.disabled = true;
            try {
                const res = await fetch('/api/v1/admin/forms/' + encodeURIComponent(renameFormId), {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: name })
                });
                if (res.status === 200) {
                    const data = await res.json();
                    bootstrap.Modal.getInstance(renameModalEl).hide();
                    const toastEl = document.getElementById('form-created-toast');
                    if (toastEl) {
                        document.getElementById('form-created-toast-body').textContent = 'Form renamed to "' + data.name + '".';
                        new bootstrap.Toast(toastEl).show();
                    }
                    refreshSidebar();
                } else if (res.status === 409) {
                    const body = await res.json().catch(function () { return {}; });
                    if (String(body.detail || '').toLowerCase().indexOf('archived') !== -1) {
                        showRenameError('This form is archived and cannot be renamed.');
                    } else {
                        showRenameError('A form with that name already exists.');
                    }
                } else if (res.status === 404) {
                    showRenameError('This form no longer exists.');
                    refreshSidebar();
                } else if (res.status === 422) {
                    showRenameError('Please enter a valid form name.');
                } else {
                    showRenameError('Could not rename the form. Please try again.');
                }
            } catch (err) {
                showRenameError('Could not reach the server.');
            } finally {
                renameSaveBtn.disabled = false;
            }
        });
    }

    // Add brand: the BRANDS "+" in the sidebar opens a modal; Save calls POST /api/v1/admin/brands
    const addBrandModalEl = document.getElementById('addBrandModal');
    if (addBrandModalEl) {
        const addBrandInput = document.getElementById('add-brand-name');
        const addBrandError = document.getElementById('add-brand-error');
        const addBrandSaveBtn = document.getElementById('add-brand-save-btn');

        const showAddBrandError = function (msg) {
            addBrandError.textContent = msg;
            addBrandError.classList.remove('d-none');
        };

        let addBrandUnitId = null;
        addBrandModalEl.addEventListener('show.bs.modal', function (e) {
            // The unit "+" button that opened the modal carries data-business-unit-id (set when the real list renders).
            const trigger = e.relatedTarget;
            addBrandUnitId = (trigger && trigger.dataset && trigger.dataset.businessUnitId) || null;
            addBrandInput.value = '';
            addBrandError.classList.add('d-none');
        });
        addBrandModalEl.addEventListener('shown.bs.modal', function () {
            addBrandInput.focus();
        });

        const saveBrand = async function () {
            addBrandError.classList.add('d-none');
            const name = addBrandInput.value.trim();
            if (!name) {
                showAddBrandError('Please enter a brand name.');
                return;
            }
            if (!addBrandUnitId) {
                showAddBrandError('Open this from a business unit\'s + button.');
                return;
            }
            addBrandSaveBtn.disabled = true;
            try {
                const res = await fetch('/api/v1/admin/brands', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: name, business_unit_id: addBrandUnitId })
                });
                if (res.status === 201) {
                    const data = await res.json();
                    bootstrap.Modal.getInstance(addBrandModalEl).hide();
                    const toastEl = document.getElementById('form-created-toast');
                    if (toastEl) {
                        document.getElementById('form-created-toast-body').textContent = 'Brand "' + data.name + '" added.';
                        new bootstrap.Toast(toastEl).show();
                    }
                    refreshSidebar();
                } else if (res.status === 409) {
                    showAddBrandError('A brand with that name already exists.');
                } else if (res.status === 404) {
                    showAddBrandError('That business unit no longer exists. Reload the page.');
                } else if (res.status === 422) {
                    showAddBrandError('Please enter a valid brand name.');
                } else {
                    showAddBrandError('Could not add the brand. Please try again.');
                }
            } catch (err) {
                showAddBrandError('Could not reach the server.');
            } finally {
                addBrandSaveBtn.disabled = false;
            }
        };
        addBrandSaveBtn.addEventListener('click', saveBrand);
        addBrandInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                saveBrand();
            }
        });
    }

    // Add business unit: the OPERATIONS "+" in the sidebar opens a modal; Save calls POST /api/v1/admin/business-units
    const addBusinessUnitModalEl = document.getElementById('addBusinessUnitModal');
    if (addBusinessUnitModalEl) {
        const addBusinessUnitInput = document.getElementById('add-business-unit-name');
        const addBusinessUnitError = document.getElementById('add-business-unit-error');
        const addBusinessUnitSaveBtn = document.getElementById('add-business-unit-save-btn');

        const showAddBusinessUnitError = function (msg) {
            addBusinessUnitError.textContent = msg;
            addBusinessUnitError.classList.remove('d-none');
        };

        addBusinessUnitModalEl.addEventListener('show.bs.modal', function () {
            addBusinessUnitInput.value = '';
            addBusinessUnitError.classList.add('d-none');
        });
        addBusinessUnitModalEl.addEventListener('shown.bs.modal', function () {
            addBusinessUnitInput.focus();
        });

        const saveBusinessUnit = async function () {
            addBusinessUnitError.classList.add('d-none');
            const name = addBusinessUnitInput.value.trim();
            if (!name) {
                showAddBusinessUnitError('Please enter a business unit name.');
                return;
            }
            addBusinessUnitSaveBtn.disabled = true;
            try {
                const res = await fetch('/api/v1/admin/business-units', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: name })
                });
                if (res.status === 201) {
                    const data = await res.json();
                    bootstrap.Modal.getInstance(addBusinessUnitModalEl).hide();
                    const toastEl = document.getElementById('form-created-toast');
                    if (toastEl) {
                        document.getElementById('form-created-toast-body').textContent = 'Business unit "' + data.name + '" added.';
                        new bootstrap.Toast(toastEl).show();
                    }
                    refreshSidebar();
                } else if (res.status === 409) {
                    showAddBusinessUnitError('A business unit with that name already exists.');
                } else if (res.status === 422) {
                    showAddBusinessUnitError('Please enter a valid business unit name.');
                } else {
                    showAddBusinessUnitError('Could not add the business unit. Please try again.');
                }
            } catch (err) {
                showAddBusinessUnitError('Could not reach the server.');
            } finally {
                addBusinessUnitSaveBtn.disabled = false;
            }
        };
        addBusinessUnitSaveBtn.addEventListener('click', saveBusinessUnit);
        addBusinessUnitInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                saveBusinessUnit();
            }
        });
    }

    // Rename brand: the pencil item in a brand's 3-dot menu opens a small modal; Save calls PATCH /api/v1/admin/brands/{id}
    const renameBrandModalEl = document.getElementById('renameBrandModal');
    if (renameBrandModalEl) {
        const renameBrandInput = document.getElementById('rename-brand-input');
        const renameBrandError = document.getElementById('rename-brand-error');
        const renameBrandSaveBtn = document.getElementById('rename-brand-save-btn');
        let renameBrandId = null;
        let renameBrandOriginal = '';

        const showRenameBrandError = function (msg) {
            renameBrandError.textContent = msg;
            renameBrandError.classList.remove('d-none');
        };

        document.addEventListener('click', function (e) {
            const item = e.target.closest('.form-menu-item[data-action="rename"]');
            if (!item) return;
            const row = item.closest('.brand-row');
            if (!row) return;
            renameBrandId = row.dataset.brandId;
            renameBrandOriginal = row.querySelector('a').textContent;
            renameBrandInput.value = renameBrandOriginal;
            renameBrandError.classList.add('d-none');
            bootstrap.Modal.getOrCreateInstance(renameBrandModalEl).show();
        });

        renameBrandModalEl.addEventListener('shown.bs.modal', function () {
            renameBrandInput.focus();
            renameBrandInput.select();
        });

        renameBrandInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                renameBrandSaveBtn.click();
            }
        });

        renameBrandSaveBtn.addEventListener('click', async function () {
            const name = renameBrandInput.value.trim();
            renameBrandError.classList.add('d-none');
            if (!name) {
                showRenameBrandError('Brand name is required.');
                return;
            }
            if (name === renameBrandOriginal) {
                bootstrap.Modal.getInstance(renameBrandModalEl).hide();
                return;
            }
            renameBrandSaveBtn.disabled = true;
            try {
                const res = await fetch('/api/v1/admin/brands/' + encodeURIComponent(renameBrandId), {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: name })
                });
                if (res.status === 200) {
                    const data = await res.json();
                    bootstrap.Modal.getInstance(renameBrandModalEl).hide();
                    document.dispatchEvent(new CustomEvent('brand:renamed', { detail: { id: data.id, name: data.name } }));
                    const toastEl = document.getElementById('form-created-toast');
                    if (toastEl) {
                        document.getElementById('form-created-toast-body').textContent = 'Brand renamed to "' + data.name + '".';
                        new bootstrap.Toast(toastEl).show();
                    }
                    refreshSidebar();
                } else if (res.status === 409) {
                    const body = await res.json().catch(function () { return {}; });
                    if (String(body.detail || '').toLowerCase().indexOf('archived') !== -1) {
                        showRenameBrandError('This brand is archived and cannot be renamed.');
                    } else {
                        showRenameBrandError('A brand with that name already exists.');
                    }
                } else if (res.status === 404) {
                    showRenameBrandError('This brand no longer exists.');
                    refreshSidebar();
                } else if (res.status === 422) {
                    showRenameBrandError('Please enter a valid brand name.');
                } else {
                    showRenameBrandError('Could not rename the brand. Please try again.');
                }
            } catch (err) {
                showRenameBrandError('Could not reach the server.');
            } finally {
                renameBrandSaveBtn.disabled = false;
            }
        });
    }

    // Delete brand: the Delete brand item in a brand's 3-dot menu opens a confirm modal; Confirm calls DELETE /api/v1/admin/brands/{id} (409 when the brand has jobs)
    const archiveBrandModalEl = document.getElementById('archiveBrandModal');
    if (archiveBrandModalEl) {
        const archiveBrandNameEl = document.getElementById('archive-brand-name');
        const archiveBrandError = document.getElementById('archive-brand-error');
        const archiveBrandConfirmBtn = document.getElementById('archive-brand-confirm-btn');
        let archiveBrandId = null;

        const showArchiveBrandError = function (msg) {
            archiveBrandError.textContent = msg;
            archiveBrandError.classList.remove('d-none');
        };

        document.addEventListener('click', function (e) {
            const item = e.target.closest('.form-menu-item[data-action="delete"]');
            if (!item) return;
            const row = item.closest('.brand-row');
            if (!row) return;
            archiveBrandId = row.dataset.brandId;
            archiveBrandNameEl.textContent = row.querySelector('a').textContent;
            archiveBrandError.classList.add('d-none');
            bootstrap.Modal.getOrCreateInstance(archiveBrandModalEl).show();
        });

        archiveBrandConfirmBtn.addEventListener('click', async function () {
            archiveBrandError.classList.add('d-none');
            archiveBrandConfirmBtn.disabled = true;
            try {
                const deletedName = archiveBrandNameEl.textContent;
                const res = await fetch('/api/v1/admin/brands/' + encodeURIComponent(archiveBrandId), {
                    method: 'DELETE'
                });
                if (res.status === 204) {
                    bootstrap.Modal.getInstance(archiveBrandModalEl).hide();
                    const toastEl = document.getElementById('form-created-toast');
                    if (toastEl) {
                        document.getElementById('form-created-toast-body').textContent = 'Brand "' + deletedName + '" deleted.';
                        new bootstrap.Toast(toastEl).show();
                    }
                    refreshSidebar();
                    document.dispatchEvent(new CustomEvent('brands:changed'));
                } else if (res.status === 409) {
                    showArchiveBrandError('This brand has jobs and cannot be deleted.');
                } else if (res.status === 404) {
                    showArchiveBrandError('This brand no longer exists.');
                    refreshSidebar();
                } else {
                    showArchiveBrandError('Could not delete the brand. Please try again.');
                }
            } catch (err) {
                showArchiveBrandError('Could not reach the server.');
            } finally {
                archiveBrandConfirmBtn.disabled = false;
            }
        });
    }

    // Archive form: the Archive button in a form's 3-dot menu opens a confirm modal; Confirm calls the archive endpoint
    const archiveModalEl = document.getElementById('archiveFormModal');
    if (archiveModalEl) {
        const archiveNameEl = document.getElementById('archive-form-name');
        const archiveError = document.getElementById('archive-form-error');
        const archiveConfirmBtn = document.getElementById('archive-form-confirm-btn');
        let archiveFormId = null;

        const showArchiveError = function (msg) {
            archiveError.textContent = msg;
            archiveError.classList.remove('d-none');
        };

        document.addEventListener('click', function (e) {
            const item = e.target.closest('.form-menu-item[data-action="archive"]');
            if (!item) return;
            const row = item.closest('.form-row');
            if (!row) return;
            archiveFormId = row.dataset.formId;
            archiveNameEl.textContent = row.querySelector('a').textContent;
            archiveError.classList.add('d-none');
            bootstrap.Modal.getOrCreateInstance(archiveModalEl).show();
        });

        archiveConfirmBtn.addEventListener('click', async function () {
            archiveError.classList.add('d-none');
            archiveConfirmBtn.disabled = true;
            try {
                const res = await fetch('/api/v1/admin/forms/' + encodeURIComponent(archiveFormId) + '/archive', {
                    method: 'POST'
                });
                if (res.status === 200) {
                    const data = await res.json();
                    bootstrap.Modal.getInstance(archiveModalEl).hide();
                    const toastEl = document.getElementById('form-created-toast');
                    if (toastEl) {
                        document.getElementById('form-created-toast-body').textContent = 'Form "' + data.name + '" archived.';
                        new bootstrap.Toast(toastEl).show();
                    }
                    refreshSidebar();
                    document.dispatchEvent(new CustomEvent('forms:changed'));
                } else if (res.status === 409) {
                    const body = await res.json().catch(function () { return {}; });
                    const detail = String(body.detail || '');
                    if (detail.toLowerCase().indexOf('already archived') !== -1) {
                        showArchiveError('This form is already archived.');
                        refreshSidebar();
                    } else if (detail.indexOf('job(s)') !== -1) {
                        showArchiveError('Cannot archive: ' + detail);
                    } else {
                        showArchiveError('Could not archive the form.');
                    }
                } else if (res.status === 404) {
                    showArchiveError('This form no longer exists.');
                    refreshSidebar();
                } else {
                    showArchiveError('Could not archive the form. Please try again.');
                }
            } catch (err) {
                showArchiveError('Could not reach the server.');
            } finally {
                archiveConfirmBtn.disabled = false;
            }
        });
    }

    // Form Builder modal
    const modalEl = document.getElementById('formBuilderModal');
    if (modalEl) {
        document.querySelectorAll('.form-element-btn').forEach(function (btn) {
            btn.addEventListener('dragstart', function (e) {
                e.dataTransfer.setData('text/plain', btn.textContent.trim());
            });
        });

        // Element editor overlay (Yes / No)
        const elOverlay = document.getElementById('element-modal-overlay');
        let editingCard = null;
        let editorType = 'YES_NO';
        let savedFormId = null;
        let editMode = false;
        let savedFormName = '';
        function closeElementEditor() {
            editingCard = null;
            elOverlay.style.display = 'none';
        }
        function mcChoiceRow(optionId, text) {
            const row = document.createElement('div');
            row.className = 'd-flex gap-2 align-items-center mc-choice-row';
            row.dataset.optionId = optionId || '';
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'form-control mc-choice-input';
            input.placeholder = 'Choice text';
            input.value = text || '';
            input.setAttribute('aria-label', 'Choice text');
            input.addEventListener('input', renderMcKey);
            const removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = 'btn btn-sm btn-outline-danger mc-choice-remove';
            removeBtn.textContent = '\u00d7';
            removeBtn.setAttribute('aria-label', 'Remove choice');
            removeBtn.addEventListener('click', function () {
                const list = document.getElementById('element-mc-choices-list');
                if (list.children.length > 3) { row.remove(); renderMcKey(); }
            });
            row.appendChild(input);
            row.appendChild(removeBtn);
            return row;
        }
        function setMcChoices(options) {
            const list = document.getElementById('element-mc-choices-list');
            list.textContent = '';
            const items = (options && options.length) ? options : [{}, {}, {}];
            items.forEach(function (o) {
                list.appendChild(mcChoiceRow(o.id, o.text));
            });
        }
        function getMcChoiceValues() {
            return Array.from(document.getElementById('element-mc-choices-list').children).map(function (row) {
                return { id: row.dataset.optionId || null, text: row.querySelector('.mc-choice-input').value.trim() };
            });
        }
        document.getElementById('element-mc-add-choice-btn').addEventListener('click', function () {
            document.getElementById('element-mc-choices-list').appendChild(mcChoiceRow(null, ''));
            renderMcKey();
        });
        function renderMcKey(hide) {
            const wrap = document.getElementById('element-mc-key-wrap');
            const box = document.getElementById('element-mc-key-list');
            if (typeof hide === 'boolean') wrap.classList.toggle('d-none', hide);
            box.textContent = '';
            Array.from(document.getElementById('element-mc-choices-list').children).forEach(function (row, i) {
                const label = document.createElement('label');
                label.className = 'd-flex align-items-center gap-2';
                const cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.checked = row.dataset.keyed === '1';
                cb.addEventListener('change', function () { row.dataset.keyed = cb.checked ? '1' : ''; });
                const span = document.createElement('span');
                const needsSave = !!(editingCard && editingCard.dataset.questionId) && !row.dataset.optionId;
                cb.disabled = needsSave;
                span.textContent = (row.querySelector('.mc-choice-input').value.trim() || ('Choice ' + String.fromCharCode(65 + i))) + (needsSave ? ' (save first to mark correct)' : '');
                label.appendChild(cb);
                label.appendChild(span);
                box.appendChild(label);
            });
        }
        function getMcKeyPositions() {
            const pos = [];
            Array.from(document.getElementById('element-mc-choices-list').children).forEach(function (row, i) {
                if (row.dataset.keyed === '1') pos.push(i);
            });
            return pos;
        }
        function getMcKeyIds() {
            const ids = [];
            Array.from(document.getElementById('element-mc-choices-list').children).forEach(function (row) {
                if (row.dataset.keyed === '1' && row.dataset.optionId) ids.push(row.dataset.optionId);
            });
            return ids.length ? ids : null;
        }
        function keyLabel(id) {
            return document.getElementById(id).value.trim();
        }
        function setKeyPicker(type, value) {
            const wrap = document.getElementById('element-key-wrap');
            const box = document.getElementById('element-key-options');
            box.textContent = '';
            wrap.classList.toggle('d-none', type !== 'YES_NO');
            if (type !== 'YES_NO') return;
            [['YES', 'element-choice-a'], ['NO', 'element-choice-b'], ['', null]].forEach(function (opt) {
                const label = document.createElement('label');
                label.className = 'd-flex align-items-center gap-2';
                const radio = document.createElement('input');
                radio.type = 'radio';
                radio.name = 'element-key';
                radio.value = opt[0];
                radio.checked = (opt[0] === (value || ''));
                const span = document.createElement('span');
                if (opt[1]) span.dataset.labelSource = opt[1];
                span.textContent = opt[1] ? (keyLabel(opt[1]) || opt[0]) : 'Not scored';
                label.appendChild(radio);
                label.appendChild(span);
                box.appendChild(label);
            });
        }
        function refreshKeyLabels() {
            document.querySelectorAll('#element-key-options span[data-label-source]').forEach(function (s) {
                s.textContent = keyLabel(s.dataset.labelSource) || (s.dataset.labelSource === 'element-choice-a' ? 'YES' : 'NO');
            });
        }
        ['element-choice-a', 'element-choice-b'].forEach(function (id) {
            document.getElementById(id).addEventListener('input', refreshKeyLabels);
        });
        function getKeyValue() {
            const r = document.querySelector('input[name="element-key"]:checked');
            return r ? r.value : '';
        }
        function openElementEditor(type) {
            editorType = (type === 'OPEN_ENDED' || type === 'MULTIPLE_CHOICE') ? type : 'YES_NO';
            const isOpenEnded = editorType === 'OPEN_ENDED';
            const isMultipleChoice = editorType === 'MULTIPLE_CHOICE';
            document.getElementById('element-modal-title').textContent =
                isOpenEnded ? 'Open Ended' : (isMultipleChoice ? 'Multiple Choice' : 'Yes / No Question');
            document.getElementById('element-choices-label').classList.toggle('d-none', isOpenEnded || isMultipleChoice);
            document.getElementById('element-choices-row').classList.toggle('d-none', isOpenEnded || isMultipleChoice);
            document.getElementById('element-mc-choices-wrap').classList.toggle('d-none', !isMultipleChoice);
            editingCard = null;
            document.getElementById('element-name-input').value = '';
            document.getElementById('element-choice-a').value = 'YES';
            document.getElementById('element-choice-b').value = 'NO';
            setKeyPicker(editorType, '');
            if (isMultipleChoice) { setMcChoices(null); renderMcKey(false); }
            document.getElementById('element-modal-error').classList.add('d-none');
            elOverlay.style.display = 'flex';
            document.getElementById('element-name-input').focus();
        }
        document.querySelectorAll('.form-element-btn[data-element-type="YES_NO"]').forEach(function (btn) {
            btn.addEventListener('click', function () { openElementEditor('YES_NO'); });
        });
        document.getElementById('element-modal-close').addEventListener('click', closeElementEditor);
        document.querySelectorAll('.form-element-btn[data-element-type="OPEN_ENDED"]').forEach(function (btn) {
            btn.addEventListener('click', function () { openElementEditor('OPEN_ENDED'); });
        });
        document.querySelectorAll('.form-element-btn[data-element-type="MULTIPLE_CHOICE"]').forEach(function (btn) {
            btn.addEventListener('click', function () { openElementEditor('MULTIPLE_CHOICE'); });
        });

        function editElement(card) {
            openElementEditor(card.dataset.elementType);
            editingCard = card;
            document.getElementById('element-name-input').value = card.dataset.name;
            if (card.dataset.elementType === 'MULTIPLE_CHOICE') {
                setMcChoices(card.dataset.options ? JSON.parse(card.dataset.options) : null);
                const kp = card.dataset.keyPositions ? JSON.parse(card.dataset.keyPositions) : [];
                const kids = card.dataset.keyIds ? JSON.parse(card.dataset.keyIds) : [];
                Array.from(document.getElementById('element-mc-choices-list').children).forEach(function (row, i) { row.dataset.keyed = (row.dataset.optionId ? kids.indexOf(row.dataset.optionId) >= 0 : kp.indexOf(i) >= 0) ? '1' : ''; });
                renderMcKey(false);
            } else {
                document.getElementById('element-choice-a').value = card.dataset.choiceA;
                document.getElementById('element-choice-b').value = card.dataset.choiceB;
                if (card.dataset.elementType === 'YES_NO') {
                    setKeyPicker('YES_NO', card.dataset.correctAnswer || '');
                }
            }
        }

        document.getElementById('element-confirm-btn').addEventListener('click', async function () {
            const errorEl = document.getElementById('element-modal-error');
            const name = document.getElementById('element-name-input').value.trim();
            const choiceA = document.getElementById('element-choice-a').value.trim();
            const choiceB = document.getElementById('element-choice-b').value.trim();
            const mcChoices = editorType === 'MULTIPLE_CHOICE' ? getMcChoiceValues() : [];
            errorEl.classList.add('d-none');
            let msg = '';
            if (!name) msg = 'Question name is required.';
            else if (editorType === 'YES_NO' && (!choiceA || !choiceB)) msg = 'Both choices need a label.';
            else if (editorType === 'YES_NO' && choiceA.toLowerCase() === choiceB.toLowerCase()) msg = 'The two choices must be different.';
            else if (editorType === 'MULTIPLE_CHOICE') {
                if (mcChoices.some(function (c) { return !c.text; })) msg = 'Every choice needs a label.';
                else if (mcChoices.length < 3) msg = 'At least 3 choices are required.';
                else {
                    const lower = mcChoices.map(function (c) { return c.text.toLowerCase(); });
                    if (new Set(lower).size !== lower.length) msg = 'Choices must be different from each other.';
                }
            }
            if (msg) {
                errorEl.textContent = msg;
                errorEl.classList.remove('d-none');
                return;
            }
            if (editingCard) {
                if (editorType !== 'YES_NO' && !editingCard.dataset.questionId) {
                    // New (unsaved) Open ended / Multiple Choice card: DOM-only, Save creates it
                    editingCard.dataset.name = name;
                    editingCard.querySelector('.element-title').textContent = name;
                    if (editorType === 'MULTIPLE_CHOICE') {
                        editingCard.dataset.options = JSON.stringify(mcChoices.map(function (c) { return { text: c.text }; }));
                        editingCard.dataset.keyPositions = JSON.stringify(getMcKeyPositions());
                        const chipWrap0 = editingCard.querySelector('.element-choices');
                        chipWrap0.textContent = '';
                        mcChoices.forEach(function (c) {
                            const chip = document.createElement('span');
                            chip.className = 'border rounded px-3 py-1 small text-muted';
                            chip.textContent = c.text;
                            chipWrap0.appendChild(chip);
                        });
                    }
                    closeElementEditor();
                    return;
                }
                if (editingCard.dataset.questionId) {
                    // Existing question: PATCH first, update the card only on success
                    const confirmBtn = document.getElementById('element-confirm-btn');
                    confirmBtn.disabled = true;
                    let patchedOptions = null;
                    let patchedKey = [];
                    try {
                        let reqBody;
                        if (editorType === 'OPEN_ENDED') reqBody = { question_text: name };
                        else if (editorType === 'MULTIPLE_CHOICE') reqBody = { question_text: name, options: mcChoices.map(function (c) { return c.id ? { id: c.id, text: c.text } : { text: c.text }; }), correct_answer: getMcKeyIds() };
                        else reqBody = { question_text: name, options: [choiceA, choiceB], correct_answer: getKeyValue() || null };
                        const res = await fetch('/api/v1/admin/forms/' + encodeURIComponent(savedFormId) + '/questions/' + encodeURIComponent(editingCard.dataset.questionId), {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(reqBody)
                        });
                        if (!res.ok) {
                            let detail = '';
                            try {
                                const body2 = await res.json();
                                if (typeof body2.detail === 'string') detail = body2.detail;
                            } catch (e) { /* no JSON body */ }
                            if (res.status === 404) errorEl.textContent = 'This question no longer exists.';
                            else if (res.status === 409) errorEl.textContent = 'This form is archived and cannot be edited.';
                            else errorEl.textContent = 'Could not save the question' + (detail ? ' (' + detail + ')' : '') + '.';
                            errorEl.classList.remove('d-none');
                            return;
                        }
                        if (editorType === 'MULTIPLE_CHOICE') {
                            const data = await res.json();
                            patchedOptions = data.options || [];
                            patchedKey = Array.isArray(data.correct_answer) ? data.correct_answer : [];
                        }
                    } catch (err) {
                        errorEl.textContent = 'Could not reach the server.';
                        errorEl.classList.remove('d-none');
                        return;
                    } finally {
                        confirmBtn.disabled = false;
                    }
                    if (editorType === 'MULTIPLE_CHOICE') {
                        editingCard.dataset.name = name;
                        editingCard.dataset.options = JSON.stringify(patchedOptions);
                        editingCard.dataset.keyIds = JSON.stringify(patchedKey);
                        editingCard.querySelector('.element-title').textContent = name;
                        const chipWrap1 = editingCard.querySelector('.element-choices');
                        chipWrap1.textContent = '';
                        patchedOptions.forEach(function (o) {
                            const chip = document.createElement('span');
                            chip.className = 'border rounded px-3 py-1 small text-muted';
                            chip.textContent = o.text;
                            chipWrap1.appendChild(chip);
                        });
                        closeElementEditor();
                        return;
                    }
                }
                if (editorType === 'OPEN_ENDED') {
                    // Saved Open ended card: PATCH succeeded above, update the card and stop
                    editingCard.dataset.name = name;
                    editingCard.querySelector('.element-title').textContent = name;
                    closeElementEditor();
                    return;
                }
                editingCard.dataset.name = name;
                editingCard.dataset.choiceA = choiceA;
                editingCard.dataset.choiceB = choiceB;
                editingCard.dataset.correctAnswer = getKeyValue();
                editingCard.querySelector('.element-title').textContent = name;
                const chipWrap = editingCard.querySelector('.element-choices');
                chipWrap.textContent = '';
                [choiceA, choiceB].forEach(function (label) {
                    const chip = document.createElement('span');
                    chip.className = 'border rounded px-3 py-1 small text-muted';
                    chip.textContent = label;
                    chipWrap.appendChild(chip);
                });
                closeElementEditor();
                return;
            }
            document.getElementById('form-contents-placeholder').classList.add('d-none');
            const list = document.getElementById('form-contents-list');
            list.classList.remove('d-none');
            const card = document.createElement('div');
            card.className = 'border rounded p-3 mb-2';
            card.dataset.elementType = editorType;
            card.dataset.name = name;
            card.dataset.choiceA = choiceA;
            card.dataset.choiceB = choiceB;
            card.dataset.correctAnswer = editorType === 'YES_NO' ? getKeyValue() : '';
            if (editorType === 'MULTIPLE_CHOICE') {
                card.dataset.options = JSON.stringify(mcChoices.map(function (c) { return { text: c.text }; }));
                card.dataset.keyPositions = JSON.stringify(getMcKeyPositions());
            }
            const title = document.createElement('div');
            title.className = 'fw-bold element-title';
            title.textContent = name;
            const choices = document.createElement('div');
            choices.className = 'd-flex gap-2 mt-2 element-choices';
            if (editorType === 'YES_NO') {
                [choiceA, choiceB].forEach(function (label) {
                    const chip = document.createElement('span');
                    chip.className = 'border rounded px-3 py-1 small text-muted';
                    chip.textContent = label;
                    choices.appendChild(chip);
                });
            } else if (editorType === 'MULTIPLE_CHOICE') {
                mcChoices.forEach(function (c) {
                    const chip = document.createElement('span');
                    chip.className = 'border rounded px-3 py-1 small text-muted';
                    chip.textContent = c.text;
                    choices.appendChild(chip);
                });
            }
            const header = document.createElement('div');
            header.className = 'd-flex justify-content-between align-items-start gap-2';
            const actions = document.createElement('div');
            actions.className = 'd-flex gap-2 flex-shrink-0';
            const deleteBtn = document.createElement('button');
            deleteBtn.type = 'button';
            deleteBtn.className = 'btn btn-sm btn-outline-danger element-delete-btn';
            deleteBtn.textContent = 'Delete';
            deleteBtn.setAttribute('aria-label', 'Delete question');
            deleteBtn.addEventListener('click', function () {
                card.remove();
                if (!list.children.length) {
                    list.classList.add('d-none');
                    document.getElementById('form-contents-placeholder').classList.remove('d-none');
                }
            });
            const editBtn = document.createElement('button');
            editBtn.type = 'button';
            editBtn.className = 'btn btn-sm btn-outline-secondary element-edit-btn';
            editBtn.textContent = 'Edit';
            editBtn.setAttribute('aria-label', 'Edit question');
            editBtn.addEventListener('click', function () { editElement(card); });
            actions.appendChild(editBtn);
            actions.appendChild(deleteBtn);
            header.appendChild(title);
            header.appendChild(actions);
            card.appendChild(header);
            if (editorType === 'YES_NO' || editorType === 'MULTIPLE_CHOICE') card.appendChild(choices);
            list.appendChild(card);
            closeElementEditor();
        });

        const delModalEl = document.getElementById('deleteElementModal');
        const delConfirmBtn = document.getElementById('delete-element-confirm-btn');
        const delError = document.getElementById('delete-element-error');
        delConfirmBtn.addEventListener('click', async function () {
            const questionId = delModalEl.dataset.questionId;
            if (!savedFormId || !questionId) return;
            delError.classList.add('d-none');
            delConfirmBtn.disabled = true;
            try {
                const res = await fetch('/api/v1/admin/forms/' + encodeURIComponent(savedFormId) + '/questions/' + encodeURIComponent(questionId), { method: 'DELETE' });
                if (res.status === 204 || res.status === 404) {
                    const list = document.getElementById('form-contents-list');
                    const card = list.querySelector('[data-question-id="' + questionId + '"]');
                    if (card) card.remove();
                    if (!list.children.length) {
                        list.classList.add('d-none');
                        document.getElementById('form-contents-placeholder').classList.remove('d-none');
                    }
                    bootstrap.Modal.getInstance(delModalEl).hide();
                    document.getElementById('form-created-toast-body').textContent = res.status === 204 ? 'Element deleted.' : 'That element no longer existed.';
                    new bootstrap.Toast(document.getElementById('form-created-toast')).show();
                } else if (res.status === 409) {
                    delError.textContent = 'Applicants have already answered this element, so it cannot be deleted.';
                    delError.classList.remove('d-none');
                } else {
                    delError.textContent = 'Could not delete the element.';
                    delError.classList.remove('d-none');
                }
            } catch (err) {
                delError.textContent = 'Could not reach the server.';
                delError.classList.remove('d-none');
            } finally {
                delConfirmBtn.disabled = false;
            }
        });

        const panel = document.getElementById('form-contents-panel');
        panel.addEventListener('dragover', function (e) { e.preventDefault(); });
        panel.addEventListener('drop', function (e) {
            e.preventDefault();
            const label = e.dataTransfer.getData('text/plain');
            if (!label) return;
            document.getElementById('form-contents-placeholder').classList.add('d-none');
            const list = document.getElementById('form-contents-list');
            list.classList.remove('d-none');
            const item = document.createElement('div');
            item.className = 'border rounded p-3 mb-2';
            const span = document.createElement('span');
            span.className = 'text-muted small fw-bold';
            span.textContent = label;
            item.appendChild(span);
            list.appendChild(item);
        });

        // Edit mode: open the builder on an existing form (GET /api/v1/admin/forms/{form_id}).
        // Loaded questions are read-only for now; cards added afterwards are saved by the normal Save.
        window.openFormBuilderForEdit = async function (formId) {
            const showToast = function (msg) {
                document.getElementById('form-created-toast-body').textContent = msg;
                new bootstrap.Toast(document.getElementById('form-created-toast')).show();
            };
            let form;
            try {
                const res = await fetch('/api/v1/admin/forms/' + encodeURIComponent(formId));
                if (!res.ok) {
                    showToast(res.status === 404 ? 'This form no longer exists.' : 'Could not load the form.');
                    return;
                }
                form = await res.json();
            } catch (err) {
                showToast('Could not reach the server.');
                return;
            }
            savedFormId = form.id;
            editMode = true;
            savedFormName = form.name;
            const nameInput = document.getElementById('form-name-input');
            nameInput.value = form.name;
            nameInput.readOnly = true;
            document.getElementById('form-save-error').classList.add('d-none');
            const list = document.getElementById('form-contents-list');
            list.textContent = '';
            (form.questions || []).forEach(function (q) {
                const card = document.createElement('div');
                card.className = 'border rounded p-3 mb-2';
                card.dataset.elementType = q.question_type;
                card.dataset.questionId = q.id;
                card.dataset.saved = '1';
                const title = document.createElement('div');
                title.className = 'fw-bold element-title';
                title.textContent = q.question_text;
                const labels = (q.options && q.options.length)
                    ? (q.question_type === 'MULTIPLE_CHOICE' ? q.options.map(function (o) { return o.text; }) : q.options)
                    : (q.question_type === 'YES_NO' ? ['Yes', 'No'] : []);
                const header = document.createElement('div');
                header.className = 'd-flex justify-content-between align-items-start gap-2';
                header.appendChild(title);
                if (q.question_type === 'YES_NO' || q.question_type === 'OPEN_ENDED' || q.question_type === 'MULTIPLE_CHOICE') {
                    card.dataset.name = q.question_text;
                    if (q.question_type === 'YES_NO') {
                        card.dataset.choiceA = labels[0];
                        card.dataset.choiceB = labels[1];
                        card.dataset.correctAnswer = q.correct_answer || '';
                    } else if (q.question_type === 'MULTIPLE_CHOICE') {
                        card.dataset.options = JSON.stringify(q.options || []);
                        card.dataset.keyIds = JSON.stringify(Array.isArray(q.correct_answer) ? q.correct_answer : []);
                    }
                    const editBtn = document.createElement('button');
                    editBtn.type = 'button';
                    editBtn.className = 'btn btn-sm btn-outline-secondary element-edit-btn flex-shrink-0';
                    editBtn.textContent = 'Edit';
                    editBtn.setAttribute('aria-label', 'Edit question');
                    editBtn.addEventListener('click', function () { editElement(card); });
                    const deleteBtn = document.createElement('button');
                    deleteBtn.type = 'button';
                    deleteBtn.className = 'btn btn-sm btn-outline-danger element-delete-btn flex-shrink-0';
                    deleteBtn.textContent = 'Delete';
                    deleteBtn.setAttribute('aria-label', 'Delete question');
                    deleteBtn.addEventListener('click', function () {
                        const delModalEl = document.getElementById('deleteElementModal');
                        document.getElementById('delete-element-name').textContent = card.querySelector('.element-title').textContent;
                        document.getElementById('delete-element-error').classList.add('d-none');
                        delModalEl.dataset.questionId = card.dataset.questionId;
                        bootstrap.Modal.getOrCreateInstance(delModalEl).show();
                    });
                    const actions = document.createElement('div');
                    actions.className = 'd-flex gap-2 flex-shrink-0';
                    actions.appendChild(editBtn);
                    actions.appendChild(deleteBtn);
                    header.appendChild(actions);
                }
                card.appendChild(header);
                if (labels.length) {
                    const chips = document.createElement('div');
                    chips.className = 'd-flex gap-2 mt-2 element-choices';
                    labels.forEach(function (label) {
                        const chip = document.createElement('span');
                        chip.className = 'border rounded px-3 py-1 small text-muted';
                        chip.textContent = label;
                        chips.appendChild(chip);
                    });
                    card.appendChild(chips);
                }
                list.appendChild(card);
            });
            const hasCards = list.children.length > 0;
            list.classList.toggle('d-none', !hasCards);
            document.getElementById('form-contents-placeholder').classList.toggle('d-none', hasCards);
            bootstrap.Modal.getOrCreateInstance(modalEl).show();
        };

        document.getElementById('form-save-btn').addEventListener('click', async function () {
            const name = document.getElementById('form-name-input').value.trim();
            const errorEl = document.getElementById('form-save-error');
            errorEl.classList.add('d-none');
            if (!name) {
                errorEl.textContent = 'Form name is required.';
                errorEl.classList.remove('d-none');
                return;
            }
            const cards = Array.from(document.getElementById('form-contents-list').children);
            if (cards.some(function (c) { return c.dataset.saved !== '1' && c.dataset.elementType !== 'YES_NO' && c.dataset.elementType !== 'OPEN_ENDED' && c.dataset.elementType !== 'MULTIPLE_CHOICE'; })) {
                errorEl.textContent = 'Only Yes / No, Open ended and Multiple Choice questions can be saved for now. Remove the other elements first.';
                errorEl.classList.remove('d-none');
                return;
            }
            const saveBtn = document.getElementById('form-save-btn');
            saveBtn.disabled = true;
            try {
                if (!savedFormId) {
                    const res = await fetch('/api/v1/admin/forms', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: name })
                    });
                    if (res.status === 201) {
                        const data = await res.json();
                        savedFormId = data.id;
                        savedFormName = data.name;
                        document.getElementById('form-name-input').readOnly = true;
                    } else if (res.status === 409) {
                        errorEl.textContent = 'A form with that name already exists.';
                        errorEl.classList.remove('d-none');
                        return;
                    } else {
                        errorEl.textContent = 'Could not save the form. Please try again.';
                        errorEl.classList.remove('d-none');
                        return;
                    }
                }
                for (const card of cards) {
                    if (card.dataset.saved === '1') continue;
                    const qres = await fetch('/api/v1/admin/forms/' + savedFormId + '/questions', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(card.dataset.elementType === 'OPEN_ENDED'
                            ? { question_type: 'OPEN_ENDED', question_text: card.dataset.name }
                            : card.dataset.elementType === 'MULTIPLE_CHOICE'
                                ? { question_type: 'MULTIPLE_CHOICE', question_text: card.dataset.name, options: JSON.parse(card.dataset.options).map(function (o) { return o.text; }), ...(card.dataset.keyPositions && JSON.parse(card.dataset.keyPositions).length ? { correct_answer: JSON.parse(card.dataset.keyPositions) } : {}) }
                                : Object.assign({ question_type: 'YES_NO', question_text: card.dataset.name, options: [card.dataset.choiceA, card.dataset.choiceB] }, card.dataset.correctAnswer ? { correct_answer: card.dataset.correctAnswer } : {}))
                    });
                    if (qres.status !== 201) {
                        let detail = '';
                        try {
                            const body = await qres.json();
                            if (typeof body.detail === 'string') detail = body.detail;
                        } catch (e) { /* no JSON body */ }
                        errorEl.textContent = 'The form was created, but "' + card.dataset.name + '" could not be saved' + (detail ? ' (' + detail + ')' : '') + '. Press Save to retry the remaining questions.';
                        errorEl.classList.remove('d-none');
                        return;
                    }
                    card.dataset.saved = '1';
                    card.querySelectorAll('button').forEach(function (b) { b.disabled = true; });
                }
                const createdName = savedFormName;
                bootstrap.Modal.getInstance(modalEl).hide();
                document.getElementById('form-created-toast-body').textContent = editMode ? 'Edited Successfully' : 'Form "' + createdName + '" is created successfully!';
                new bootstrap.Toast(document.getElementById('form-created-toast')).show();
                refreshSidebar();
            } catch (err) {
                errorEl.textContent = 'Could not reach the server.';
                errorEl.classList.remove('d-none');
            } finally {
                saveBtn.disabled = false;
            }
        });

        modalEl.addEventListener('hidden.bs.modal', function () {
            document.getElementById('form-name-input').value = '';
            document.getElementById('form-contents-list').textContent = '';
            document.getElementById('form-contents-list').classList.add('d-none');
            document.getElementById('form-contents-placeholder').classList.remove('d-none');
            document.getElementById('form-save-error').classList.add('d-none');
            savedFormId = null;
            savedFormName = '';
            document.getElementById('form-name-input').readOnly = false;
            editMode = false;
            closeElementEditor();
        });
    }

    // Fixed profile pill (markup in _sidebar.html, styles in admin-sidebar.css). Loads GET /api/v1/admin/me on every page; logout calls POST /api/v1/admin/logout then goes to /login.
    function initProfilePill() {
        const elInitials = document.getElementById('profile-pill-initials');
        const elName = document.getElementById('profile-pill-name');
        const elRole = document.getElementById('profile-pill-role');
        const btnLogout = document.getElementById('profile-pill-logout');
        const elError = document.getElementById('profile-pill-error');
        if (!elInitials || !elName || !elRole || !btnLogout || !elError) return;

        function initialsFor(fullName, email) {
            const words = (fullName || '').trim().split(/ +/).filter(Boolean);
            if (words.length >= 2) return (words[0][0] + words[words.length - 1][0]).toUpperCase();
            if (words.length === 1) return words[0][0].toUpperCase();
            return ((email || '?')[0]).toUpperCase();
        }

        async function loadProfile() {
            try {
                const res = await fetch('/api/v1/admin/me', { headers: { 'Accept': 'application/json' } });
                if (!res.ok) throw new Error('HTTP ' + res.status);
                const me = await res.json();
                elInitials.textContent = initialsFor(me.full_name, me.email);
                elName.textContent = me.full_name || me.email;
                elName.title = me.full_name || me.email;
                elRole.textContent = me.role;
            } catch (err) {
                elInitials.textContent = '!';
                elName.textContent = 'Could not load profile';
                elName.title = '';
                elRole.textContent = '';
            }
        }

        let loggingOut = false;
        async function logOut() {
            if (loggingOut) return;
            loggingOut = true;
            btnLogout.disabled = true;
            elError.classList.add('d-none');
            try {
                const res = await fetch('/api/v1/admin/logout', { method: 'POST' });
                if (!res.ok) throw new Error('HTTP ' + res.status);
                location.replace('/login');
            } catch (err) {
                elError.textContent = 'Could not log out. Try again.';
                elError.classList.remove('d-none');
                btnLogout.disabled = false;
                loggingOut = false;
            }
        }
        btnLogout.addEventListener('click', logOut);

        loadProfile();
    }

    // MRF pending-accounts badge on the sidebar MRF item (SUPERADMIN and MANAGER only: the element exists only for them).
    // Contract: GET /api/v1/admin/mrf/summary (docs/API_CONTRACT.md). Polls only while the tab is visible.
    const MRF_BADGE_POLL_MS = 60000;
    const MRF_BADGE_MAX_BACKOFF_MS = 300000;

    function initMrfBadge() {
        const badge = document.getElementById('mrf-nav-badge');
        if (!badge) return;
        // Present on /admin/mrf only (Users tab badge); shows the same count as the sidebar badge.
        const usersBadge = document.getElementById('mrf-users-badge');
        function showCount(n) {
            [badge, usersBadge].forEach(function (b) {
                if (!b) return;
                if (n > 0) {
                    b.textContent = String(n);
                    b.hidden = false;
                } else {
                    b.hidden = true;
                }
            });
        }
        let delay = MRF_BADGE_POLL_MS;
        let timer = null;
        let stopped = false;
        let inFlight = false;

        function schedule() {
            clearTimeout(timer);
            if (stopped || document.hidden) return;
            timer = setTimeout(refreshMrfBadge, delay);
        }

        async function refreshMrfBadge() {
            if (stopped || inFlight) return;
            inFlight = true;
            try {
                const res = await fetch('/api/v1/admin/mrf/summary', { headers: { 'Accept': 'application/json' } });
                if (res.status === 401 || res.status === 403) {
                    stopped = true;
                    showCount(0);
                    return;
                }
                if (!res.ok) throw new Error('HTTP ' + res.status);
                const data = await res.json();
                const n = Number(data.pending_accounts);
                showCount(Number.isInteger(n) ? n : 0);
                delay = MRF_BADGE_POLL_MS;
            } catch (err) {
                console.error('MRF badge load failed:', err);
                showCount(0);
                delay = Math.min(delay * 2, MRF_BADGE_MAX_BACKOFF_MS);
            } finally {
                inFlight = false;
                schedule();
            }
        }

        window.refreshMrfBadge = refreshMrfBadge;

        document.addEventListener('visibilitychange', function () {
            if (document.hidden) {
                clearTimeout(timer);
            } else if (!stopped) {
                refreshMrfBadge();
            }
        });

        refreshMrfBadge();
    }

    initProfilePill();
    refreshSidebar();
    initMrfBadge();
})();
