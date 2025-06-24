// static/assets/js/revenue.js

document.addEventListener("DOMContentLoaded", function () {
    console.log("DOM Content Loaded. Initializing revenue.js.");


    // --- Element References ---
    // Corrected ID: 'id_customer_selector' from your Django form
    const customerSelector = document.getElementById("id_customer_selector"); 
    const existingCustomerFields = document.getElementById("existing_customer_fields");
    const newCustomerFields = document.getElementById("new_customer_fields");
    const branchSelector = document.getElementById("id_branch"); // Assuming this is correct
    const existingCustomerDropdown = document.getElementById("id_existing_customer");

    const customerLoyaltyInfo = document.getElementById("customer_loyalty_info");
    const displayLoyaltyPoints = document.getElementById("display_loyalty_points");
    const displayTotalSpend = document.getElementById("display_total_spend");
    const displayTotalVisits = document.getElementById("display_total_visits");
    const loyaltyRedemptionSection = document.getElementById("loyalty_redemption_section");
    const redeemLoyaltyPointsCheckbox = document.getElementById("id_redeem_loyalty_points");
    const loyaltyRedemptionStatus = document.getElementById("loyalty_redemption_status");
    const couponCodeSection = document.getElementById("coupon_code_section");
    const couponCodeInput = document.getElementById("id_coupon_code");
    const couponStatus = document.getElementById("coupon_status");

    const transactionItemsTableBody = document.querySelector("#transaction-items-table tbody");
    const addItemButton = document.getElementById("add-item-button");
    const subtotalDisplay = document.getElementById("subtotal_display");
    const discountDisplaySection = document.getElementById("discount_display_section");
    const totalDiscountDisplay = document.getElementById("total_discount_display");
    const grandTotalDisplay = document.getElementById("grand_total_display");

    let currentCustomerLoyaltyData = null; // Stores fetched loyalty data
    let currentLoyaltyDiscount = 0;
    let currentCouponDiscount = 0; // Currently, coupon is validated server-side on submission
    let currentSubtotal = 0;

    // Verify critical elements are found
    console.log("customerSelector:", customerSelector);
    console.log("branchSelector:", branchSelector);
    console.log("addItemButton:", addItemButton);
    console.log("subtotalDisplay:", subtotalDisplay);
    console.log("transactionItemsTableBody:", transactionItemsTableBody);
    console.log("Existing customer dropdown:", existingCustomerDropdown); // Added for debug


    // Helper to format currency
    function formatCurrency(amount) {
        // Use toLocaleString for better internationalization and formatting (e.g., thousands separators)
        return parseFloat(amount).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    }

    // Function to calculate and update all totals
    function calculateAndDisplayTotals() {
        console.log("calculateAndDisplayTotals() called.");
        // 1. Calculate Subtotal
        let subtotal = 0;
        document.querySelectorAll('.formset-row').forEach((row, index) => {
            const deleteInput = row.querySelector(`[name="items-${index}-DELETE"]`); 
            if (deleteInput && deleteInput.checked) {
                console.log(`Skipping row ${index} marked for deletion.`);
                return;
            }

            const quantityInput = row.querySelector(`[name="items-${index}-quantity"]`);
            const itemSelect = row.querySelector(`[name="items-${index}-item"]`);

            if (quantityInput && itemSelect && itemSelect.value) {
                const quantity = parseInt(quantityInput.value) || 0;
                const itemId = itemSelect.value;
                
                // Ensure itemPrices object exists and has the item ID
                if (typeof itemPrices === 'object' && itemPrices !== null && itemPrices.hasOwnProperty(itemId)) {
                    const itemData = itemPrices[itemId]; 
                    const itemPrice = parseFloat(itemData.price) || 0;
                    subtotal += quantity * itemPrice;
                    console.log(`Row ${index}: Item Price: ${itemPrice}, Quantity: ${quantity}, Current Subtotal: ${subtotal}`);
                } else {
                    console.warn(`Row ${index}: Item data not found for ID: ${itemId} in itemPrices. Ensure itemPrices is correctly populated from Django context.`);
                }
            } else {
                console.log(`Row ${index}: Missing quantity, item select, or item value.`);
            }
        });
        currentSubtotal = subtotal;
        subtotalDisplay.value = formatCurrency(currentSubtotal);
        console.log("Calculated Subtotal:", currentSubtotal);

        // 2. Calculate Discounts (client-side estimation)
        currentLoyaltyDiscount = 0;
        // currentCouponDiscount is typically handled server-side upon form submission
        // For client-side display, you'd need an AJAX call to validate the coupon code
        // and fetch its discount amount. For now, it remains 0 here.

        // Loyalty Discount
        if (typeof BUSINESS_SETTINGS !== 'undefined' && BUSINESS_SETTINGS.enable_loyalty_point_redemption && redeemLoyaltyPointsCheckbox.checked && currentCustomerLoyaltyData) {
            const pointsRequired = BUSINESS_SETTINGS.loyalty_points_required_for_redemption;
            const customerPoints = currentCustomerLoyaltyData.loyalty_points;

            if (customerPoints >= pointsRequired) {
                // Check for branch specificity if enabled
                if (BUSINESS_SETTINGS.loyalty_redemption_is_branch_specific &&
                    currentCustomerLoyaltyData.branch_id !== null && // Ensure branch_id exists
                    currentCustomerLoyaltyData.branch_id !== parseInt(branchSelector.value)) {
                    
                    loyaltyRedemptionStatus.textContent = `Points can only be redeemed at customer's home branch.`;
                    loyaltyRedemptionStatus.style.color = 'red';
                    // Do NOT apply discount if not at home branch
                    redeemLoyaltyPointsCheckbox.checked = false; // Uncheck it if not allowed
                } else {
                    let discountValue = BUSINESS_SETTINGS.loyalty_redemption_discount_value;
                    let discountAmount = 0;
                    
                    let remainingTotalForLoyaltyCalculation = currentSubtotal - currentCouponDiscount; // Apply loyalty after coupon (if any)

                    if (BUSINESS_SETTINGS.loyalty_redemption_discount_type === 'percentage') {
                        discountAmount = (remainingTotalForLoyaltyCalculation * discountValue) / 100;
                        if (BUSINESS_SETTINGS.loyalty_redemption_max_discount_amount > 0 && discountAmount > BUSINESS_SETTINGS.loyalty_redemption_max_discount_amount) {
                            discountAmount = BUSINESS_SETTINGS.loyalty_redemption_max_discount_amount;
                        }
                    } else if (BUSINESS_SETTINGS.loyalty_redemption_discount_type === 'fixed') {
                        discountAmount = discountValue;
                        if (BUSINESS_SETTINGS.loyalty_redemption_max_discount_amount > 0 && discountAmount > BUSINESS_SETTINGS.loyalty_redemption_max_discount_amount) {
                            discountAmount = BUSINESS_SETTINGS.loyalty_redemption_max_discount_amount;
                        }
                    }
                    currentLoyaltyDiscount = Math.min(discountAmount, remainingTotalForLoyaltyCalculation); // Ensure discount doesn't exceed subtotal
                    loyaltyRedemptionStatus.textContent = `Redeeming ${pointsRequired} points for UGX ${formatCurrency(currentLoyaltyDiscount)} discount.`;
                    loyaltyRedemptionStatus.style.color = 'green';
                }
            } else {
                // Not enough points
                loyaltyRedemptionStatus.textContent = `Not enough points to redeem (${currentCustomerLoyaltyData.loyalty_points}/${pointsRequired}).`;
                loyaltyRedemptionStatus.style.color = 'red';
                redeemLoyaltyPointsCheckbox.checked = false; // Uncheck if not enough points
                currentLoyaltyDiscount = 0; // Ensure no discount
            }
        } else {
            // Loyalty redemption not enabled, checkbox not checked, or no customer data
            currentLoyaltyDiscount = 0; // No loyalty discount
            if (typeof BUSINESS_SETTINGS !== 'undefined' && BUSINESS_SETTINGS.enable_loyalty_point_redemption) {
                loyaltyRedemptionStatus.textContent = `Requires ${BUSINESS_SETTINGS.loyalty_points_required_for_redemption} points to redeem.`;
                loyaltyRedemptionStatus.style.color = 'gray';
            } else {
                loyaltyRedemptionStatus.textContent = ''; // Clear if feature disabled
            }
            redeemLoyaltyPointsCheckbox.checked = false; // Uncheck if ineligible or no customer
        }
        
        // Final total discount
        let totalDiscount = currentLoyaltyDiscount + currentCouponDiscount;

        // 3. Calculate Grand Total
        let grandTotal = currentSubtotal - totalDiscount;
        if (grandTotal < 0) grandTotal = 0;

        totalDiscountDisplay.value = formatCurrency(totalDiscount);
        grandTotalDisplay.value = formatCurrency(grandTotal);

        if (totalDiscount > 0) {
            discountDisplaySection.style.display = 'block';
        } else {
            discountDisplaySection.style.display = 'none';
        }
        console.log(`Totals updated: Subtotal=${currentSubtotal}, Loyalty Discount=${currentLoyaltyDiscount}, Total Discount=${totalDiscount}, Grand Total=${grandTotal}`);
    }

    // --- Customer Selection and Loyalty Data Fetching ---
    function toggleCustomerFields() {
        const selectedType = customerSelector.value;
        if (selectedType === 'existing') {
            existingCustomerFields.style.display = '';
            newCustomerFields.style.display = 'none';
            customerLoyaltyInfo.style.display = 'block';
            if (typeof BUSINESS_SETTINGS !== 'undefined' && BUSINESS_SETTINGS.enable_loyalty_point_redemption) {
                redeemLoyaltyPointsCheckbox.removeAttribute('disabled');
            } else {
                redeemLoyaltyPointsCheckbox.setAttribute('disabled', 'disabled');
            }
            existingCustomerDropdown.setAttribute('required', 'required');
            document.getElementById('id_new_customer_name').removeAttribute('required');
            document.getElementById('id_new_customer_phone').removeAttribute('required');
            if (existingCustomerDropdown.value) {
                fetchCustomerLoyaltyData(existingCustomerDropdown.value);
            } else {
                currentCustomerLoyaltyData = null;
                displayLoyaltyPoints.textContent = '0';
                displayTotalSpend.textContent = '0.00';
                displayTotalVisits.textContent = '0';
                loyaltyRedemptionSection.style.display = 'none';
                redeemLoyaltyPointsCheckbox.checked = false;
                loyaltyRedemptionStatus.textContent = 'Select an existing customer to see loyalty info.';
                loyaltyRedemptionStatus.style.color = 'gray';
                calculateAndDisplayTotals();
            }
        } else {
            existingCustomerFields.style.display = 'none';
            newCustomerFields.style.display = '';
            customerLoyaltyInfo.style.display = 'none';
            existingCustomerDropdown.removeAttribute('required');
            document.getElementById('id_new_customer_name').setAttribute('required', 'required');
            document.getElementById('id_new_customer_phone').setAttribute('required', 'required');
            currentCustomerLoyaltyData = null;
            displayLoyaltyPoints.textContent = '0';
            displayTotalSpend.textContent = '0.00';
            displayTotalVisits.textContent = '0';
            loyaltyRedemptionSection.style.display = 'none';
            redeemLoyaltyPointsCheckbox.checked = false;
            redeemLoyaltyPointsCheckbox.setAttribute('disabled', 'disabled');
            loyaltyRedemptionStatus.textContent = 'New customers cannot redeem points immediately.';
            loyaltyRedemptionStatus.style.color = 'gray';
            calculateAndDisplayTotals();
        }
        if (typeof BUSINESS_SETTINGS !== 'undefined' && BUSINESS_SETTINGS.enable_coupon_codes) {
            couponCodeSection.style.display = 'block';
        } else {
            couponCodeSection.style.display = 'none';
            couponCodeInput.value = '';
            couponStatus.textContent = '';
        }
    }

    async function fetchCustomerLoyaltyData(customerId) {
        console.log("fetchCustomerLoyaltyData() called for customer ID:", customerId);
        if (!customerId) {
            customerLoyaltyInfo.style.display = 'none';
            currentCustomerLoyaltyData = null;
            redeemLoyaltyPointsCheckbox.checked = false;
            redeemLoyaltyPointsCheckbox.setAttribute('disabled', 'disabled');
            loyaltyRedemptionStatus.textContent = 'No customer selected.';
            loyaltyRedemptionStatus.style.color = 'gray';
            calculateAndDisplayTotals();
            return;
        }

        try {
            const response = await fetch(`/get-customer-details/${customerId}/`, { // Corrected URL
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': CSRF_TOKEN, // Assumed CSRF_TOKEN is available globally
                }
            });
            const data = await response.json();

            console.log("Loyalty data received:", data);
            if (data.success) {
                currentCustomerLoyaltyData = data; // Store all data
                customerLoyaltyInfo.style.display = 'block';
                displayLoyaltyPoints.textContent = data.loyalty_points.toLocaleString();
                displayTotalSpend.textContent = formatCurrency(data.total_spend);
                displayTotalVisits.textContent = data.total_visits.toLocaleString();

                if (typeof BUSINESS_SETTINGS !== 'undefined' && BUSINESS_SETTINGS.enable_loyalty_point_redemption) {
                    loyaltyRedemptionSection.style.display = 'block';
                    redeemLoyaltyPointsCheckbox.removeAttribute('disabled'); // Enable checkbox if feature is on
                    if (data.loyalty_points >= BUSINESS_SETTINGS.loyalty_points_required_for_redemption) {
                        loyaltyRedemptionStatus.textContent = `Customer qualifies for loyalty discount! (Requires ${BUSINESS_SETTINGS.loyalty_points_required_for_redemption.toLocaleString()} points)`;
                        loyaltyRedemptionStatus.style.color = 'green';
                    } else {
                        redeemLoyaltyPointsCheckbox.checked = false; // Uncheck if not enough points
                        // Re-disable if not enough points, even if feature is enabled
                        redeemLoyaltyPointsCheckbox.setAttribute('disabled', 'disabled'); 
                        loyaltyRedemptionStatus.textContent = `Needs ${BUSINESS_SETTINGS.loyalty_points_required_for_redemption.toLocaleString()} points to redeem. Current: ${data.loyalty_points.toLocaleString()}`;
                        loyaltyRedemptionStatus.style.color = 'red';
                    }
                } else {
                    loyaltyRedemptionSection.style.display = 'none';
                    redeemLoyaltyPointsCheckbox.checked = false;
                    redeemLoyaltyPointsCheckbox.setAttribute('disabled', 'disabled'); // Disable if feature is off
                    loyaltyRedemptionStatus.textContent = ''; // No message if feature disabled
                }
            } else {
                customerLoyaltyInfo.style.display = 'none';
                redeemLoyaltyPointsCheckbox.checked = false;
                redeemLoyaltyPointsCheckbox.setAttribute('disabled', 'disabled');
                loyaltyRedemptionStatus.textContent = `Could not fetch loyalty data: ${data.error || 'Unknown error'}`;
                loyaltyRedemptionStatus.style.color = 'red';
                console.error("Error fetching loyalty data:", data.error);
                currentCustomerLoyaltyData = null; // Clear data on error
            }
            calculateAndDisplayTotals(); // Recalculate after loyalty data is updated
        } catch (error) {
            console.error('Error fetching customer loyalty data (AJAX request failed):', error);
            customerLoyaltyInfo.style.display = 'none';
            redeemLoyaltyPointsCheckbox.checked = false;
            redeemLoyaltyPointsCheckbox.setAttribute('disabled', 'disabled');
            loyaltyRedemptionStatus.textContent = 'Error fetching loyalty data. Check console.';
            loyaltyRedemptionStatus.style.color = 'red';
            currentCustomerLoyaltyData = null; // Clear data on error
            calculateAndDisplayTotals(); // Recalculate after error
        }
    }

    // --- Dynamic Formset Management ---
    function populateAllItemsDropdown(itemSelectElement, selectedItemId = null) {
        console.log("populateAllItemsDropdown() called for element:", itemSelectElement);
        itemSelectElement.innerHTML = `<option value="">-- Select Item --</option>`;
        if (typeof itemPrices !== 'object' || itemPrices === null || Object.keys(itemPrices).length === 0) {
            console.warn("itemPrices object is empty, null, or undefined. Cannot populate item dropdown.");
            return;
        }
        for (const itemId in itemPrices) {
            if (itemPrices.hasOwnProperty(itemId)) {
                const itemData = itemPrices[itemId];
                const option = document.createElement('option');
                option.value = itemId;
                option.textContent = itemData.name; // ONLY ITEM NAME
                if (selectedItemId && itemId == selectedItemId) {
                    option.selected = true;
                }
                itemSelectElement.appendChild(option);
            }
        }
    }

    function populateEmployeeDropdown(employeeSelectElement, branchId, selectedEmployeeId = null) {
        console.log(`populateEmployeeDropdown() called for element:`, employeeSelectElement, `Branch ID: ${branchId}, Selected Employee ID: ${selectedEmployeeId}`);
        if (!branchId) {
            employeeSelectElement.innerHTML = `<option value="">-- Select Branch First --</option>`;
            employeeSelectElement.setAttribute('disabled', 'disabled');
            employeeSelectElement.style.backgroundColor = '#e9ecef'; // Grey out
            return;
        }
        employeeSelectElement.removeAttribute('disabled');
        employeeSelectElement.style.backgroundColor = ''; // Remove grey out
        employeeSelectElement.innerHTML = `<option value="">Loading employees...</option>`;
        fetch(`/get-employees-by-branch/?branch_id=${branchId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log("Employees data received:", data);
                employeeSelectElement.innerHTML = `<option value="">-- Select Employee --</option>`;
                data.forEach(employee => {
                    const option = document.createElement('option');
                    option.value = employee.id;
                    option.textContent = employee.name;
                    if (selectedEmployeeId && employee.id == selectedEmployeeId) {
                        option.selected = true;
                    }
                    employeeSelectElement.appendChild(option);
                });
                // After populating, ensure the correct option is selected if one was pre-selected
                // and if the option actually exists in the new dropdown
                if (selectedEmployeeId && !employeeSelectElement.querySelector(`option[value="${selectedEmployeeId}"]`)) {
                    console.warn(`Previously selected employee ID ${selectedEmployeeId} not found in new list for branch ${branchId}. Resetting.`);
                    employeeSelectElement.value = ""; // Reset to default
                }
            })
            .catch(error => {
                console.error('Error fetching employees (AJAX request failed):', error);
                employeeSelectElement.innerHTML = `<option value="">-- Error loading employees --</option>`;
                employeeSelectElement.setAttribute('disabled', 'disabled'); // Disable on error
                employeeSelectElement.style.backgroundColor = '#e9ecef';
            });
    }

    function addFormsetRow() {
        console.log("addFormsetRow() called.");
        const totalFormsInput = document.getElementById('id_items-TOTAL_FORMS');
        let currentTotal = parseInt(totalFormsInput.value);

        const newIndex = currentTotal;

        const newRowHtml = `
            <tr class="formset-row">
                <td>
                    <select name="items-${newIndex}-item" id="id_items-${newIndex}-item" class="form-control item-select" required>
                        <option value="">-- Select Item --</option>
                    </select>
                </td>
                <td><input type="number" name="items-${newIndex}-quantity" id="id_items-${newIndex}-quantity" class="form-control quantity-input" value="1" min="1" required></td>
                <td>
                    <select name="items-${newIndex}-employee" id="id_items-${newIndex}-employee" class="form-control employee-select">
                        <option value="">-- Select Employee --</option>
                    </select>
                </td>
                <td>
                    <button type="button" class="btn btn-sm btn-outline-danger remove-item-button">Remove</button>
                    <input type="hidden" name="items-${newIndex}-id" id="id_items-${newIndex}-id">
                    <input type="hidden" name="items-${newIndex}-DELETE" id="id_items-${newIndex}-DELETE" value="false">
                </td>
            </tr>
        `;
        transactionItemsTableBody.insertAdjacentHTML('beforeend', newRowHtml);

        totalFormsInput.value = currentTotal + 1;

        // Select the newly added row and its elements
        const newRow = transactionItemsTableBody.lastElementChild;
        const newItemSelect = newRow.querySelector('.item-select');
        const newQuantityInput = newRow.querySelector('.quantity-input');
        const newEmployeeSelect = newRow.querySelector('.employee-select');
        const removeButton = newRow.querySelector('.remove-item-button');

        // Populate dropdowns and attach listeners for the new row
        populateAllItemsDropdown(newItemSelect);
        const selectedBranchId = branchSelector.value;
        populateEmployeeDropdown(newEmployeeSelect, selectedBranchId);

        newItemSelect.addEventListener('change', calculateAndDisplayTotals);
        newQuantityInput.addEventListener('input', calculateAndDisplayTotals);
        removeButton.addEventListener('click', removeFormsetRow);

        calculateAndDisplayTotals(); // Recalculate after adding a new row (even if empty initially)
    }

    function removeFormsetRow(event) {
        console.log("removeFormsetRow() called.");
        const row = event.target.closest('.formset-row');
        const deleteInput = row.querySelector('[name$="-DELETE"]');
        if (deleteInput) {
            deleteInput.value = 'on'; // Mark for deletion
            row.style.display = 'none'; // Hide the row
            console.log("Row marked for deletion and hidden.");
            calculateAndDisplayTotals();
        } else {
            // Fallback for direct removal if DELETE input isn't found (shouldn't happen with proper formsets)
            console.warn("DELETE input not found, directly removing row from DOM.");
            row.remove();
            calculateAndDisplayTotals();
        }
    }

    // --- Initial Setup and Event Attachments ---
    function initializeFormsetRows() {
        console.log("initializeFormsetRows() called. Attaching listeners to initial rows.");
        document.querySelectorAll('.formset-row').forEach((row, index) => {
            const deleteButton = row.querySelector('.remove-item-button');
            if (deleteButton) {
                deleteButton.addEventListener('click', removeFormsetRow);
            }
            const quantityInput = row.querySelector(`[name="items-${index}-quantity"]`);
            if (quantityInput) {
                quantityInput.addEventListener('input', calculateAndDisplayTotals);
            }
            const itemSelect = row.querySelector(`[name="items-${index}-item"]`);
            if (itemSelect) {
                itemSelect.addEventListener('change', calculateAndDisplayTotals);
                // Populate item dropdown for existing rows on load
                const initialSelectedItemId = itemSelect.value;
                populateAllItemsDropdown(itemSelect, initialSelectedItemId);
            }

            const employeeSelect = row.querySelector(`[name="items-${index}-employee"]`);
            if (employeeSelect) {
                const initialSelectedEmployeeId = employeeSelect.value;
                const currentBranchId = branchSelector.value;
                console.log(`Initial row ${index}: Employee dropdown for branch ${currentBranchId}, selected: ${initialSelectedEmployeeId}`);
                if (currentBranchId) {
                    populateEmployeeDropdown(employeeSelect, currentBranchId, initialSelectedEmployeeId);
                } else {
                    employeeSelect.innerHTML = `<option value="">-- Select Branch First --</option>`;
                    employeeSelect.setAttribute('disabled', 'disabled');
                    employeeSelect.style.backgroundColor = '#e9ecef';
                }
            }
        });
    }

    // --- Main Initializations ---
    // Event listeners for main form fields
    if (customerSelector) customerSelector.addEventListener("change", toggleCustomerFields);
    if (existingCustomerDropdown) existingCustomerDropdown.addEventListener('change', function() {
        fetchCustomerLoyaltyData(this.value);
    });
    if (redeemLoyaltyPointsCheckbox) redeemLoyaltyPointsCheckbox.addEventListener('change', calculateAndDisplayTotals);
    if (couponCodeInput) couponCodeInput.addEventListener('input', calculateAndDisplayTotals); // Or change event for coupon
    if (addItemButton) addItemButton.addEventListener('click', addFormsetRow);

    // Branch selector specific logic
    if (branchSelector) {
        branchSelector.addEventListener('change', function() {
            console.log("Branch selector changed to:", this.value);
            const selectedBranchId = this.value;
            // Re-populate all employee dropdowns on branch change
            document.querySelectorAll('.employee-select').forEach(employeeDropdown => {
                const currentSelectedEmployeeId = employeeDropdown.value; // Keep previously selected if possible
                populateEmployeeDropdown(employeeDropdown, selectedBranchId, currentSelectedEmployeeId);
            });
            // Re-evaluate customer loyalty data for branch-specific loyalty
            if (existingCustomerDropdown && existingCustomerDropdown.value) {
                fetchCustomerLoyaltyData(existingCustomerDropdown.value);
            }
            calculateAndDisplayTotals();
        });
    }

    // Initial setup calls
    toggleCustomerFields(); // Sets initial display of customer fields
    initializeFormsetRows(); // Attaches event listeners and populates dropdowns for initial rows

    // Show/hide coupon section based on business settings
    // This should ideally be within toggleCustomerFields if coupon visibility depends on customer type
    // If it's universally enabled/disabled, this is fine here.
    if (typeof BUSINESS_SETTINGS !== 'undefined' && BUSINESS_SETTINGS.enable_coupon_codes) {
        couponCodeSection.style.display = 'block';
    } else {
        couponCodeSection.style.display = 'none';
    }

    // Final initial calculation
    calculateAndDisplayTotals();
    console.log("revenue.js initialization complete.");
});
