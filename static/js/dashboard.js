document.addEventListener('DOMContentLoaded', function () {
    const addButton = document.getElementById('add-row-btn');
    const tableBody = document.querySelector('#formset-table tbody');
    const totalForms = document.getElementById('id_form-TOTAL_FORMS');

    // ==== 1. Tambah Baris Formset ====
    if (addButton && tableBody && totalForms) {
        addButton.addEventListener('click', function (e) {
            e.preventDefault();

            const currentFormCount = parseInt(totalForms.value);
            const lastRow = tableBody.querySelector('tr:last-child');
            const newRow = lastRow.cloneNode(true);

            newRow.querySelectorAll('input, textarea, select').forEach((input) => {
                const oldName = input.getAttribute('name');
                if (!oldName) return;

                const newName = oldName.replace(/-(\d+)-/, `-${currentFormCount}-`);
                input.setAttribute('name', newName);
                input.setAttribute('id', `id_${newName}`);

                if (input.tagName === 'SELECT') {
                    input.selectedIndex = 0;
                } else if (input.type === 'checkbox') {
                    input.checked = false;
                } else {
                    input.value = '';
                }

                // 🔧 Bersihkan semua error label dalam cell
                const errorLabels = input.closest('td').querySelectorAll('.text-danger, .alert');
                errorLabels.forEach(el => el.remove());
            });

            tableBody.appendChild(newRow);
            totalForms.value = currentFormCount + 1;
        });
    }

    // ==== 2. Paste dari Excel (Copy-Paste Support) ====
    if (tableBody) {
        tableBody.addEventListener('paste', function (e) {
            const clipboardData = e.clipboardData || window.clipboardData;
            const pastedText = clipboardData.getData('Text');

            const rows = pastedText.trim().split('\n');
            const startRow = e.target.closest('tr');
            if (!startRow) return;

            const startIndex = Array.from(tableBody.children).indexOf(startRow);
            let currentFormCount = parseInt(totalForms.value);

            rows.forEach((line, i) => {
                const columns = line.split('\t');
                let row;

                if (i === 0) {
                    row = startRow;
                } else {
                    const lastRow = tableBody.querySelector('tr:last-child');
                    row = lastRow.cloneNode(true);

                    row.querySelectorAll('input, textarea, select').forEach((input) => {
                        const oldName = input.getAttribute('name');
                        if (!oldName) return;

                        const newName = oldName.replace(/-(\d+)-/, `-${currentFormCount}-`);
                        input.setAttribute('name', newName);
                        input.setAttribute('id', `id_${newName}`);

                        if (input.tagName === 'SELECT') {
                            input.selectedIndex = 0;
                        } else if (input.type === 'checkbox') {
                            input.checked = false;
                        } else {
                            input.value = '';
                        }

                        const errorLabels = input.closest('td').querySelectorAll('.text-danger, .alert');
                        errorLabels.forEach(el => el.remove());
                    });

                    tableBody.appendChild(row);
                    currentFormCount++;
                }

                const fields = row.querySelectorAll('input, textarea, select');
                columns.forEach((value, colIndex) => {
                    const field = fields[colIndex];
                    if (!field) return;

                    if (field.tagName === 'SELECT') {
                        const option = Array.from(field.options).find(opt =>
                            opt.text.toLowerCase().trim() === value.toLowerCase().trim()
                        );
                        if (option) {
                            field.value = option.value;
                        }
                    } else {
                        field.value = value.trim();
                    }
                });
            });

            totalForms.value = currentFormCount;
            e.preventDefault();
        });
    }

    // ==== 3. Toggle View ====
    const listViewBtn = document.getElementById('list-view-btn');
    const gridViewBtn = document.getElementById('grid-view-btn');
    const listView = document.getElementById('list-view');
    const gridView = document.getElementById('grid-view');

    if (gridViewBtn && listViewBtn && gridView && listView) {
        gridViewBtn.addEventListener('click', () => {
            listView.classList.add('d-none');
            gridView.classList.remove('d-none');
            listViewBtn.classList.remove('active');
            gridViewBtn.classList.add('active');
        });

        listViewBtn.addEventListener('click', () => {
            gridView.classList.add('d-none');
            listView.classList.remove('d-none');
            gridViewBtn.classList.remove('active');
            listViewBtn.classList.add('active');
        });
    }

    // ==== 4. Shortcut Keyboard ====
    const searchInput = document.getElementById('search-input');
    document.addEventListener('keydown', function (e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            if (searchInput) searchInput.focus();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            const firstInput = document.querySelector('input[name$="-nama"]');
            if (firstInput) firstInput.focus();
        }
    });

    // ==== 5. Scroll ke bagian tabel saat reload ====
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("submitted") === "true") {
        const tableSection = document.querySelector('.dashboard-table-wrapper');
        if (tableSection) {
            tableSection.scrollIntoView({ behavior: 'smooth' });
        }

        if (window.history.replaceState) {
            const cleanUrl = window.location.origin + window.location.pathname;
            window.history.replaceState({}, document.title, cleanUrl);
        }
    }
});
