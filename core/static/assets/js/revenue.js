
document.addEventListener("DOMContentLoaded", function () {
    const customerSelector = document.getElementById("id_customer_selector");
    const newCustomerFields = document.getElementById("new_customer_fields");

    customerSelector.addEventListener("change", function () {
        if (this.value === "new_customer") {
            newCustomerFields.style.display = "block";
        } else {
            newCustomerFields.style.display = "none";
        }
    });

    const itemCategory = document.getElementById("item_category");
    const existingItemSection = document.getElementById("existing_item_section");
    const newItemFields = document.getElementById("new_item_fields");

    itemCategory.addEventListener("change", function () {
        const category = this.value;
        if (category) {
            existingItemSection.style.display = "block";
            fetch(`/get-items-by-category/?category=${category}`)
                .then(response => response.json())
                .then(data => {
                    const dropdown = document.getElementById("item_dropdown");
                    dropdown.innerHTML = `<option value="">-- Select Item --</option>`;
                    data.forEach(item => {
                        dropdown.innerHTML += `<option value="${item.id}">${item.name}</option>`;
                    });
                    dropdown.innerHTML += `<option value="new">+ Add New Item</option>`;
                });
        } else {
            existingItemSection.style.display = "none";
        }
    });

    const itemDropdown = document.getElementById("item_dropdown");
    itemDropdown.addEventListener("change", function () {
        if (this.value === "new") {
            newItemFields.style.display = "block";
        } else {
            newItemFields.style.display = "none";
        }
    });
});

