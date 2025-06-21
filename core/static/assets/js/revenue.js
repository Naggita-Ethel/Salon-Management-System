document.addEventListener("DOMContentLoaded", function () {
    const customerSelector = document.getElementById("id_customer_selector");
    const existingCustomerFields = document.getElementById("existing_customer_fields");
    const newCustomerFields = document.getElementById("new_customer_fields");
    const branchSelector = document.getElementById("id_branch");

    function toggleCustomerFields() {
        if (customerSelector.value === "existing") {
            existingCustomerFields.style.display = "block";
            newCustomerFields.style.display = "none";
        } else { // 'new'
            existingCustomerFields.style.display = "none";
            newCustomerFields.style.display = "block";
        }
    }

    customerSelector.addEventListener("change", toggleCustomerFields);
    toggleCustomerFields(); // Initial call

    // --- Item and Employee Management ---
    const itemCategory = document.getElementById("item_category");
    const existingItemSection = document.getElementById("existing_item_section");
    const newItemFields = document.getElementById("new_item_fields");
    const itemDropdown = document.getElementById("item_dropdown");
    const transactionItemsTableBody = document.querySelector("#transaction-items-table tbody");
    const addItemButton = document.getElementById("add-item-button");
    const totalAmountDisplay = document.getElementById("total_amount_display");

    let formsetIndex = document.querySelectorAll('.formset-row').length;

    // itemPrices should be defined globally from your Django template
    // const itemPrices = {{ item_prices_json|safe }}; // This is assumed to be already there

    function updateTotalAmount() {
        let total = 0;
        document.querySelectorAll('.formset-row').forEach(row => {
            // Ensure the row is not marked for deletion
            const deleteInput = row.querySelector('[name$="-DELETE"]');
            if (deleteInput && deleteInput.checked) { // Check if checkbox is checked
                return; // Skip this row if marked for deletion
            }

            const quantityInput = row.querySelector('[name$="-quantity"]');
            const itemSelect = row.querySelector('[name$="-item"]'); // This is the select element

            if (quantityInput && itemSelect && itemSelect.value) {
                const quantity = parseInt(quantityInput.value) || 0;
                const itemId = itemSelect.value;
                const itemPrice = parseFloat(itemPrices[itemId]) || 0; // Use itemPrices from global scope
                total += quantity * itemPrice;
            }
        });
        totalAmountDisplay.value = total.toFixed(2);
    }

    // Function to fetch and populate items and their prices for the main dropdown
    function fetchAndPopulateItemsAndPrices(category, callback) {
        fetch(`/get-items-by-category/?category=${category}`)
            .then(response => response.json())
            .then(data => {
                itemDropdown.innerHTML = `<option value="">-- Select Item --</option>`;
                // itemPrices is globally defined, so we don't clear it here.
                // We assume `itemPrices` already contains all items from the view context.
                data.forEach(item => {
                    itemDropdown.innerHTML += `<option value="${item.id}">${item.name}</option>`;
                });
                itemDropdown.innerHTML += `<option value="new">+ Add New Item</option>`;
                if (callback) callback();
            })
            .catch(error => console.error('Error fetching items:', error));
    }

    // Function to populate employee dropdowns for a given select element and branch ID
    function populateEmployeeDropdown(employeeSelectElement, branchId) {
        if (!branchId) {
            employeeSelectElement.innerHTML = `<option value="">-- Select Branch First --</option>`;
            employeeSelectElement.setAttribute('disabled', 'disabled');
            return;
        }
        employeeSelectElement.removeAttribute('disabled');
        fetch(`/get-employees-by-branch/?branch_id=${branchId}`)
            .then(response => response.json())
            .then(data => {
                employeeSelectElement.innerHTML = `<option value="">-- Select Employee --</option>`;
                data.forEach(employee => {
                    employeeSelectElement.innerHTML += `<option value="${employee.id}">${employee.name}</option>`;
                });
            })
            .catch(error => console.error('Error fetching employees:', error));
    }

    // Event listener for main Item Category dropdown
    itemCategory.addEventListener("change", function () {
        const category = this.value;
        if (category) {
            existingItemSection.style.display = "block";
            fetchAndPopulateItemsAndPrices(category);
        } else {
            existingItemSection.style.display = "none";
        }
    });

    // Event listener for main Item dropdown (to show new item fields)
    itemDropdown.addEventListener("change", function () {
        if (this.value === "new") {
            newItemFields.style.display = "block";
        } else {
            newItemFields.style.display = "none";
        }
    });

    // Function to add a new formset row
    function addFormsetRow() {
        const totalFormsInput = document.getElementById('id_items-TOTAL_FORMS');
        const currentTotal = parseInt(totalFormsInput.value);

        const newRowHtml = `
            <tr class="formset-row">
                <td>
                    <select name="items-${currentTotal}-item" class="form-control item-select" required>
                        <option value="">-- Select Item --</option>
                    </select>
                </td>
                <td><input type="number" name="items-${currentTotal}-quantity" class="form-control quantity-input" value="1" min="1" required></td>
                <td>
                    <select name="items-${currentTotal}-employee" class="form-control employee-select">
                        <option value="">-- Select Employee --</option>
                    </select>
                </td>
                <td>
                    <button type="button" class="btn btn-sm btn-outline-danger remove-item-button">Remove</button>
                    <input type="hidden" name="items-${currentTotal}-id" id="id_items-${currentTotal}-id">
                    <input type="hidden" name="items-${currentTotal}-DELETE" id="id_items-${currentTotal}-DELETE" value="false">
                </td>
            </tr>
        `;
        transactionItemsTableBody.insertAdjacentHTML('beforeend', newRowHtml);

        // Update TOTAL_FORMS
        totalFormsInput.value = currentTotal + 1;

        // Get references to the newly added elements
        const newRow = transactionItemsTableBody.lastElementChild;
        const newItemSelect = newRow.querySelector('.item-select');
        const newQuantityInput = newRow.querySelector('.quantity-input');
        const newEmployeeSelect = newRow.querySelector('.employee-select');
        const removeButton = newRow.querySelector('.remove-item-button');

        // Clone options from the main itemDropdown to the new one
        // This ensures the new row's item select has options if a category was already picked
        if (itemDropdown.value) {
            newItemSelect.innerHTML = itemDropdown.innerHTML;
        } else {
            // If no category selected yet, ensure it's empty
            newItemSelect.innerHTML = `<option value="">-- Select Item --</option>`;
        }

        // Populate employees in the new row's employee select based on currently selected branch
        const selectedBranchId = branchSelector.value;
        populateEmployeeDropdown(newEmployeeSelect, selectedBranchId);

        // Add event listeners for the new row's inputs
        newItemSelect.addEventListener('change', updateTotalAmount);
        newQuantityInput.addEventListener('input', updateTotalAmount);
        removeButton.addEventListener('click', removeFormsetRow);
    }

    function removeFormsetRow(event) {
        const row = event.target.closest('.formset-row');
        const deleteInput = row.querySelector('[name$="-DELETE"]');
        if (deleteInput) {
            deleteInput.value = 'on'; // Mark for deletion
            row.style.display = 'none'; // Hide the row
            updateTotalAmount();
        } else {
            // This case should ideally not happen if hidden DELETE field is always present
            row.remove();
            updateTotalAmount();
            // Decrement TOTAL_FORMS if it's not a server-rendered form being marked for delete
            const totalFormsInput = document.getElementById('id_items-TOTAL_FORMS');
            totalFormsInput.value = parseInt(totalFormsInput.value) - 1;
        }
    }

    // Initial setup for existing rows (if any) and event delegation
    // Attach event listeners to already rendered formset rows
    document.querySelectorAll('.formset-row').forEach(row => {
        const deleteButton = row.querySelector('.remove-item-button');
        if (deleteButton) {
            deleteButton.addEventListener('click', removeFormsetRow);
        }
        const quantityInput = row.querySelector('[name$="-quantity"]');
        if (quantityInput) {
            quantityInput.addEventListener('input', updateTotalAmount);
        }
        const itemSelect = row.querySelector('[name$="-item"]');
        if (itemSelect) {
            itemSelect.addEventListener('change', updateTotalAmount);
        }
    });

    addItemButton.addEventListener('click', addFormsetRow);

    // Handle branch change to repopulate all employee dropdowns in all item rows
    branchSelector.addEventListener('change', function() {
        const selectedBranchId = this.value;
        // Populate main transaction serviced_by
        const mainServicedBy = document.getElementById('id_serviced_by');
        if (mainServicedBy) {
            populateEmployeeDropdown(mainServicedBy, selectedBranchId);
        }

        // Populate all item-specific serviced_by dropdowns
        document.querySelectorAll('.employee-select').forEach(employeeDropdown => {
            populateEmployeeDropdown(employeeDropdown, selectedBranchId);
        });
    });

    // Initial population for branch-dependent dropdowns on page load
    // This will run when the page loads for the first time.
    const initialBranchId = branchSelector.value;
    if (initialBranchId) {
        // Populate main transaction serviced_by if branch is pre-selected
        const mainServicedBy = document.getElementById('id_serviced_by');
        if (mainServicedBy) {
            populateEmployeeDropdown(mainServicedBy, initialBranchId);
        }
        // Populate existing item rows' employee dropdowns
        document.querySelectorAll('.employee-select').forEach(employeeDropdown => {
            // Only populate if the dropdown is not already selected for an existing item
            // (e.g., if you're editing a transaction and an employee was already chosen)
            if (!employeeDropdown.value) { // Only if current value is empty
                populateEmployeeDropdown(employeeDropdown, initialBranchId);
            }
        });
    }

    // Initial total amount calculation on page load
    updateTotalAmount();
});