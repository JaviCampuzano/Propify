import os
from datetime import datetime
from unittest.mock import patch

import models
from data_manager import DataManager
from models import Tenant


TEST_FILE = "test_verify_logic.json"


class MockDate(datetime):
    @classmethod
    def now(cls):
        return cls._now


def run_verification():
    print("--- Starting Verification ---")

    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)

    dm = DataManager(TEST_FILE)
    dm.add_property("Calle Test 123")
    prop = dm.properties[0]

    prop.tenant = Tenant("Juan", 500)
    dm.save_data()
    print("[PASS] Tenant added.")

    current_month = datetime.now().strftime("%Y-%m")
    changed = dm.check_monthly_receipts()
    if changed and current_month in prop.tenant.payments:
        print(f"[PASS] Monthly payment generated for {current_month}.")
    else:
        print(f"[FAIL] Monthly payment NOT generated. Changed={changed}, Keys={list(prop.tenant.payments.keys())}")

    MockDate._now = datetime(2023, 10, 5)
    with patch.object(models, "datetime", MockDate):
        prop.tenant.payments["2023-10"] = "PENDING"
        status, color = prop.check_payment_status()
        if status == "Pendiente" and color == "orange":
            print(f"[PASS] Date=5th -> Status: {status} ({color})")
        else:
            print(f"[FAIL] Date=5th -> Status: {status} ({color})")

    MockDate._now = datetime(2023, 10, 12)
    with patch.object(models, "datetime", MockDate):
        status, color = prop.check_payment_status()
        if status == "Retraso" and color == "red":
            print(f"[PASS] Date=12th -> Status: {status} ({color})")
        else:
            print(f"[FAIL] Date=12th -> Status: {status} ({color})")

    MockDate._now = datetime(2023, 10, 15)
    with patch.object(models, "datetime", MockDate):
        prop.tenant.payments["2023-10"] = "PAID"
        status, color = prop.check_payment_status()
        if status == "Pagado" and color == "green":
            print(f"[PASS] Paid -> Status: {status} ({color})")
        else:
            print(f"[FAIL] Paid -> Status: {status} ({color})")

    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)
    print("--- Verification Complete ---")


if __name__ == "__main__":
    run_verification()
