const predefinedServices = [
    "Hair Cuts", "Hair Plaiting", "Massage",
    "Manicure and Pedicure", "Hair washing", "Hair styling", "Hair treatment"
];

function addService() {
    const container = document.getElementById("services-container");

    const wrapper = document.createElement("div");
    wrapper.classList.add("input-group", "mb-2", "service-row");

    const select = document.createElement("select");
    select.name = "services[]";
    select.className = "form-select";
    select.innerHTML = `
        <option value="">-- Select service or add new --</option>
        ${predefinedServices.map(service => `<option value="${service}">${service}</option>`).join("")}
        <option value="custom">Other (Specify below)</option>
    `;

    const customInput = document.createElement("input");
    customInput.type = "text";
    customInput.name = "custom_services[]";
    customInput.placeholder = "Custom Service Name";
    customInput.className = "form-control";
    customInput.style.display = "none";

    const priceInput = document.createElement("input");
    priceInput.type = "number";
    priceInput.name = "prices[]";
    priceInput.placeholder = "Price";
    priceInput.className = "form-control";
    priceInput.required = true;

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "btn btn-outline-danger";
    removeButton.textContent = "Remove";
    removeButton.onclick = () => wrapper.remove();

    select.addEventListener("change", () => {
        customInput.style.display = (select.value === "custom") ? "block" : "none";
    });

    wrapper.appendChild(select);
    wrapper.appendChild(customInput);
    wrapper.appendChild(priceInput);
    wrapper.appendChild(removeButton);
    container.appendChild(wrapper);
}

function removeServiceRow(button) {
    const row = button.closest(".service-row");
    if (row) {
        row.remove();
    }
}
