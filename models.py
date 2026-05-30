import uuid
from datetime import datetime
from typing import List, Dict, Optional

class User:
    def __init__(self, name: str, client_code: str, password: str):
        self.name = name
        self.client_code = client_code
        self.password = password  # In a real app, hash this!

    def to_dict(self):
        return {"name": self.name, "client_code": self.client_code, "password": self.password}

    @classmethod
    def from_dict(cls, data):
        if not data: return None
        return cls(data.get("name"), data.get("client_code"), data.get("password"))

class Expense:
    def __init__(self, amount: float, category: str, description: str, date: str = None, property_id: str = None):
        self.id = str(uuid.uuid4())
        self.amount = amount
        self.category = category # "MORTGAGE", "UTILITY", "REPAIR", "OTHER"
        self.description = description
        self.date = date or datetime.now().strftime("%Y-%m-%d")
        self.property_id = property_id

    def to_dict(self):
        return {
            "id": self.id,
            "amount": self.amount,
            "category": self.category,
            "description": self.description,
            "date": self.date,
            "property_id": self.property_id
        }

    @classmethod
    def from_dict(cls, data):
        e = cls(data["amount"], data["category"], data["description"], data.get("date"), data.get("property_id"))
        e.id = data.get("id", str(uuid.uuid4()))
        return e

class Income:
    def __init__(self, amount: float, category: str, description: str, date: str = None, property_id: str = None):
        self.id = str(uuid.uuid4())
        self.amount = amount
        self.category = category
        self.description = description
        self.date = date or datetime.now().strftime("%Y-%m-%d")
        self.property_id = property_id

    def to_dict(self):
        return {
            "id": self.id,
            "amount": self.amount,
            "category": self.category,
            "description": self.description,
            "date": self.date,
            "property_id": self.property_id
        }

    @classmethod
    def from_dict(cls, data):
        income = cls(data["amount"], data["category"], data["description"], data.get("date"), data.get("property_id"))
        income.id = data.get("id", str(uuid.uuid4()))
        return income

class Tenant:
    def __init__(self, name: str, rent: float, start_date: str = None):
        self.id = str(uuid.uuid4())
        self.name = name
        self.rent = rent
        self.start_date = start_date or datetime.now().strftime("%Y-%m-%d")
        self.payments: Dict[str, str] = {}
        self.deposit_amount = 0.0
        self.deposit_paid = False
        self.deposit_payment_date = ""
        self.lease_contract_path = ""
        self.deposit_contract_path = ""

    def get_active_month_keys(self):
        start = datetime.strptime(self.start_date, "%Y-%m-%d")
        cursor_year = start.year
        cursor_month = start.month
        current = datetime.now()
        month_keys = []

        while (cursor_year, cursor_month) <= (current.year, current.month):
            month_keys.append(f"{cursor_year:04d}-{cursor_month:02d}")
            cursor_month += 1
            if cursor_month > 12:
                cursor_month = 1
                cursor_year += 1

        return month_keys

    def sync_payments(self, payment_overrides: Optional[Dict[str, str]] = None):
        source = payment_overrides or self.payments
        normalized = {}

        for month_key in self.get_active_month_keys():
            status = source.get(month_key, self.payments.get(month_key, "PENDING"))
            normalized[month_key] = "PAID" if status == "PAID" else "PENDING"

        self.payments = normalized
        return self.payments

    def ensure_current_month_payment(self):
        before = dict(self.payments)
        self.sync_payments()
        return before != self.payments

    def get_current_status(self):
        current_month = datetime.now().strftime("%Y-%m")
        status = self.payments.get(current_month, "PENDING")
        day_of_month = datetime.now().day
        
        if status == "PAID":
            return "Pagado", "#2ecc71" # Emerald Green
        elif status == "PENDING":
            if day_of_month <= 10:
                return "Pendiente", "#f1c40f" # Sunflower Yellow
            else:
                return "Retraso", "#e74c3c" # Alizarin Red
        return "Desconocido", "gray"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "rent": self.rent,
            "start_date": self.start_date,
            "payments": self.payments,
            "deposit_amount": self.deposit_amount,
            "deposit_paid": self.deposit_paid,
            "deposit_payment_date": self.deposit_payment_date,
            "lease_contract_path": self.lease_contract_path,
            "deposit_contract_path": self.deposit_contract_path
        }

    @classmethod
    def from_dict(cls, data):
        if not data: return None
        t = cls(data["name"], data["rent"], data.get("start_date"))
        t.id = data.get("id", str(uuid.uuid4()))
        t.payments = data.get("payments", {})
        t.deposit_amount = float(data.get("deposit_amount", 0.0) or 0.0)
        t.deposit_paid = bool(data.get("deposit_paid", False))
        t.deposit_payment_date = data.get("deposit_payment_date", "")
        t.lease_contract_path = data.get("lease_contract_path", "")
        t.deposit_contract_path = data.get("deposit_contract_path", "")
        t.sync_payments()
        return t

class Property:
    def __init__(self, address: str):
        self.id = str(uuid.uuid4())
        self.address = address
        # Details
        self.country = "España"
        self.city = ""
        self.zip_code = ""
        self.cadastral_ref = ""
        
        # Financials
        self.mortgage_monthly = 0.0
        self.mortgage_contract_path = ""
        self.utilities_included = False
        
        # Files
        self.electricity_contract_path = ""
        self.water_contract_path = ""
        
        # Multi-tenant support
        self.tenants: List[Tenant] = []

    @property
    def tenant(self):
        """Backward-compatible accessor for legacy single-tenant code."""
        return self.tenants[0] if self.tenants else None

    @tenant.setter
    def tenant(self, value):
        """Map legacy single-tenant assignments onto the current tenants list."""
        self.tenants = [value] if value else []

    def check_payment_status(self):
        if not self.tenants:
            return "Vacío", "gray"
        
        # Logic: If ANY tenant is PENDING/LATE, return that status. 
        # Only "Pagado" if ALL are paid.
        statuses = [t.get_current_status()[0] for t in self.tenants]
        
        if "Retraso" in statuses:
            return "Retraso", "red"
        elif "Pendiente" in statuses:
            return "Pendiente", "orange"
        elif "Pagado" in statuses:
            return "Pagado", "green" 
            
        return "Vacío", "gray"

    def calculate_profit(self, expenses: List['Expense'], incomes: Optional[List['Income']] = None):
        total_rent = sum(t.rent for t in self.tenants)
        total_extra_income = 0.0
        profit = total_rent - self.mortgage_monthly
        
        # Deduct global property expenses linked to this property
        current_month = datetime.now().strftime("%Y-%m")
        prop_expenses = sum(
            e.amount
            for e in expenses
            if e.property_id == self.id
            and e.category != "MORTGAGE"
            and e.date
            and e.date.startswith(current_month)
        )
        profit -= prop_expenses

        if incomes:
            total_extra_income = sum(
                income.amount
                for income in incomes
                if income.property_id == self.id
                and income.category != "DEPOSIT"
                and income.date
                and income.date.startswith(current_month)
            )
            profit += total_extra_income

        if self.utilities_included and total_rent > 0:
            profit -= 100 # Estimated utility cost
            
        return profit

    def to_dict(self):
        return {
            "id": self.id,
            "address": self.address,
            "country": self.country,
            "city": self.city,
            "zip_code": self.zip_code,
            "cadastral_ref": self.cadastral_ref,
            "utilities_included": self.utilities_included,
            "tenants": [t.to_dict() for t in self.tenants],
            "mortgage_monthly": self.mortgage_monthly,
            "mortgage_contract_path": self.mortgage_contract_path,
            "electricity_contract_path": self.electricity_contract_path,
            "water_contract_path": self.water_contract_path
        }

    @classmethod
    def from_dict(cls, data):
        p = cls(data["address"])
        p.id = data.get("id", str(uuid.uuid4()))
        p.country = data.get("country") or "España"
        p.city = data.get("city", "")
        p.zip_code = data.get("zip_code", "")
        p.cadastral_ref = data.get("cadastral_ref", "")
        p.mortgage_monthly = data.get("mortgage_monthly", 0.0)
        p.mortgage_contract_path = data.get("mortgage_contract_path", "")
        p.utilities_included = data.get("utilities_included", False)
        p.electricity_contract_path = data.get("electricity_contract_path", "")
        p.water_contract_path = data.get("water_contract_path", "")
        
        # Handle migration: tenant -> tenants
        if "tenants" in data:
            p.tenants = [Tenant.from_dict(t) for t in data["tenants"]]
        elif data.get("tenant"): # Migration V1/V2 early
            t = Tenant.from_dict(data["tenant"])
            if t: p.tenants.append(t)
            
        return p
