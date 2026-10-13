// Shared admin sidebar behaviour. Used by every admin module. Do not duplicate in page templates.
// Requires: bootstrap bundle loaded first; _sidebar.html and _form_builder.html included in the page.
(function () {
    const ICONS = {
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
        a.href = '#';
        a.textContent = f.name; // textContent: names are never parsed as HTML
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

    function emptyNote(text) {
        const s = document.createElement('span');
        s.className = 'px-3 text-muted small fw-bold';
        s.textContent = text;
        return s;
    }

    function render(data) {
        const brandBox = document.getElementById('brand-list');
        const formBox = document.getElementById('form-list');
        brandBox.textContent = '';
        (data.brands || []).forEach(function (b) {
            const a = document.createElement('a');
            a.href = '#';
            a.textContent = b.name;
            brandBox.appendChild(a);
        });
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

    // Form 3-dot menu: open/close only (Archive is wired in a later step)
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

    // Form Builder modal
    const modalEl = document.getElementById('formBuilderModal');
    if (modalEl) {
        document.querySelectorAll('.form-element-btn').forEach(function (btn) {
            btn.addEventListener('dragstart', function (e) {
                e.dataTransfer.setData('text/plain', btn.textContent.trim());
            });
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

        document.getElementById('form-save-btn').addEventListener('click', async function () {
            const name = document.getElementById('form-name-input').value.trim();
            const errorEl = document.getElementById('form-save-error');
            errorEl.classList.add('d-none');
            if (!name) {
                errorEl.textContent = 'Form name is required.';
                errorEl.classList.remove('d-none');
                return;
            }
            try {
                const res = await fetch('/api/v1/admin/forms', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: name })
                });
                if (res.status === 201) {
                    const data = await res.json();
                    bootstrap.Modal.getInstance(modalEl).hide();
                    document.getElementById('form-created-toast-body').textContent = 'Form "' + data.name + '" is created successfully!';
                    new bootstrap.Toast(document.getElementById('form-created-toast')).show();
                    refreshSidebar();
                } else if (res.status === 409) {
                    errorEl.textContent = 'A form with that name already exists.';
                    errorEl.classList.remove('d-none');
                } else {
                    errorEl.textContent = 'Could not save the form. Please try again.';
                    errorEl.classList.remove('d-none');
                }
            } catch (err) {
                errorEl.textContent = 'Could not reach the server.';
                errorEl.classList.remove('d-none');
            }
        });

        modalEl.addEventListener('hidden.bs.modal', function () {
            document.getElementById('form-name-input').value = '';
            document.getElementById('form-contents-list').textContent = '';
            document.getElementById('form-contents-list').classList.add('d-none');
            document.getElementById('form-contents-placeholder').classList.remove('d-none');
            document.getElementById('form-save-error').classList.add('d-none');
        });
    }

    refreshSidebar();
})();
