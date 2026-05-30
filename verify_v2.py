import shutil
import os
from datetime import datetime
from models import Property, Tenant, Expense
from data_manager import DataManager

TEST_FILE = "test_verify_v2.json"

def verify_v2():
    print("--- Starting V2 Verification ---")
    
    # Setup clean environment
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)

    # 1. Models & Persistence
    dm = DataManager(TEST_FILE)
    dm.add_property("Avenida Libertad 10")
    dm.set_user("Admin", "123456", "pass")
    
    prop = dm.properties[0]
    prop.mortgage_monthly = 500.0
    prop.tenant = Tenant("Inquilino V2", 1000.0)
    
    dm.save_data()
    print("[PASS] Helper data created and saved.")

    # 2. Verify Profit Calculation
    # Profit = Rent (1000) - Mortgage (500) = 500
    profit = prop.calculate_profit([])
    if profit == 500.0:
        print("[PASS] Basic Profit Calc: 1000 - 500 = 500")
    else:
        print(f"[FAIL] Basic Profit Calc: Expected 500, got {profit}")

    # 3. Verify Expense Deduction
    # Add an expense for this property for current month
    exp = Expense(100.0, "REPAIR", "Reparación Grifo", property_id=prop.id)
    dm.expenses.append(exp)
    
    profit_after_expense = prop.calculate_profit(dm.expenses)
    # Profit = 500 - 100 = 400
    if profit_after_expense == 400.0:
         print("[PASS] Profit with Expense: 500 - 100 = 400")
    else:
         print(f"[FAIL] Profit with Expense: Expected 400, got {profit_after_expense}")

    income = dm.add_income(250.0, "BONUS", "Ingreso extraordinario", property_id=prop.id)
    profit_after_income = prop.calculate_profit(dm.expenses, dm.incomes)
    if income and profit_after_income == 650.0:
         print("[PASS] Profit with Income: 400 + 250 = 650")
    else:
         print(f"[FAIL] Profit with Income: Expected 650, got {profit_after_income}")

    expense_updated = dm.update_expense(exp.id, amount=120.0, category="REPAIR", description="Reparación Grifo", date=exp.date, property_id=prop.id)
    income_updated = dm.update_income(income.id, amount=275.0, category="BONUS", description="Ingreso actualizado", date=income.date, property_id=prop.id)
    if expense_updated and income_updated and dm.get_expense(exp.id).amount == 120.0 and dm.get_income(income.id).amount == 275.0:
        print("[PASS] Expense and income update valid.")
    else:
        print("[FAIL] Expense and income update failed.")

    retro_tenant = dm.add_tenant(
        prop.id,
        "Retroactivo",
        900.0,
        start_date="2026-02-10",
        payments={"2026-02": "PAID", "2026-03": "PAID"},
        deposit_amount=1800.0,
        deposit_paid=True,
        deposit_payment_date="2026-02-10",
    )
    expected_months = ["2026-02", "2026-03", "2026-04", "2026-05"]
    if retro_tenant and list(retro_tenant.payments.keys()) == expected_months and retro_tenant.payments["2026-04"] == "PENDING":
        print("[PASS] Retroactive monthly schedule generated correctly.")
    else:
        print(f"[FAIL] Retroactive schedule incorrect: {retro_tenant.payments if retro_tenant else 'tenant not created'}")

    deposit_income = [income for income in dm.get_all_incomes() if income.category == "DEPOSIT"]
    if deposit_income and deposit_income[0].amount == 1800.0:
        print("[PASS] Tenant deposit registered as income correctly.")
    else:
        print("[FAIL] Tenant deposit was not exposed as income correctly.")

    # 4. Verify File Path persistence
    prop.electricity_contract_path = "/tmp/test.pdf"
    dm.save_data()
    
    dm2 = DataManager(TEST_FILE)
    dm2.load_data()
    if dm2.properties[0].electricity_contract_path == "/tmp/test.pdf":
        print("[PASS] File path persistence valid.")
    else:
        print("[FAIL] File path persistence failed.")

    if dm2.incomes and dm2.incomes[0].description == "Ingreso actualizado":
        print("[PASS] Income persistence valid.")
    else:
        print("[FAIL] Income persistence failed.")

    if dm2.properties[0].tenants[1].deposit_paid and dm2.properties[0].tenants[1].deposit_amount == 1800.0:
        print("[PASS] Deposit persistence valid.")
    else:
        print("[FAIL] Deposit persistence failed.")

    removed_expense = dm2.remove_expense(exp.id)
    removed_income = dm2.remove_income(income.id)
    if removed_expense and removed_income and dm2.get_expense(exp.id) is None and dm2.get_income(income.id) is None:
        print("[PASS] Expense and income deletion valid.")
    else:
        print("[FAIL] Expense and income deletion failed.")

    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)

    print("--- V2 Verification Complete ---")

if __name__ == "__main__":
    verify_v2()
