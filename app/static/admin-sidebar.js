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
        function openElementEditor(type) {
            editorType = type === 'OPEN_ENDED' ? 'OPEN_ENDED' : 'YES_NO';
            const isOpen = editorType === 'OPEN_ENDED';
            document.getElementById('element-modal-title').textContent = isOpen ? 'Open Ended' : 'Yes / No Question';
            document.getElementById('element-choices-label').classList.toggle('d-none', isOpen);
            document.getElementById('element-choices-row').classList.toggle('d-none', isOpen);
            editingCard = null;
            document.getElementById('element-name-input').value = '';
            document.getElementById('element-choice-a').value = 'YES';
            document.getElementById('element-choice-b').value = 'NO';
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

        function editElement(card) {
            openElementEditor(card.dataset.elementType);
            editingCard = card;
            document.getElementById('element-name-input').value = card.dataset.name;
            document.getElementById('element-choice-a').value = card.dataset.choiceA;
            document.getElementById('element-choice-b').value = card.dataset.choiceB;
        }

        document.getElementById('element-confirm-btn').addEventListener('click', async function () {
            const errorEl = document.getElementById('element-modal-error');
            const name = document.getElementById('element-name-input').value.trim();
            const choiceA = document.getElementById('element-choice-a').value.trim();
            const choiceB = document.getElementById('element-choice-b').value.trim();
            errorEl.classList.add('d-none');
            let msg = '';
            if (!name) msg = 'Question name is required.';
            else if (editorType === 'YES_NO' && (!choiceA || !choiceB)) msg = 'Both choices need a label.';
            else if (editorType === 'YES_NO' && choiceA.toLowerCase() === choiceB.toLowerCase()) msg = 'The two choices must be different.';
            if (msg) {
                errorEl.textContent = msg;
                errorEl.classList.remove('d-none');
                return;
            }
            if (editingCard) {
                if (editorType === 'OPEN_ENDED' && !editingCard.dataset.questionId) {
                    // New (unsaved) Open ended card: DOM-only, Save creates it
                    editingCard.dataset.name = name;
                    editingCard.querySelector('.element-title').textContent = name;
                    closeElementEditor();
                    return;
                }
                if (editingCard.dataset.questionId) {
                    // Existing question: PATCH first, update the card only on success
                    const confirmBtn = document.getElementById('element-confirm-btn');
                    confirmBtn.disabled = true;
                    try {
                        const res = await fetch('/api/v1/admin/forms/' + encodeURIComponent(savedFormId) + '/questions/' + encodeURIComponent(editingCard.dataset.questionId), {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(editorType === 'OPEN_ENDED' ? { question_text: name } : { question_text: name, options: [choiceA, choiceB] })
                        });
                        if (!res.ok) {
                            let detail = '';
                            try {
                                const body = await res.json();
                                if (typeof body.detail === 'string') detail = body.detail;
                            } catch (e) { /* no JSON body */ }
                            if (res.status === 404) errorEl.textContent = 'This question no longer exists.';
                            else if (res.status === 409) errorEl.textContent = 'This form is archived and cannot be edited.';
                            else errorEl.textContent = 'Could not save the question' + (detail ? ' (' + detail + ')' : '') + '.';
                            errorEl.classList.remove('d-none');
                            return;
                        }
                    } catch (err) {
                        errorEl.textContent = 'Could not reach the server.';
                        errorEl.classList.remove('d-none');
                        return;
                    } finally {
                        confirmBtn.disabled = false;
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
            const title = document.createElement('div');
            title.className = 'fw-bold element-title';
            title.textContent = name;
            const choices = document.createElement('div');
            choices.className = 'd-flex gap-2 mt-2 element-choices';
            [choiceA, choiceB].forEach(function (label) {
                const chip = document.createElement('span');
                chip.className = 'border rounded px-3 py-1 small text-muted';
                chip.textContent = label;
                choices.appendChild(chip);
            });
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
            if (editorType === 'YES_NO') card.appendChild(choices);
            list.appendChild(card);
            closeElementEditor();
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
                const labels = (q.options && q.options.length) ? q.options : (q.question_type === 'YES_NO' ? ['Yes', 'No'] : []);
                const header = document.createElement('div');
                header.className = 'd-flex justify-content-between align-items-start gap-2';
                header.appendChild(title);
                if (q.question_type === 'YES_NO' || q.question_type === 'OPEN_ENDED') {
                    card.dataset.name = q.question_text;
                    if (q.question_type === 'YES_NO') {
                        card.dataset.choiceA = labels[0];
                        card.dataset.choiceB = labels[1];
                    }
                    const editBtn = document.createElement('button');
                    editBtn.type = 'button';
                    editBtn.className = 'btn btn-sm btn-outline-secondary element-edit-btn flex-shrink-0';
                    editBtn.textContent = 'Edit';
                    editBtn.setAttribute('aria-label', 'Edit question');
                    editBtn.addEventListener('click', function () { editElement(card); });
                    header.appendChild(editBtn);
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
            if (cards.some(function (c) { return c.dataset.saved !== '1' && c.dataset.elementType !== 'YES_NO' && c.dataset.elementType !== 'OPEN_ENDED'; })) {
                errorEl.textContent = 'Only Yes / No and Open ended questions can be saved for now. Remove the other elements first.';
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
                            : { question_type: 'YES_NO', question_text: card.dataset.name, options: [card.dataset.choiceA, card.dataset.choiceB] })
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

    refreshSidebar();
})();
