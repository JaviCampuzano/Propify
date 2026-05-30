import os

from data_manager import DataManager


TEST_FILE = "test_migration_v2.json"


def verify_migration():
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)

    dm = DataManager(TEST_FILE)
    dm.load_data()

    if dm.properties:
        print(f"[PASS] Migration loaded {len(dm.properties)} properties from legacy data.")
    else:
        print("[FAIL] Migration did not load any property.")

    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)


if __name__ == "__main__":
    verify_migration()
