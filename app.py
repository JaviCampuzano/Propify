import json
import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from data_manager import DataManager


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = os.getenv("GESTOR_DATA_FILE", "datos_v2.json")

app = FastAPI(title="Propify", version="3.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

data_manager = DataManager(DATA_FILE)
data_manager.load_data()


def build_property_payload(prop):
    status_label, status_color = prop.check_payment_status()
    return {
        "id": prop.id,
        "address": prop.address,
        "country": prop.country,
        "city": prop.city,
        "zip_code": prop.zip_code,
        "cadastral_ref": prop.cadastral_ref,
        "mortgage_monthly": prop.mortgage_monthly,
        "utilities_included": prop.utilities_included,
        "electricity_contract_path": prop.electricity_contract_path,
        "water_contract_path": prop.water_contract_path,
        "mortgage_contract_path": prop.mortgage_contract_path,
        "status_label": status_label,
        "status_color": status_color,
        "profit": prop.calculate_profit(data_manager.expenses, data_manager.get_all_incomes()),
        "tenants": [build_tenant_payload(tenant) for tenant in prop.tenants],
    }


def build_tenant_payload(tenant):
    status_label, status_color = tenant.get_current_status()
    color_aliases = {
        "#2ecc71": "green",
        "#f1c40f": "orange",
        "#e74c3c": "red",
    }
    return {
        "id": tenant.id,
        "name": tenant.name,
        "rent": tenant.rent,
        "start_date": tenant.start_date,
        "payments": tenant.payments,
        "deposit_amount": tenant.deposit_amount,
        "deposit_paid": tenant.deposit_paid,
        "deposit_payment_date": tenant.deposit_payment_date,
        "payment_schedule": [
            {"month": month_key, "status": tenant.payments.get(month_key, "PENDING")}
            for month_key in tenant.get_active_month_keys()
        ],
        "lease_contract_path": tenant.lease_contract_path,
        "deposit_contract_path": tenant.deposit_contract_path,
        "status_label": status_label,
        "status_color": color_aliases.get(status_color, status_color),
    }


def build_expense_payload(expense):
    return {
        "id": expense.id,
        "amount": expense.amount,
        "category": expense.category,
        "description": expense.description,
        "date": expense.date,
        "property_id": expense.property_id,
    }


def build_income_payload(income):
    return {
        "id": income.id,
        "amount": income.amount,
        "category": income.category,
        "description": income.description,
        "date": income.date,
        "property_id": income.property_id,
        "is_editable": not str(income.id).startswith("deposit-"),
    }


def format_currency(amount):
    return f"{float(amount):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def format_month_label(month_key):
    month_date = datetime.strptime(f"{month_key}-01", "%Y-%m-%d")
    month_names = {
        1: "enero",
        2: "febrero",
        3: "marzo",
        4: "abril",
        5: "mayo",
        6: "junio",
        7: "julio",
        8: "agosto",
        9: "septiembre",
        10: "octubre",
        11: "noviembre",
        12: "diciembre",
    }
    return f"{month_names[month_date.month].capitalize()} {month_date.year}"


def build_receipt_payload(prop, tenant):
    today = datetime.now()
    month_key = today.strftime("%Y-%m")
    status_raw = tenant.payments.get(month_key, "PENDING")
    status_label = {
        "PAID": "Pagado",
        "PENDING": "Pendiente",
    }.get(status_raw, "Pendiente")

    location_bits = [prop.city, prop.zip_code, prop.country]
    location = " · ".join(filter(None, location_bits)) or "Ubicacion pendiente"
    owner = data_manager.user.to_dict() if data_manager.user else None
    receipt_ref = f"REC-{today.strftime('%Y%m')}-{tenant.id[:4].upper()}-{prop.id[:4].upper()}"
    concept = f"Renta mensual correspondiente a {format_month_label(month_key).lower()}."

    return {
        "reference": receipt_ref,
        "issue_date": today.strftime("%d/%m/%Y"),
        "period_label": format_month_label(month_key),
        "status_label": status_label,
        "status_class": "success" if status_label == "Pagado" else "warning",
        "amount": tenant.rent,
        "amount_label": format_currency(tenant.rent),
        "tenant": {
            "name": tenant.name,
            "start_date": tenant.start_date,
            "deposit_amount": format_currency(tenant.deposit_amount or 0),
            "deposit_paid": tenant.deposit_paid,
        },
        "property": {
            "address": prop.address,
            "location": location,
            "cadastral_ref": prop.cadastral_ref or "Pendiente",
        },
        "owner": owner,
        "concept": concept,
        "notes": "Este recibo acredita la emision del cobro mensual del alquiler. Se recomienda conservarlo junto con el justificante bancario.",
    }


def get_app_state():
    metrics = data_manager.get_dashboard_metrics()
    properties = [build_property_payload(prop) for prop in data_manager.properties]
    expenses = [build_expense_payload(expense) for expense in data_manager.expenses]
    incomes = [build_income_payload(income) for income in data_manager.get_all_incomes()]
    user = data_manager.user.to_dict() if data_manager.user else None
    metrics["recent_expenses"] = [build_expense_payload(expense) for expense in metrics["recent_expenses"]]
    metrics["recent_incomes"] = [build_income_payload(income) for income in metrics["recent_incomes"]]
    return {"user": user, "metrics": metrics, "properties": properties, "expenses": expenses, "incomes": incomes}


def require_text(payload, field_name):
    value = str(payload.get(field_name, "")).strip()
    if not value:
        raise HTTPException(status_code=400, detail=f"El campo '{field_name}' es obligatorio.")
    return value


def parse_float(payload, field_name, default=None):
    raw_value = payload.get(field_name, default)
    if raw_value in (None, ""):
        if default is None:
            raise HTTPException(status_code=400, detail=f"El campo '{field_name}' es obligatorio.")
        return default
    try:
        return float(raw_value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"El campo '{field_name}' debe ser numerico.") from exc


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    state = get_app_state()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "state": state,
            "state_json": json.dumps(state, ensure_ascii=False),
        },
    )


@app.get("/health")
async def healthcheck():
    return {"ok": True}


@app.get("/brand/propify.png")
async def brand_logo():
    logo_path = BASE_DIR / "propify.png"
    if not logo_path.exists():
        raise HTTPException(status_code=404, detail="Logo no encontrado.")
    return FileResponse(logo_path)


@app.get("/api/state")
async def api_state():
    return JSONResponse(get_app_state())


@app.post("/api/user")
async def save_user(request: Request):
    payload = await request.json()
    name = require_text(payload, "name")
    client_code = str(payload.get("client_code", "")).strip()
    password = require_text(payload, "password")
    data_manager.set_user(name, client_code, password)
    return JSONResponse(get_app_state())


@app.post("/api/properties")
async def create_property(request: Request):
    payload = await request.json()
    address = require_text(payload, "address")
    created = data_manager.add_property(address)
    if not created:
        raise HTTPException(status_code=409, detail="Ya existe una propiedad con esa direccion.")

    prop = data_manager.properties[-1]
    data_manager.update_property(
        prop.id,
        address=address,
        city=str(payload.get("city", "")).strip(),
        zip_code=str(payload.get("zip_code", "")).strip(),
        country=str(payload.get("country", "España")).strip() or "España",
        cadastral_ref=str(payload.get("cadastral_ref", "")).strip(),
        mortgage_monthly=parse_float(payload, "mortgage_monthly", default=0.0),
        utilities_included=bool(payload.get("utilities_included", False)),
    )
    return JSONResponse(get_app_state(), status_code=201)


@app.put("/api/properties/{property_id}")
async def update_property(property_id: str, request: Request):
    payload = await request.json()
    updated = data_manager.update_property(
        property_id,
        address=require_text(payload, "address"),
        city=str(payload.get("city", "")).strip(),
        zip_code=str(payload.get("zip_code", "")).strip(),
        country=str(payload.get("country", "España")).strip() or "España",
        cadastral_ref=str(payload.get("cadastral_ref", "")).strip(),
        mortgage_monthly=parse_float(payload, "mortgage_monthly", default=0.0),
        utilities_included=bool(payload.get("utilities_included", False)),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Propiedad no encontrada.")
    return JSONResponse(get_app_state())


@app.post("/api/properties/{property_id}/tenants")
async def create_tenant(property_id: str, request: Request):
    payload = await request.json()
    tenant = data_manager.add_tenant(
        property_id,
        require_text(payload, "name"),
        parse_float(payload, "rent"),
        str(payload.get("start_date", "")).strip() or None,
        payload.get("payments"),
        parse_float(payload, "deposit_amount", default=0.0),
        bool(payload.get("deposit_paid", False)),
        str(payload.get("deposit_payment_date", "")).strip() or None,
    )
    if not tenant:
        raise HTTPException(status_code=404, detail="Propiedad no encontrada.")
    return JSONResponse(get_app_state(), status_code=201)


@app.put("/api/properties/{property_id}/tenants/{tenant_id}")
async def update_tenant(property_id: str, tenant_id: str, request: Request):
    payload = await request.json()
    updated = data_manager.update_tenant(
        property_id,
        tenant_id,
        name=require_text(payload, "name"),
        rent=parse_float(payload, "rent"),
        start_date=str(payload.get("start_date", "")).strip() or None,
        payments=payload.get("payments"),
        deposit_amount=parse_float(payload, "deposit_amount", default=0.0),
        deposit_paid=bool(payload.get("deposit_paid", False)),
        deposit_payment_date=str(payload.get("deposit_payment_date", "")).strip() or None,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Inquilino no encontrado.")
    return JSONResponse(get_app_state())


@app.post("/api/properties/{property_id}/tenants/{tenant_id}/mark-paid")
async def mark_tenant_paid(property_id: str, tenant_id: str):
    updated = data_manager.mark_tenant_paid(property_id, tenant_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Inquilino no encontrado.")
    return JSONResponse(get_app_state())


@app.delete("/api/properties/{property_id}/tenants/{tenant_id}")
async def delete_tenant(property_id: str, tenant_id: str):
    removed = data_manager.remove_tenant(property_id, tenant_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Inquilino no encontrado.")
    return JSONResponse(get_app_state())


@app.get("/api/properties/{property_id}/tenants/{tenant_id}/receipt")
async def generate_receipt(request: Request, property_id: str, tenant_id: str):
    prop = data_manager.get_property(property_id)
    tenant = data_manager.get_tenant(property_id, tenant_id)
    if not prop or not tenant:
        raise HTTPException(status_code=404, detail="No se ha encontrado la propiedad o el inquilino.")

    receipt = build_receipt_payload(prop, tenant)
    return templates.TemplateResponse(
        request,
        "receipt.html",
        {
            "request": request,
            "receipt": receipt,
        },
    )


@app.post("/api/expenses")
async def create_expense(request: Request):
    payload = await request.json()
    data_manager.add_expense(
        parse_float(payload, "amount"),
        require_text(payload, "category"),
        require_text(payload, "description"),
        str(payload.get("date", "")).strip() or None,
        str(payload.get("property_id", "")).strip() or None,
    )
    return JSONResponse(get_app_state(), status_code=201)


@app.put("/api/expenses/{expense_id}")
async def update_expense(expense_id: str, request: Request):
    payload = await request.json()
    updated = data_manager.update_expense(
        expense_id,
        amount=parse_float(payload, "amount"),
        category=require_text(payload, "category"),
        description=require_text(payload, "description"),
        date=str(payload.get("date", "")).strip() or None,
        property_id=str(payload.get("property_id", "")).strip() or None,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Gasto no encontrado.")
    return JSONResponse(get_app_state())


@app.delete("/api/expenses/{expense_id}")
async def delete_expense(expense_id: str):
    removed = data_manager.remove_expense(expense_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Gasto no encontrado.")
    return JSONResponse(get_app_state())


@app.post("/api/incomes")
async def create_income(request: Request):
    payload = await request.json()
    data_manager.add_income(
        parse_float(payload, "amount"),
        require_text(payload, "category"),
        require_text(payload, "description"),
        str(payload.get("date", "")).strip() or None,
        str(payload.get("property_id", "")).strip() or None,
    )
    return JSONResponse(get_app_state(), status_code=201)


@app.put("/api/incomes/{income_id}")
async def update_income(income_id: str, request: Request):
    if income_id.startswith("deposit-"):
        raise HTTPException(status_code=400, detail="Las fianzas se editan desde el inquilino.")

    payload = await request.json()
    updated = data_manager.update_income(
        income_id,
        amount=parse_float(payload, "amount"),
        category=require_text(payload, "category"),
        description=require_text(payload, "description"),
        date=str(payload.get("date", "")).strip() or None,
        property_id=str(payload.get("property_id", "")).strip() or None,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Ingreso no encontrado.")
    return JSONResponse(get_app_state())


@app.delete("/api/incomes/{income_id}")
async def delete_income(income_id: str):
    if income_id.startswith("deposit-"):
        raise HTTPException(status_code=400, detail="Las fianzas se eliminan desde el inquilino.")

    removed = data_manager.remove_income(income_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Ingreso no encontrado.")
    return JSONResponse(get_app_state())
