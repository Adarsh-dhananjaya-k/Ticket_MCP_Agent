import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

# ---------------- CONFIG ----------------
INSTANCE = os.getenv("SNOW_INSTANCE")
if INSTANCE:
    INSTANCE = INSTANCE.replace("https://", "").replace("http://", "").strip("/")

USER = os.getenv("SNOW_USER")
PWD = os.getenv("SNOW_PASSWORD")

BASE_URL = f"https://{INSTANCE}/api/now/table/sys_user"

# ---------------- USER LIST ----------------
users = [
    ("Alice", "alice@demo.com"),
    ("Bob", "bob@demo.com"),
    ("Charlie", "charlie@demo.com"),
    ("David", "david@demo.com"),
    ("Eve", "eve@demo.com"),
    ("Frank", "frank@demo.com"),
    ("Grace", "grace@demo.com"),
    ("Henry", "henry@demo.com"),
    ("Irene", "irene@demo.com"),
    ("Jack", "jack@demo.com"),
    ("Karen", "karen@demo.com"),
    ("Leo", "leo@demo.com"),
    ("Mia", "mia@demo.com"),
    ("Nathan", "nathan@demo.com"),
    ("Olivia", "olivia@demo.com"),
    ("Paul", "paul@demo.com"),
    ("Quinn", "quinn@demo.com"),
    ("Rachel", "rachel@demo.com"),
    ("Sam", "sam@demo.com"),
    ("Tina", "tina@demo.com"),
    ("Uma", "uma@demo.com"),
    ("Victor", "victor@demo.com"),
    ("Wendy", "wendy@demo.com"),
    ("Xander", "xander@demo.com"),
    ("Yara", "yara@demo.com"),
    ("Zoe", "zoe@demo.com"),
    ("Jhon", "jhon@demo.com"),
]

# ---------------- FUNCTIONS ----------------

def user_exists(email):
    params = {
        "sysparm_query": f"email={email}",
        "sysparm_fields": "sys_id",
        "sysparm_limit": 1
    }
    response = requests.get(BASE_URL, auth=HTTPBasicAuth(USER, PWD), params=params)
    result = response.json().get("result", [])
    return len(result) > 0


def create_user(name, email):
    payload = {
        "name": name,
        "user_name": email.split("@")[0],  # simple username
        "email": email,
        "active": True
    }

    response = requests.post(BASE_URL, auth=HTTPBasicAuth(USER, PWD), json=payload)

    if response.status_code == 201:
        print(f"✅ Created: {name} ({email})")
    else:
        print(f"❌ Failed: {name} ({email}) → {response.text}")


# ---------------- MAIN ----------------

def main():
    print("🚀 Starting bulk user creation...\n")

    for name, email in users:
        try:
            if user_exists(email):
                print(f"⚠️ Already exists: {email}")
            else:
                create_user(name, email)
        except Exception as e:
            print(f"❌ Error creating {email}: {e}")

    print("\n🎉 Done.")

if __name__ == "__main__":
    main()