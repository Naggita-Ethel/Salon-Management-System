// product_purchase.js

document.addEventListener("DOMContentLoaded", function () {
    // --- Element References ---
    const supplierTypeSelector = document.getElementById("id_supplier_selection_type");
    const existingSupplierFields = document.getElementById("existing_supplier_fields");
    const newSupplierFields = document.getElementById("new_supplier_fields");
    const branchSelector = document.getElementById("id_branch");
    const transactionItemsTableBody = document.querySelector("#transaction-items-table tbody");
    const addItemButton = document.getElementById("add-item-button");
    const subtotalDisplay = document.getElementById("subtotal_display");
    const grandTotalDisplay = document.getElementById("grand_total_display");
    const paymentStatusSelector = document.getElementById("id_payment_status");
    const amountPaidField = document.getElementById("amount_paid_field");
    const amountPaidInput = document.getElementById("id_amount_paid");

    // NEW: Reference to the hidden 'amount' input field
    const hiddenAmountInput = document.getElementById("id_amount");


    // Helper to format currency
    function formatCurrency(amount) {
        return parseFloat(amount).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 });
    }

    // Toggle supplier fields
    function toggleSupplierFields() {
        if (supplierTypeSelector && existingSupplierFields && newSupplierFields) {
            if (supplierTypeSelector.value === "existing") {
                existingSupplierFields.style.display = "";
                newSupplierFields.style.display = "none";
                existingSupplierFields.querySelectorAll('input, select').forEach(el => el.removeAttribute('disabled'));
                newSupplierFields.querySelectorAll('input, select').forEach(el => {
                    el.setAttribute('disabled', 'disabled');
                    el.removeAttribute('required'); // Remove required from disabled new supplier fields
                });
                // Ensure existing supplier select is required
                const existingSupplierSelect = existingSupplierFields.querySelector('#id_existing_supplier');
                if (existingSupplierSelect) existingSupplierSelect.setAttribute('required', 'required');

            } else {
                existingSupplierFields.style.display = "none";
                newSupplierFields.style.display = "";
                existingSupplierFields.querySelectorAll('input, select').forEach(el => {
                    el.setAttribute('disabled', 'disabled');
                    el.removeAttribute('required'); // Remove required from disabled existing supplier fields
                });
                newSupplierFields.querySelectorAll('input, select').forEach(el => el.removeAttribute('disabled'));
                document.getElementById('id_new_supplier_name').setAttribute('required', 'required'); // Ensure name is required for new
            }
        }
    }



    function populateProductItemsDropdown(itemSelectElement, selectedItemId = null) {



        if (!window.itemPrices) return;



        itemSelectElement.innerHTML = `<option value="">-- Select Product --</option>`;



        for (const itemId in window.itemPrices) {



            if (window.itemPrices.hasOwnProperty(itemId)) {



                const itemData = window.itemPrices[itemId];



                if (itemData.type === "product") {



                    const option = document.createElement('option');



                    option.value = itemId;



                    option.textContent = `${itemData.name} (UGX ${formatCurrency(itemData.cost_price)})`;



                    if (selectedItemId && String(itemId) === String(selectedItemId)) {



                        option.selected = true;



                    }



                    itemSelectElement.appendChild(option);



                }



            }



        }



    }


    // Populate employee dropdown (remains largely the same)
    function populateEmployeeDropdown(employeeSelectElement, branchId, selectedEmployeeId = null) {
        if (!branchId) {
            employeeSelectElement.innerHTML = `<option value="">-- Select Branch First --</option>`;
            employeeSelectElement.setAttribute('disabled', 'disabled');
            return;
        }
        employeeSelectElement.removeAttribute('disabled');
        employeeSelectElement.innerHTML = `<option value="">Loading employees...</option>`;

        const url = `/get-employees-by-branch/?branch_id=${branchId}`;

        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                employeeSelectElement.innerHTML = `<option value="">-- Select Employee --</option>`;
                data.forEach(employee => {
                    const option = document.createElement('option');
                    option.value = employee.id;
                    option.textContent = employee.name;
                    if (selectedEmployeeId && String(employee.id) === String(selectedEmployeeId)) {
                        option.selected = true;
                    }
                    employeeSelectElement.appendChild(option);
                });
            })
            .catch(error => {
                console.error("Error fetching employees:", error);
                employeeSelectElement.innerHTML = `<option value="">-- Error loading employees --</option>`;
                employeeSelectElement.setAttribute('disabled', 'disabled');
            });
    }

    // Calculate subtotal and grand total, and update hidden field
    function calculateAndDisplayTotals() {
        let subtotal = 0;
        document.querySelectorAll('.formset-row').forEach((row) => {
            const deleteInput = row.querySelector(`[name$="-DELETE"]`);
            if (deleteInput && deleteInput.checked) return; // Skip deleted rows
            const quantityInput = row.querySelector(`[name$="-quantity"]`);
            const itemSelect = row.querySelector(`[name$="-item"]`);
            if (quantityInput && itemSelect && itemSelect.value && itemPrices) {
                const quantity = parseInt(quantityInput.value) || 0;
                const itemId = itemSelect.value;
                if (itemPrices.hasOwnProperty(itemId)) {
                    const itemData = itemPrices[itemId];
                    const costPrice = parseFloat(itemData.cost_price) || 0;
                    subtotal += quantity * costPrice;
                }
            }
    });

        // Update display fields
        if (subtotalDisplay) subtotalDisplay.value = formatCurrency(subtotal);
        if (grandTotalDisplay) grandTotalDisplay.value = formatCurrency(subtotal); // No discount for now

        // --- CRITICAL FIX: Update the hidden 'amount' field for backend submission ---
        if (hiddenAmountInput) {
            hiddenAmountInput.value = subtotal.toFixed(2); // Ensure it's a number with 2 decimal places
        }

        // Adjust amount_paid field behavior based on payment status and calculated total
        if (paymentStatusSelector && amountPaidInput) {
            if (paymentStatusSelector.value === 'fully_paid') {
                amountPaidInput.value = subtotal.toFixed(2); // Auto-fill if fully paid
                amountPaidInput.readOnly = false; // Make it read-only
            } else if (paymentStatusSelector.value === 'pending') {
                amountPaidInput.value = '0.00'; // Set to 0 if pending
                amountPaidInput.readOnly = false; // Make it read-only
            } else { // partially_paid
                amountPaidInput.readOnly = false; // Allow user input for partial payments
                // Do not clear value if it was already partially paid and user changes mind,
                // but set to 0 if it was fully paid/pending before this change
                if (parseFloat(amountPaidInput.value) === 0 || parseFloat(amountPaidInput.value) === subtotal) {
                     amountPaidInput.value = ''; // Clear for user to enter partial amount
                }
            }
        }

        console.log("Calculating totals...");
        console.log("itemPrices:", itemPrices);
        console.log("Rows:", document.querySelectorAll('.formset-row').length);
    }




    function toggleAmountPaidField() {

        if (paymentStatusSelector && amountPaidField && amountPaidInput) {

            if (paymentStatusSelector.value === "partially_paid") {

                amountPaidField.style.display = "";

                amountPaidInput.setAttribute('required', 'required'); // Use setAttribute

            } else {

                amountPaidField.style.display = "none";

                amountPaidInput.removeAttribute('required'); // Use removeAttribute

                amountPaidInput.value = "";

            }

        }

    }

    // --- Initial Setup and Event Attachments ---

    toggleSupplierFields();
    if (supplierTypeSelector) supplierTypeSelector.addEventListener("change", toggleSupplierFields);

    toggleAmountPaidField(); // Call initially
    if (paymentStatusSelector) paymentStatusSelector.addEventListener("change", toggleAmountPaidField);
    if (hiddenAmountInput) hiddenAmountInput.addEventListener('change', toggleAmountPaidField); // Listen for hidden amount change

//     toggleAmountPaidField();

//     if (paymentStatusSelector) paymentStatusSelector.addEventListener("change", toggleAmountPaidField);

    if (branchSelector) {
        branchSelector.addEventListener("change", function () {
            const selectedBranchId = this.value;
            document.querySelectorAll('.employee-select').forEach(employeeSelectElement => {
                const currentEmployeeId = employeeSelectElement.value;
                populateEmployeeDropdown(employeeSelectElement, selectedBranchId, currentEmployeeId);
            });
        });
    }

    function initializeFormsetRow(row) {
        const itemSelect = row.querySelector('[name$="-item"]');
        const quantityInput = row.querySelector('[name$="-quantity"]');
        const employeeSelect = row.querySelector('[name$="-employee"]');

        if (itemSelect) {
            populateProductItemsDropdown(itemSelect, itemSelect.value);
            itemSelect.addEventListener('change', calculateAndDisplayTotals);
        }
        if (quantityInput) {
            quantityInput.addEventListener('input', calculateAndDisplayTotals);
            quantityInput.addEventListener('change', calculateAndDisplayTotals); // For blur/losing focus
        }

        if (employeeSelect && branchSelector) {
            populateEmployeeDropdown(employeeSelect, branchSelector.value, employeeSelect.value);
        }

        const removeButton = row.querySelector('.remove-item-button');
        if (removeButton) {
            removeButton.addEventListener('click', function() {
                row.remove();
                updateManagementFormTotalForms();
                calculateAndDisplayTotals(); // Recalculate after removal
            });
        }
    }

    let formsetIndex = document.querySelectorAll('.formset-row').length;
    const managementFormTotalForms = document.querySelector('input[name$="-TOTAL_FORMS"]');

    function updateManagementFormTotalForms() {
        if (managementFormTotalForms) {
            managementFormTotalForms.value = document.querySelectorAll('.formset-row').length;
        }
    }

    addItemButton.addEventListener('click', function () {
        const emptyFormRow = transactionItemsTableBody.querySelector('.empty-form-template');
        let newFormRow;

        if (emptyFormRow) {
            newFormRow = emptyFormRow.cloneNode(true);
            newFormRow.classList.remove('empty-form-template', 'd-none');
            newFormRow.classList.add('formset-row');
        } else {
            // Fallback for manually creating if template is missing (consider removing for production)
            newFormRow = document.createElement('tr');
            newFormRow.classList.add('formset-row');
            newFormRow.innerHTML = `
                <td><select name="form-${formsetIndex}-item" class="form-control"></select></td>
                <td><input type="number" name="form-${formsetIndex}-quantity" class="form-control" value="1" min="1"></td>
                <td><select name="form-${formsetIndex}-employee" class="form-control employee-select"></select></td>
                <td>
                    <button type="button" class="btn btn-sm btn-outline-danger remove-item-button">Remove</button>
                    <input type="hidden" name="form-${formsetIndex}-id" id="id_form-${formsetIndex}-id">
                    <input type="hidden" name="form-${formsetIndex}-DELETE" id="id_form-${formsetIndex}-DELETE">
                </td>
            `;
        }

        newFormRow.innerHTML = newFormRow.innerHTML.replace(/__prefix__/g, formsetIndex);
        transactionItemsTableBody.appendChild(newFormRow);

        initializeFormsetRow(newFormRow);
        updateManagementFormTotalForms();
        formsetIndex++;

        // After adding a new row, recalculate totals
        calculateAndDisplayTotals();
    });

    // Initialize existing rows on page load
    document.querySelectorAll('.formset-row').forEach(initializeFormsetRow);

    // Initial calculation on page load
    calculateAndDisplayTotals();
});