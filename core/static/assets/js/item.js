function toggleItemFields() {
    const itemType = document.getElementById('item-type').value;
    const servicePriceField = document.getElementById('service-price-field');
    const productCostField = document.getElementById('product-cost-field');
    
    if (itemType === 'product') {
        productCostField.style.display = 'block';
        document.getElementById('cost-price').setAttribute('required', 'required');
    } else {
        productCostField.style.display = 'none';
        document.getElementById('cost-price').removeAttribute('required');
    }
}