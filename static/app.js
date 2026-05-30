const state = window.__APP_STATE__ || { properties: [], expenses: [], incomes: [], metrics: {}, user: null };

const badgeClassByColor = {
    green: "success",
    orange: "warning",
    red: "danger",
    "#2ecc71": "success",
    "#f1c40f": "warning",
    "#e74c3c": "danger",
    gray: "",
};

const elements = {
    propertyGrid: document.getElementById("properties-grid"),
    expenseList: document.getElementById("expenses-list"),
    incomeList: document.getElementById("incomes-list"),
    expenseProperty: document.getElementById("expense-property"),
    incomeProperty: document.getElementById("income-property"),
    propertyModal: document.getElementById("property-modal"),
    propertyForm: document.getElementById("property-form"),
    propertyModalTitle: document.getElementById("property-modal-title"),
    tenantModal: document.getElementById("tenant-modal"),
    tenantForm: document.getElementById("tenant-form"),
    tenantModalTitle: document.getElementById("tenant-modal-title"),
    tenantPaymentsEditor: document.getElementById("tenant-payments-editor"),
    expenseForm: document.getElementById("expense-form"),
    incomeForm: document.getElementById("income-form"),
    userForm: document.getElementById("user-form"),
    expenseSubmit: document.getElementById("expense-submit"),
    expenseCancel: document.getElementById("expense-cancel"),
    incomeSubmit: document.getElementById("income-submit"),
    incomeCancel: document.getElementById("income-cancel"),
    metricsGrid: document.getElementById("metrics-grid"),
    trendChart: document.getElementById("trend-chart"),
    trendSummary: document.getElementById("trend-summary"),
    expenseBreakdown: document.getElementById("expense-breakdown"),
    toast: document.getElementById("toast"),
};

function formatCurrency(value) {
    return new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(value || 0);
}

function getMonthSequence(startDate) {
    if (!startDate) {
        return [];
    }

    const [year, month] = startDate.split("-").map(Number);
    if (!year || !month) {
        return [];
    }

    const current = new Date();
    const months = [];
    let cursorYear = year;
    let cursorMonth = month;

    while (cursorYear < current.getFullYear() || (cursorYear === current.getFullYear() && cursorMonth <= current.getMonth() + 1)) {
        months.push(`${cursorYear.toString().padStart(4, "0")}-${cursorMonth.toString().padStart(2, "0")}`);
        cursorMonth += 1;
        if (cursorMonth > 12) {
            cursorMonth = 1;
            cursorYear += 1;
        }
    }

    return months;
}

function formatMonthLabel(monthKey) {
    const [year, month] = monthKey.split("-").map(Number);
    const date = new Date(year, month - 1, 1);
    return new Intl.DateTimeFormat("es-ES", { month: "long", year: "numeric" }).format(date);
}

function shortMonthLabel(monthKey) {
    const [year, month] = monthKey.split("-").map(Number);
    const date = new Date(year, month - 1, 1);
    return new Intl.DateTimeFormat("es-ES", { month: "short" }).format(date);
}

function getTenantPaymentsFromEditor() {
    const rows = elements.tenantPaymentsEditor.querySelectorAll("[data-payment-month]");
    const payments = {};
    rows.forEach((row) => {
        const month = row.dataset.paymentMonth;
        const select = row.querySelector("select");
        payments[month] = select.value;
    });
    return payments;
}

function renderTenantPaymentsEditor(existingPayments = {}) {
    const startDate = document.getElementById("tenant-start-date").value;
    const months = getMonthSequence(startDate);

    if (!months.length) {
        elements.tenantPaymentsEditor.innerHTML = `<div class="empty-state">Selecciona una fecha de inicio para generar las mensualidades.</div>`;
        return;
    }

    elements.tenantPaymentsEditor.innerHTML = months.map((monthKey) => `
        <div class="payment-row" data-payment-month="${monthKey}">
            <div>
                <strong>${formatMonthLabel(monthKey)}</strong>
                <p class="muted">Estado del recibo mensual</p>
            </div>
            <select>
                <option value="PENDING" ${existingPayments[monthKey] === "PAID" ? "" : "selected"}>Pendiente</option>
                <option value="PAID" ${existingPayments[monthKey] === "PAID" ? "selected" : ""}>Pagado</option>
            </select>
        </div>
    `).join("");
}

function depositLabel(tenant) {
    if (!tenant.deposit_amount) {
        return "Sin fianza";
    }
    return tenant.deposit_paid
        ? `Fianza cobrada ${formatCurrency(tenant.deposit_amount)}`
        : `Fianza pendiente ${formatCurrency(tenant.deposit_amount)}`;
}

function propertyLocation(property) {
    return [property.city, property.zip_code, property.country].filter(Boolean).join(" · ") || "Ubicacion pendiente";
}

function showToast(message, isError = false) {
    elements.toast.textContent = message;
    elements.toast.hidden = false;
    elements.toast.style.background = isError ? "#bd3f3f" : "#1d2b36";
    window.clearTimeout(showToast.timeoutId);
    showToast.timeoutId = window.setTimeout(() => {
        elements.toast.hidden = true;
    }, 3000);
}

function openModal(id) {
    document.getElementById(id)?.showModal();
}

function closeModal(id) {
    document.getElementById(id)?.close();
}

function renderMetrics() {
    const cards = [
        ["Ingresos mensuales", formatCurrency(state.metrics.total_income)],
        ["Ingresos extra", formatCurrency(state.metrics.extra_income_current || 0)],
        ["Hipotecas", formatCurrency(state.metrics.mortgage_total)],
        ["Gastos del mes", formatCurrency(state.metrics.current_expenses)],
        ["Beneficio estimado", formatCurrency(state.metrics.estimated_profit), true],
    ];

    elements.metricsGrid.innerHTML = cards.map(([label, value, accent]) => `
        <article class="metric-card ${accent ? "accent" : ""}">
            <span>${label}</span>
            <strong>${value}</strong>
        </article>
    `).join("");
}

function renderAnalytics() {
    const trendData = state.metrics.trend_data || [];
    const maxValue = Math.max(
        1,
        ...trendData.flatMap((item) => [item.expected_income || 0, item.expenses || 0, Math.max(item.profit || 0, 0)]),
    );

    if (!trendData.length) {
        elements.trendChart.innerHTML = `<div class="empty-state">Aun no hay suficiente historico para mostrar tendencias.</div>`;
        elements.trendSummary.innerHTML = "";
        elements.expenseBreakdown.innerHTML = `<div class="empty-state">Sin gastos acumulados por categoria.</div>`;
        return;
    }

    elements.trendChart.innerHTML = trendData.map((item) => `
        <div class="trend-month">
            <div class="trend-bars">
                <div class="trend-bar income" style="height:${(item.expected_income / maxValue) * 140 + 8}px" title="Ingresos ${formatCurrency(item.expected_income)}"></div>
                <div class="trend-bar expense" style="height:${(item.expenses / maxValue) * 140 + 8}px" title="Gastos ${formatCurrency(item.expenses)}"></div>
                <div class="trend-bar profit" style="height:${(Math.max(item.profit, 0) / maxValue) * 140 + 8}px" title="Beneficio ${formatCurrency(item.profit)}"></div>
            </div>
            <div class="trend-label">${shortMonthLabel(item.month)}</div>
        </div>
    `).join("");

    elements.trendSummary.innerHTML = [
        ["Cobrado este mes", formatCurrency(state.metrics.paid_income_current || 0)],
        ["Ratio de cobro", `${state.metrics.collection_rate_current || 0}%`],
        ["Variacion beneficio", formatCurrency(state.metrics.profit_delta || 0)],
        ["Beneficio acumulado", formatCurrency(state.metrics.accumulated_profit || 0)],
        ["Inquilinos con retraso", `${state.metrics.late_tenants || 0}`],
    ].map(([label, value]) => `
        <div class="summary-pill">
            <span>${label}</span>
            <strong>${value}</strong>
        </div>
    `).join("");

    const breakdown = state.metrics.expense_breakdown || [];
    const incomeBreakdown = state.metrics.income_breakdown || [];
    const maxBreakdown = Math.max(1, ...breakdown.map((item) => item.amount || 0));
    const expenseMarkup = breakdown.length
        ? `<div class="breakdown-section"><p class="eyebrow">Salidas</p>${breakdown.map((item) => `
            <div class="breakdown-row">
                <div class="breakdown-meta">
                    <strong>${item.category}</strong>
                    <div class="breakdown-bar" style="width:${(item.amount / maxBreakdown) * 100}%"></div>
                </div>
                <span>${formatCurrency(item.amount)}</span>
            </div>
        `).join("")}</div>`
        : `<div class="empty-state">Sin gastos acumulados por categoria.</div>`;
    const maxIncomeBreakdown = Math.max(1, ...incomeBreakdown.map((item) => item.amount || 0));
    const incomeMarkup = incomeBreakdown.length
        ? `<div class="breakdown-section"><p class="eyebrow">Entradas</p>${incomeBreakdown.map((item) => `
            <div class="breakdown-row">
                <div class="breakdown-meta">
                    <strong>${item.category}</strong>
                    <div class="breakdown-bar income" style="width:${(item.amount / maxIncomeBreakdown) * 100}%"></div>
                </div>
                <span>${formatCurrency(item.amount)}</span>
            </div>
        `).join("")}</div>`
        : `<div class="empty-state">Sin ingresos manuales por categoria.</div>`;
    elements.expenseBreakdown.innerHTML = expenseMarkup + incomeMarkup;
}

function renderExpenses() {
    const items = [...state.expenses]
        .sort((a, b) => (b.date || "").localeCompare(a.date || ""));

    if (!items.length) {
        elements.expenseList.innerHTML = `<div class="empty-state">Todavia no hay gastos registrados.</div>`;
        return;
    }

    elements.expenseList.innerHTML = items.map((expense) => {
        const property = state.properties.find((item) => item.id === expense.property_id);
        return `
            <article class="expense-item">
                <div>
                    <p><strong>${expense.description}</strong></p>
                    <p class="muted">${expense.category} · ${expense.date || "Sin fecha"}${property ? ` · ${property.address}` : ""}</p>
                </div>
                <div class="movement-actions">
                    <strong>${formatCurrency(expense.amount)}</strong>
                    <button class="text-button" type="button" data-edit-expense="${expense.id}">Editar</button>
                    <button class="text-button danger-text" type="button" data-delete-expense="${expense.id}">Eliminar</button>
                </div>
            </article>
        `;
    }).join("");
}

function renderIncomes() {
    const items = [...state.incomes]
        .sort((a, b) => (b.date || "").localeCompare(a.date || ""));

    if (!items.length) {
        elements.incomeList.innerHTML = `<div class="empty-state">Todavia no hay ingresos manuales registrados.</div>`;
        return;
    }

    elements.incomeList.innerHTML = items.map((income) => {
        const property = state.properties.find((item) => item.id === income.property_id);
        return `
            <article class="expense-item">
                <div>
                    <p><strong>${income.description}</strong></p>
                    <p class="muted">${income.category} · ${income.date || "Sin fecha"}${property ? ` · ${property.address}` : ""}</p>
                </div>
                <div class="movement-actions">
                    <strong>${formatCurrency(income.amount)}</strong>
                    ${income.is_editable ? `<button class="text-button" type="button" data-edit-income="${income.id}">Editar</button>
                    <button class="text-button danger-text" type="button" data-delete-income="${income.id}">Eliminar</button>` : `<span class="muted">Desde fianza</span>`}
                </div>
            </article>
        `;
    }).join("");
}

function renderExpensePropertyOptions() {
    const currentValue = elements.expenseProperty.value;
    const currentIncomeValue = elements.incomeProperty.value;
    const options = `<option value="">Sin asociar</option>` + state.properties.map((property) => `
        <option value="${property.id}">${property.address}</option>
    `).join("");
    elements.expenseProperty.innerHTML = options;
    elements.incomeProperty.innerHTML = options;
    elements.expenseProperty.value = currentValue;
    elements.incomeProperty.value = currentIncomeValue;
}

function resetExpenseForm() {
    elements.expenseForm.reset();
    document.getElementById("expense-id").value = "";
    elements.expenseSubmit.textContent = "Guardar gasto";
    elements.expenseCancel.hidden = true;
}

function fillExpenseForm(expense) {
    document.getElementById("expense-id").value = expense.id;
    document.getElementById("expense-description").value = expense.description || "";
    document.getElementById("expense-amount").value = expense.amount || 0;
    document.getElementById("expense-category").value = expense.category || "OTHER";
    document.getElementById("expense-date").value = expense.date || "";
    document.getElementById("expense-property").value = expense.property_id || "";
    elements.expenseSubmit.textContent = "Actualizar gasto";
    elements.expenseCancel.hidden = false;
}

function resetIncomeForm() {
    elements.incomeForm.reset();
    document.getElementById("income-id").value = "";
    elements.incomeSubmit.textContent = "Guardar ingreso";
    elements.incomeCancel.hidden = true;
}

function fillIncomeForm(income) {
    document.getElementById("income-id").value = income.id;
    document.getElementById("income-description").value = income.description || "";
    document.getElementById("income-amount").value = income.amount || 0;
    document.getElementById("income-category").value = income.category || "OTHER";
    document.getElementById("income-date").value = income.date || "";
    document.getElementById("income-property").value = income.property_id || "";
    elements.incomeSubmit.textContent = "Actualizar ingreso";
    elements.incomeCancel.hidden = false;
}

function renderTenants(property) {
    if (!property.tenants.length) {
        return `<div class="empty-state">Aun no hay inquilinos en esta propiedad.</div>`;
    }

    return `<div class="tenant-list">${property.tenants.map((tenant) => `
        <article class="tenant-card">
            <div class="tenant-summary">
                <span class="badge ${badgeClassByColor[tenant.status_color] || ""}">${tenant.status_label}</span>
                <span class="badge">${formatCurrency(tenant.rent)}</span>
                <span class="badge">${tenant.start_date || "Sin fecha de inicio"}</span>
                <span class="badge ${tenant.deposit_paid ? "success" : ""}">${depositLabel(tenant)}</span>
            </div>
            <h5>${tenant.name}</h5>
            <p class="muted">Pagos registrados: ${Object.keys(tenant.payments || {}).length}</p>
            <div class="tenant-actions">
                <button class="button secondary" type="button" data-mark-paid="${property.id}:${tenant.id}">Marcar pagado</button>
                <button class="button primary" type="button" data-receipt="${property.id}:${tenant.id}">Ver recibo</button>
                <button class="button primary" type="button" data-edit-tenant="${property.id}:${tenant.id}">Editar</button>
                <button class="icon-button" type="button" data-delete-tenant="${property.id}:${tenant.id}">Eliminar</button>
            </div>
        </article>
    `).join("")}</div>`;
}

function renderProperties() {
    if (!state.properties.length) {
        elements.propertyGrid.innerHTML = `<div class="empty-state">No hay propiedades todavia. Empieza creando la primera.</div>`;
        return;
    }

    elements.propertyGrid.innerHTML = state.properties.map((property) => `
        <article class="property-card">
            <div class="property-banner"></div>
            <div>
                <p class="property-meta">${propertyLocation(property)}</p>
                <h4>${property.address}</h4>
            </div>
            <div class="property-summary">
                <span class="badge ${badgeClassByColor[property.status_color] || ""}">${property.status_label}</span>
                <span class="badge">${property.tenants.length} inquilino(s)</span>
                <span class="badge">${formatCurrency(property.profit)} beneficio</span>
            </div>
            <p class="muted">Hipoteca: ${formatCurrency(property.mortgage_monthly)} · Ref. catastral: ${property.cadastral_ref || "Pendiente"}</p>
            <div class="property-actions">
                <button class="button primary" type="button" data-add-tenant="${property.id}">Nuevo inquilino</button>
                <button class="button secondary" type="button" data-edit-property="${property.id}">Editar propiedad</button>
            </div>
            ${renderTenants(property)}
        </article>
    `).join("");
}

function renderAll() {
    renderMetrics();
    renderAnalytics();
    renderProperties();
    renderExpenses();
    renderIncomes();
    renderExpensePropertyOptions();
}

function syncState(nextState) {
    state.user = nextState.user;
    state.metrics = nextState.metrics;
    state.properties = nextState.properties;
    state.expenses = nextState.expenses;
    state.incomes = nextState.incomes;
    renderAll();
}

async function sendJson(url, options = {}) {
    const response = await fetch(url, {
        method: options.method || "GET",
        headers: {
            "Content-Type": "application/json",
        },
        body: options.body ? JSON.stringify(options.body) : undefined,
    });

    const payload = await response.json();
    if (!response.ok) {
        throw new Error(payload.detail || "No se pudo completar la accion.");
    }
    return payload;
}

function resetPropertyForm() {
    elements.propertyForm.reset();
    document.getElementById("property-id").value = "";
    document.getElementById("property-country").value = "España";
    document.getElementById("property-mortgage").value = "0";
    elements.propertyModalTitle.textContent = "Nueva propiedad";
}

function fillPropertyForm(property) {
    document.getElementById("property-id").value = property.id;
    document.getElementById("property-address").value = property.address || "";
    document.getElementById("property-city").value = property.city || "";
    document.getElementById("property-zip").value = property.zip_code || "";
    document.getElementById("property-country").value = property.country || "España";
    document.getElementById("property-cadastral").value = property.cadastral_ref || "";
    document.getElementById("property-mortgage").value = property.mortgage_monthly || 0;
    document.getElementById("property-utilities").checked = Boolean(property.utilities_included);
    elements.propertyModalTitle.textContent = "Editar propiedad";
}

function resetTenantForm(propertyId = "") {
    elements.tenantForm.reset();
    document.getElementById("tenant-property-id").value = propertyId;
    document.getElementById("tenant-id").value = "";
    document.getElementById("tenant-start-date").value = new Date().toISOString().slice(0, 10);
    document.getElementById("tenant-deposit-amount").value = "0";
    document.getElementById("tenant-deposit-payment-date").value = "";
    document.getElementById("tenant-deposit-paid").checked = false;
    elements.tenantModalTitle.textContent = "Nuevo inquilino";
    renderTenantPaymentsEditor();
}

function fillTenantForm(propertyId, tenant) {
    document.getElementById("tenant-property-id").value = propertyId;
    document.getElementById("tenant-id").value = tenant.id;
    document.getElementById("tenant-name").value = tenant.name || "";
    document.getElementById("tenant-rent").value = tenant.rent || 0;
    document.getElementById("tenant-start-date").value = tenant.start_date || "";
    document.getElementById("tenant-deposit-amount").value = tenant.deposit_amount || 0;
    document.getElementById("tenant-deposit-payment-date").value = tenant.deposit_payment_date || "";
    document.getElementById("tenant-deposit-paid").checked = Boolean(tenant.deposit_paid);
    elements.tenantModalTitle.textContent = "Editar inquilino";
    renderTenantPaymentsEditor(tenant.payments || {});
}

document.addEventListener("click", async (event) => {
    const openTarget = event.target.closest("[data-open-modal]");
    if (openTarget) {
        if (openTarget.dataset.openModal === "property-modal") {
            resetPropertyForm();
        }
        openModal(openTarget.dataset.openModal);
    }

    const closeTarget = event.target.closest("[data-close-modal]");
    if (closeTarget) {
        closeModal(closeTarget.dataset.closeModal);
    }

    const editPropertyButton = event.target.closest("[data-edit-property]");
    if (editPropertyButton) {
        const property = state.properties.find((item) => item.id === editPropertyButton.dataset.editProperty);
        if (!property) {
            return;
        }
        fillPropertyForm(property);
        openModal("property-modal");
    }

    const addTenantButton = event.target.closest("[data-add-tenant]");
    if (addTenantButton) {
        resetTenantForm(addTenantButton.dataset.addTenant);
        openModal("tenant-modal");
    }

    const editTenantButton = event.target.closest("[data-edit-tenant]");
    if (editTenantButton) {
        const [propertyId, tenantId] = editTenantButton.dataset.editTenant.split(":");
        const property = state.properties.find((item) => item.id === propertyId);
        const tenant = property?.tenants.find((item) => item.id === tenantId);
        if (!property || !tenant) {
            return;
        }
        fillTenantForm(propertyId, tenant);
        openModal("tenant-modal");
    }

    const markPaidButton = event.target.closest("[data-mark-paid]");
    if (markPaidButton) {
        const [propertyId, tenantId] = markPaidButton.dataset.markPaid.split(":");
        try {
            const nextState = await sendJson(`/api/properties/${propertyId}/tenants/${tenantId}/mark-paid`, {
                method: "POST",
            });
            syncState(nextState);
            showToast("Pago marcado correctamente.");
        } catch (error) {
            showToast(error.message, true);
        }
    }

    const receiptButton = event.target.closest("[data-receipt]");
    if (receiptButton) {
        const [propertyId, tenantId] = receiptButton.dataset.receipt.split(":");
        window.open(`/api/properties/${propertyId}/tenants/${tenantId}/receipt`, "_blank", "noopener");
    }

    const deleteTenantButton = event.target.closest("[data-delete-tenant]");
    if (deleteTenantButton) {
        const [propertyId, tenantId] = deleteTenantButton.dataset.deleteTenant.split(":");
        if (!window.confirm("Se eliminara el inquilino de esta propiedad.")) {
            return;
        }
        try {
            const nextState = await sendJson(`/api/properties/${propertyId}/tenants/${tenantId}`, {
                method: "DELETE",
            });
            syncState(nextState);
            showToast("Inquilino eliminado.");
        } catch (error) {
            showToast(error.message, true);
        }
    }

    const editExpenseButton = event.target.closest("[data-edit-expense]");
    if (editExpenseButton) {
        const expense = state.expenses.find((item) => item.id === editExpenseButton.dataset.editExpense);
        if (!expense) {
            return;
        }
        fillExpenseForm(expense);
        document.getElementById("expense-description").scrollIntoView({ behavior: "smooth", block: "center" });
    }

    const deleteExpenseButton = event.target.closest("[data-delete-expense]");
    if (deleteExpenseButton) {
        if (!window.confirm("Se eliminara este gasto.")) {
            return;
        }
        try {
            const nextState = await sendJson(`/api/expenses/${deleteExpenseButton.dataset.deleteExpense}`, {
                method: "DELETE",
            });
            syncState(nextState);
            resetExpenseForm();
            showToast("Gasto eliminado.");
        } catch (error) {
            showToast(error.message, true);
        }
    }

    const editIncomeButton = event.target.closest("[data-edit-income]");
    if (editIncomeButton) {
        const income = state.incomes.find((item) => item.id === editIncomeButton.dataset.editIncome);
        if (!income) {
            return;
        }
        fillIncomeForm(income);
        document.getElementById("income-description").scrollIntoView({ behavior: "smooth", block: "center" });
    }

    const deleteIncomeButton = event.target.closest("[data-delete-income]");
    if (deleteIncomeButton) {
        if (!window.confirm("Se eliminara este ingreso.")) {
            return;
        }
        try {
            const nextState = await sendJson(`/api/incomes/${deleteIncomeButton.dataset.deleteIncome}`, {
                method: "DELETE",
            });
            syncState(nextState);
            resetIncomeForm();
            showToast("Ingreso eliminado.");
        } catch (error) {
            showToast(error.message, true);
        }
    }
});

elements.propertyForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const propertyId = document.getElementById("property-id").value;
    const body = {
        address: document.getElementById("property-address").value,
        city: document.getElementById("property-city").value,
        zip_code: document.getElementById("property-zip").value,
        country: document.getElementById("property-country").value,
        cadastral_ref: document.getElementById("property-cadastral").value,
        mortgage_monthly: document.getElementById("property-mortgage").value,
        utilities_included: document.getElementById("property-utilities").checked,
    };

    try {
        const nextState = await sendJson(propertyId ? `/api/properties/${propertyId}` : "/api/properties", {
            method: propertyId ? "PUT" : "POST",
            body,
        });
        syncState(nextState);
        closeModal("property-modal");
        showToast(propertyId ? "Propiedad actualizada." : "Propiedad creada.");
    } catch (error) {
        showToast(error.message, true);
    }
});

elements.tenantForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const propertyId = document.getElementById("tenant-property-id").value;
    const tenantId = document.getElementById("tenant-id").value;
    const body = {
        name: document.getElementById("tenant-name").value,
        rent: document.getElementById("tenant-rent").value,
        start_date: document.getElementById("tenant-start-date").value,
        deposit_amount: document.getElementById("tenant-deposit-amount").value,
        deposit_paid: document.getElementById("tenant-deposit-paid").checked,
        deposit_payment_date: document.getElementById("tenant-deposit-payment-date").value,
        payments: getTenantPaymentsFromEditor(),
    };

    try {
        const nextState = await sendJson(
            tenantId
                ? `/api/properties/${propertyId}/tenants/${tenantId}`
                : `/api/properties/${propertyId}/tenants`,
            {
                method: tenantId ? "PUT" : "POST",
                body,
            },
        );
        syncState(nextState);
        closeModal("tenant-modal");
        showToast(tenantId ? "Inquilino actualizado." : "Inquilino creado.");
    } catch (error) {
        showToast(error.message, true);
    }
});

document.getElementById("tenant-start-date").addEventListener("change", () => {
    const tenantId = document.getElementById("tenant-id").value;
    let existingPayments = {};

    if (tenantId) {
        const propertyId = document.getElementById("tenant-property-id").value;
        const property = state.properties.find((item) => item.id === propertyId);
        const tenant = property?.tenants.find((item) => item.id === tenantId);
        existingPayments = tenant?.payments || {};
    } else {
        existingPayments = getTenantPaymentsFromEditor();
    }

    renderTenantPaymentsEditor(existingPayments);
});

elements.expenseForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(elements.expenseForm);
    const body = Object.fromEntries(formData.entries());
    const expenseId = document.getElementById("expense-id").value;

    try {
        const nextState = await sendJson(expenseId ? `/api/expenses/${expenseId}` : "/api/expenses", {
            method: expenseId ? "PUT" : "POST",
            body,
        });
        syncState(nextState);
        resetExpenseForm();
        showToast(expenseId ? "Gasto actualizado." : "Gasto guardado.");
    } catch (error) {
        showToast(error.message, true);
    }
});

elements.incomeForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(elements.incomeForm);
    const body = Object.fromEntries(formData.entries());
    const incomeId = document.getElementById("income-id").value;

    try {
        const nextState = await sendJson(incomeId ? `/api/incomes/${incomeId}` : "/api/incomes", {
            method: incomeId ? "PUT" : "POST",
            body,
        });
        syncState(nextState);
        resetIncomeForm();
        showToast(incomeId ? "Ingreso actualizado." : "Ingreso guardado.");
    } catch (error) {
        showToast(error.message, true);
    }
});

elements.expenseCancel.addEventListener("click", resetExpenseForm);
elements.incomeCancel.addEventListener("click", resetIncomeForm);

elements.userForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(elements.userForm);
    const body = Object.fromEntries(formData.entries());

    try {
        const nextState = await sendJson("/api/user", {
            method: "POST",
            body,
        });
        syncState(nextState);
        showToast("Propietario actualizado.");
    } catch (error) {
        showToast(error.message, true);
    }
});

renderAll();
