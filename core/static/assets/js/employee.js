// employee.js
function toggleCustomRoleField() {
    const roleSelect = document.getElementById('id_role');
    const customRoleInput = document.getElementById('custom-role-container');
    customRoleInput.style.display = roleSelect.value === 'other' ? 'block' : 'none';
}

document.addEventListener('DOMContentLoaded', function() {
    const roleSelect = document.getElementById('id_role');
    if (roleSelect) {
        roleSelect.addEventListener('change', toggleCustomRoleField);
        toggleCustomRoleField(); // Run on page load to handle pre-filled values
    }
});