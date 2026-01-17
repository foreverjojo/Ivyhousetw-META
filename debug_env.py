import os
from pathlib import Path
from dotenv import load_dotenv

# 1. 嘗試載入 ifp.env
env_path = Path("ifp.env")
print(f"Checking {env_path.absolute()}...")
if env_path.exists():
    print("✅ ifp.env exists.")
    load_dotenv(env_path, override=True)
else:
    print("❌ ifp.env NOT found.")

# 2. 檢查變數
print("\n--- Environment Variables Check ---")
vars_to_check = [
    "OPENROUTER_MODEL_CONSULTANT_B",  # 舊名
    "MODEL_CONSULTANT_B",  # 新名 (程式碼現在讀這個)
    "MODEL_INSIGHTS",
    "GCP_PROJECT_ID",
]

for var in vars_to_check:
    value = os.getenv(var)
    print(f"{var}: {value if value else '❌ Not Set'}")

print("\n-----------------------------------")
