import os

print("APP_ENV =", os.getenv("APP_ENV"))
print("OPENROUTER_API_KEY exists =", bool(os.getenv("OPENROUTER_API_KEY")))