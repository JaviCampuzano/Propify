import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from models import Expense, Income, Property, Tenant, User

class DataManager:
    def __init__(self, filepath="datos_v2.json"):
        self.filepath = filepath
        self.backup_dir = Path("backups")
        self.properties: List[Property] = []
        self.user: Optional[User] = None
        self.expenses: List[Expense] = []
        self.incomes: List[Income] = []

    def load_data(self):
        if not os.path.exists(self.filepath):
            # Check for V1 migration
            if os.path.exists("datos.json"):
                self.migrate_v1_data()
            return

        try:
            with open(self.filepath, "r") as f:
                data = json.load(f)
                
            # Users
            self.user = None
            if data.get("user"):
                u = data["user"]
                self.user = User(u["name"], u["client_code"], u["password"])
                
            # Properties & Tenants
            self.properties = []
            for p_data in data.get("properties", []):
                # Property.from_dict now handles "tenant" -> "tenants" migration
                prop = Property.from_dict(p_data)
                self.properties.append(prop)

            # Expenses
            self.expenses = []
            for e_data in data.get("expenses", []):
                self.expenses.append(Expense.from_dict(e_data))
            self.incomes = []
            for i_data in data.get("incomes", []):
                self.incomes.append(Income.from_dict(i_data))
                
            # Migration V1 -> V2 Check (If V1 data exists and V2 is empty properties)
            if not self.properties and os.path.exists("datos.json"):
                self.migrate_v1_data()

            self.check_monthly_receipts()

        except Exception as e:
            print(f"Error loading data: {e}") 
            # In a real app we might want to backup the corrupt file
            

    def migrate_v1_data(self):
        # Load V1
        try:
            with open("datos.json", "r") as f:
                old_data = json.load(f)
            # Create V2 structure
            # V1 was list of dicts (Properties)
            if old_data and isinstance(old_data, list):
                if isinstance(old_data[0], str): # Very old format
                     self.properties = [Property(a) for a in old_data]
                else: 
                     self.properties = [Property.from_dict(p) for p in old_data]
            
            self.save_data()
        except Exception as e:
            print(f"Migration error: {e}")

    def save_data(self):
        data = {
            "user": self.user.to_dict() if self.user else None,
            "properties": [p.to_dict() for p in self.properties],
            "expenses": [e.to_dict() for e in self.expenses],
            "incomes": [i.to_dict() for i in self.incomes]
        }
        self._create_backup()
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def _create_backup(self):
        if not os.path.exists(self.filepath):
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        source = Path(self.filepath)
        if source.stem.startswith("test_"):
            return

        self.backup_dir.mkdir(exist_ok=True)
        backup_path = self.backup_dir / f"{source.stem}_{timestamp}{source.suffix}"
        shutil.copy2(source, backup_path)

        backups = sorted(
            self.backup_dir.glob(f"{source.stem}_*{source.suffix}"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for old_backup in backups[10:]:
            old_backup.unlink(missing_ok=True)

    def check_monthly_receipts(self):
        current_month = datetime.now().strftime("%Y-%m")
        changed = False

        for prop in self.properties:
            # Check for each tenant
            for tenant in prop.tenants:
                if current_month not in tenant.payments:
                    tenant.payments[current_month] = "PENDING"
                    changed = True

        if changed:
            self.save_data()
        return changed

    def add_property(self, address):
        if not any(p.address == address for p in self.properties):
            self.properties.append(Property(address))
            self.save_data()
            return True
        return False

    def get_property(self, property_id: str) -> Optional[Property]:
        return next((prop for prop in self.properties if prop.id == property_id), None)

    def update_property(
        self,
        property_id: str,
        *,
        address: str,
        city: str = "",
        zip_code: str = "",
        country: str = "España",
        cadastral_ref: str = "",
        mortgage_monthly: float = 0.0,
        utilities_included: bool = False,
    ) -> bool:
        prop = self.get_property(property_id)
        if not prop:
            return False

        prop.address = address
        prop.city = city
        prop.zip_code = zip_code
        prop.country = country
        prop.cadastral_ref = cadastral_ref
        prop.mortgage_monthly = mortgage_monthly
        prop.utilities_included = utilities_included
        self.save_data()
        return True

    def add_tenant(
        self,
        property_id: str,
        name: str,
        rent: float,
        start_date: Optional[str] = None,
        payments: Optional[dict] = None,
        deposit_amount: float = 0.0,
        deposit_paid: bool = False,
        deposit_payment_date: Optional[str] = None,
    ) -> Optional[Tenant]:
        prop = self.get_property(property_id)
        if not prop:
            return None

        tenant = Tenant(name, rent, start_date)
        tenant.sync_payments(payments)
        tenant.deposit_amount = deposit_amount
        tenant.deposit_paid = deposit_paid
        tenant.deposit_payment_date = deposit_payment_date or ""
        prop.tenants.append(tenant)
        self.save_data()
        return tenant

    def get_tenant(self, property_id: str, tenant_id: str) -> Optional[Tenant]:
        prop = self.get_property(property_id)
        if not prop:
            return None
        return next((tenant for tenant in prop.tenants if tenant.id == tenant_id), None)

    def update_tenant(
        self,
        property_id: str,
        tenant_id: str,
        *,
        name: str,
        rent: float,
        start_date: Optional[str] = None,
        payments: Optional[dict] = None,
        deposit_amount: float = 0.0,
        deposit_paid: bool = False,
        deposit_payment_date: Optional[str] = None,
    ) -> bool:
        tenant = self.get_tenant(property_id, tenant_id)
        if not tenant:
            return False

        tenant.name = name
        tenant.rent = rent
        if start_date:
            tenant.start_date = start_date
        tenant.sync_payments(payments)
        tenant.deposit_amount = deposit_amount
        tenant.deposit_paid = deposit_paid
        tenant.deposit_payment_date = deposit_payment_date or ""
        self.save_data()
        return True

    def mark_tenant_paid(self, property_id: str, tenant_id: str, month: Optional[str] = None) -> bool:
        tenant = self.get_tenant(property_id, tenant_id)
        if not tenant:
            return False

        target_month = month or datetime.now().strftime("%Y-%m")
        tenant.payments[target_month] = "PAID"
        self.save_data()
        return True

    def remove_tenant(self, property_id: str, tenant_id: str) -> bool:
        prop = self.get_property(property_id)
        if not prop:
            return False

        original_count = len(prop.tenants)
        prop.tenants = [tenant for tenant in prop.tenants if tenant.id != tenant_id]
        if len(prop.tenants) == original_count:
            return False

        self.save_data()
        return True

    def add_expense(
        self,
        amount: float,
        category: str,
        description: str,
        date: Optional[str] = None,
        property_id: Optional[str] = None,
    ) -> Expense:
        expense = Expense(amount, category, description, date=date, property_id=property_id)
        self.expenses.append(expense)
        self.save_data()
        return expense

    def get_expense(self, expense_id: str) -> Optional[Expense]:
        return next((expense for expense in self.expenses if expense.id == expense_id), None)

    def update_expense(
        self,
        expense_id: str,
        *,
        amount: float,
        category: str,
        description: str,
        date: Optional[str] = None,
        property_id: Optional[str] = None,
    ) -> bool:
        expense = self.get_expense(expense_id)
        if not expense:
            return False

        expense.amount = amount
        expense.category = category
        expense.description = description
        expense.date = date or expense.date
        expense.property_id = property_id
        self.save_data()
        return True

    def remove_expense(self, expense_id: str) -> bool:
        original_count = len(self.expenses)
        self.expenses = [expense for expense in self.expenses if expense.id != expense_id]
        if len(self.expenses) == original_count:
            return False
        self.save_data()
        return True

    def add_income(
        self,
        amount: float,
        category: str,
        description: str,
        date: Optional[str] = None,
        property_id: Optional[str] = None,
    ) -> Income:
        income = Income(amount, category, description, date=date, property_id=property_id)
        self.incomes.append(income)
        self.save_data()
        return income

    def get_income(self, income_id: str) -> Optional[Income]:
        return next((income for income in self.incomes if income.id == income_id), None)

    def update_income(
        self,
        income_id: str,
        *,
        amount: float,
        category: str,
        description: str,
        date: Optional[str] = None,
        property_id: Optional[str] = None,
    ) -> bool:
        income = self.get_income(income_id)
        if not income:
            return False

        income.amount = amount
        income.category = category
        income.description = description
        income.date = date or income.date
        income.property_id = property_id
        self.save_data()
        return True

    def remove_income(self, income_id: str) -> bool:
        original_count = len(self.incomes)
        self.incomes = [income for income in self.incomes if income.id != income_id]
        if len(self.incomes) == original_count:
            return False
        self.save_data()
        return True

    def get_all_incomes(self) -> List[Income]:
        combined = list(self.incomes)
        for prop in self.properties:
            for tenant in prop.tenants:
                if tenant.deposit_paid and tenant.deposit_amount > 0 and tenant.deposit_payment_date:
                    deposit_income = Income(
                        tenant.deposit_amount,
                        "DEPOSIT",
                        f"Fianza de {tenant.name}",
                        date=tenant.deposit_payment_date,
                        property_id=prop.id,
                    )
                    deposit_income.id = f"deposit-{tenant.id}"
                    combined.append(deposit_income)
        return combined

    def _month_sequence(self, months_back: int = 6):
        current = datetime.now()
        year = current.year
        month = current.month
        months = []

        for offset in range(months_back - 1, -1, -1):
            target_month = month - offset
            target_year = year
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            months.append(f"{target_year:04d}-{target_month:02d}")

        return months

    def get_dashboard_metrics(self):
        current_month = datetime.now().strftime("%Y-%m")
        all_incomes = self.get_all_incomes()
        current_month_paid_rent = 0.0
        for prop in self.properties:
            for tenant in prop.tenants:
                if tenant.payments.get(current_month) == "PAID":
                    current_month_paid_rent += tenant.rent

        extra_income_current = sum(
            income.amount
            for income in all_incomes
            if income.category != "DEPOSIT" and income.date and income.date.startswith(current_month)
        )
        total_income = current_month_paid_rent + extra_income_current
        mortgage_total = sum(prop.mortgage_monthly for prop in self.properties)
        current_expenses = sum(
            expense.amount
            for expense in self.expenses
            if expense.category != "MORTGAGE" and expense.date and expense.date.startswith(current_month)
        )
        estimated_profit = total_income - mortgage_total - current_expenses

        occupied_properties = sum(1 for prop in self.properties if prop.tenants)
        pending_tenants = 0
        paid_tenants = 0
        late_tenants = 0

        for prop in self.properties:
            for tenant in prop.tenants:
                status, _ = tenant.get_current_status()
                if status == "Pagado":
                    paid_tenants += 1
                elif status == "Retraso":
                    late_tenants += 1
                else:
                    pending_tenants += 1

        recent_expenses = sorted(self.expenses, key=lambda expense: expense.date or "", reverse=True)[:8]
        recent_incomes = sorted(all_incomes, key=lambda income: income.date or "", reverse=True)[:8]
        trend_months = self._month_sequence(6)
        trend_data = []
        expense_categories = {}
        income_categories = {}

        for month_key in trend_months:
            month_expected_rent = 0.0
            month_paid_income = 0.0
            month_mortgages = 0.0

            for prop in self.properties:
                has_active_tenant = False
                for tenant in prop.tenants:
                    if month_key in tenant.payments:
                        has_active_tenant = True
                        month_expected_rent += tenant.rent
                        if tenant.payments.get(month_key) == "PAID":
                            month_paid_income += tenant.rent
                if has_active_tenant:
                    month_mortgages += prop.mortgage_monthly

            month_expenses = 0.0
            month_extra_income = 0.0
            for expense in self.expenses:
                if expense.category != "MORTGAGE" and expense.date and expense.date.startswith(month_key):
                    month_expenses += expense.amount
                    expense_categories[expense.category] = expense_categories.get(expense.category, 0.0) + expense.amount
            for income in all_incomes:
                if income.category != "DEPOSIT" and income.date and income.date.startswith(month_key):
                    month_extra_income += income.amount
                    income_categories[income.category] = income_categories.get(income.category, 0.0) + income.amount

            month_expected_income = month_expected_rent + month_extra_income
            month_paid_income += month_extra_income

            trend_data.append(
                {
                    "month": month_key,
                    "expected_income": month_expected_income,
                    "paid_income": month_paid_income,
                    "expenses": month_expenses,
                    "profit": month_paid_income - month_mortgages - month_expenses,
                    "collection_rate": round((month_paid_income / month_expected_income) * 100, 1) if month_expected_income else 0.0,
                }
            )

        previous_month_profit = trend_data[-2]["profit"] if len(trend_data) > 1 else 0.0
        profit_delta = estimated_profit - previous_month_profit
        collection_rate_current = trend_data[-1]["collection_rate"] if trend_data else 0.0
        paid_income_current = trend_data[-1]["paid_income"] if trend_data else 0.0
        accumulated_profit = sum(item["profit"] for item in trend_data)

        expense_breakdown = [
            {"category": category, "amount": amount}
            for category, amount in sorted(expense_categories.items(), key=lambda item: item[1], reverse=True)
        ]
        income_breakdown = [
            {"category": category, "amount": amount}
            for category, amount in sorted(income_categories.items(), key=lambda item: item[1], reverse=True)
        ]

        return {
            "current_month": current_month,
            "total_income": total_income,
            "rent_income_current": current_month_paid_rent,
            "extra_income_current": extra_income_current,
            "mortgage_total": mortgage_total,
            "current_expenses": current_expenses,
            "estimated_profit": estimated_profit,
            "property_count": len(self.properties),
            "occupied_properties": occupied_properties,
            "pending_tenants": pending_tenants,
            "paid_tenants": paid_tenants,
            "late_tenants": late_tenants,
            "recent_expenses": recent_expenses,
            "recent_incomes": recent_incomes,
            "paid_income_current": paid_income_current,
            "collection_rate_current": collection_rate_current,
            "profit_delta": profit_delta,
            "accumulated_profit": accumulated_profit,
            "trend_data": trend_data,
            "expense_breakdown": expense_breakdown,
            "income_breakdown": income_breakdown,
        }

    def set_user(self, name, code, password):
        self.user = User(name, code, password)
        self.save_data()
