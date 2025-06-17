function toggleItemFields() {
    const itemTypeSelect = document.getElementById('item-type');
    const productCostField = document.getElementById('product-cost-field');
    const costPriceInput = document.getElementById('cost-price');
    productCostField.style.display = itemTypeSelect.value === 'product' ? 'block' : 'none';
    if (itemTypeSelect.value !== 'product' && costPriceInput) {
        costPriceInput.value = '';
        costPriceInput.required = false;
    } else if (itemTypeSelect.value === 'product' && costPriceInput) {
        costPriceInput.required = true;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const itemTypeSelect = document.getElementById('item-type');
    if (itemTypeSelect) {
        itemTypeSelect.addEventListener('change', toggleItemFields);
        toggleItemFields();
    }
});