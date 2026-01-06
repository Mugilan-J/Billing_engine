#!/usr/bin/env python3
import psycopg2
import bcrypt
import uuid
import sys
import re
from datetime import datetime

# DB CONFIGURATION
DB_URL = "postgres://postgres:mugi%402005@localhost:5432/billing_engine"

def connect():
    try:
        return psycopg2.connect(DB_URL)
    except psycopg2.OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

# --- UTILS ---

def check_password_strength(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    return True, ""

def get_input_hidden(prompt):
    import getpass
    return getpass.getpass(prompt)

# --- CORE AUTH ---

def validate_login(email, password):
    db = connect()
    cur = db.cursor()
    cur.execute("SELECT id, password_hash FROM users WHERE email=%s", (email,))
    row = cur.fetchone()
    db.close()
    
    if not row:
        return None
    
    user_id, stored_hash = row
    if bcrypt.checkpw(password.encode(), stored_hash.encode()):
        return user_id
    return None

def create_user(email, password, tier_name):
    db = connect()
    cur = db.cursor()

    # Check existence
    cur.execute("SELECT id FROM users WHERE email=%s", (email,))
    if cur.fetchone():
        print("❌ User already exists.")
        db.close()
        return None

    # Get Tier ID
    cur.execute("SELECT id FROM tiers WHERE name = %s", (tier_name,))
    row = cur.fetchone()
    if not row:
        print(f"❌ Tier '{tier_name}' not found.")
        db.close()
        return None
    tier_id = row[0]

    try:
        user_id = str(uuid.uuid4())
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        # Insert User
        cur.execute("INSERT INTO users(id, email, password_hash, created_at) VALUES (%s, %s, %s, %s)", 
                    (user_id, email, hashed, datetime.now()))
        
        # Link Tier
        cur.execute("INSERT INTO user_tiers(user_id, tier_id, created_at) VALUES (%s, %s, %s)", 
                    (user_id, tier_id, datetime.now()))

        # Create Default API Key
        key_value = str(uuid.uuid4())
        cur.execute("INSERT INTO api_keys(id, user_id, key_value, status, created_at) VALUES (%s, %s, %s, 'active', %s)",
                    (str(uuid.uuid4()), user_id, key_value, datetime.now()))

        db.commit()
        return user_id, key_value
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        return None
    finally:
        db.close()

# --- DASHBOARD FEATURES ---

def change_password(user_id):
    print("\n🔐 --- Change Password ---")
    new_pass = get_input_hidden("Enter New Password: ")
    valid, msg = check_password_strength(new_pass)
    if not valid:
        print(f"⚠️ {msg}")
        return

    confirm = get_input_hidden("Confirm Password: ")
    if new_pass != confirm:
        print("❌ Passwords do not match.")
        return

    hashed = bcrypt.hashpw(new_pass.encode(), bcrypt.gensalt()).decode()
    
    db = connect()
    cur = db.cursor()
    cur.execute("UPDATE users SET password_hash=%s WHERE id=%s", (hashed, user_id))
    db.commit()
    db.close()
    print("✅ Password updated successfully.")

def delete_account(user_id):
    print("\n💀 --- Delete Account ---")
    print("⚠️  WARNING: This will delete your account, all API keys, and history.")
    confirm = input("Type 'DELETE' to confirm: ").strip()
    
    if confirm != "DELETE":
        print("❌ Action cancelled.")
        return False

    db = connect()
    cur = db.cursor()
    try:
        # Cascade delete should handle children, but let's be safe
        cur.execute("DELETE FROM api_keys WHERE user_id=%s", (user_id,))
        cur.execute("DELETE FROM user_tiers WHERE user_id=%s", (user_id,))
        cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
        db.commit()
        print("✅ Account deleted. Goodbye.")
        return True # Indicates session should end
    except Exception as e:
        db.rollback()
        print(f"❌ Delete failed: {e}")
        return False
    finally:
        db.close()

# --- API KEY MANAGEMENT ---

def list_api_keys(user_id):
    db = connect()
    cur = db.cursor()
    cur.execute("SELECT key_value, status, created_at FROM api_keys WHERE user_id=%s ORDER BY created_at DESC", (user_id,))
    rows = cur.fetchall()
    db.close()

    print(f"\n🔑 --- Your API Keys ({len(rows)}) ---")
    print(f"{'KEY VALUE':<40} | {'STATUS':<10} | {'CREATED'}")
    print("-" * 75)
    for row in rows:
        key, status, created = row
        created_str = created.strftime("%Y-%m-%d") if created else "N/A"
        print(f"{key:<40} | {status:<10} | {created_str}")
    print("-" * 75)

def create_new_key(user_id):
    db = connect()
    cur = db.cursor()
    new_key = str(uuid.uuid4())
    try:
        cur.execute("INSERT INTO api_keys(id, user_id, key_value, status, created_at) VALUES (%s, %s, %s, 'active', %s)",
                    (str(uuid.uuid4()), user_id, new_key, datetime.now()))
        db.commit()
        print(f"\n✅ New Key Created: {new_key}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

def revoke_key(user_id):
    key_to_revoke = input("Enter the API Key to revoke: ").strip()
    db = connect()
    cur = db.cursor()
    
    # Check ownership
    cur.execute("SELECT id FROM api_keys WHERE key_value=%s AND user_id=%s", (key_to_revoke, user_id))
    if not cur.fetchone():
        print("❌ Invalid key or you do not own this key.")
        db.close()
        return

    cur.execute("UPDATE api_keys SET status='revoked' WHERE key_value=%s", (key_to_revoke,))
    db.commit()
    db.close()
    print(f"🚫 Key {key_to_revoke[:8]}... revoked.")

# --- MENUS ---

def dashboard_menu(user_id):
    while True:
        print("\n📊 --- Developer Dashboard ---")
        print("1. List API Keys")
        print("2. Create New API Key")
        print("3. Revoke API Key")
        print("4. Change Password")
        print("5. Delete Account")
        print("6. Logout")
        
        choice = input("Select option: ").strip()

        if choice == '1':
            list_api_keys(user_id)
        elif choice == '2':
            create_new_key(user_id)
        elif choice == '3':
            revoke_key(user_id)
        elif choice == '4':
            change_password(user_id)
        elif choice == '5':
            deleted = delete_account(user_id)
            if deleted:
                break
        elif choice == '6':
            print("👋 Logging out...")
            break
        else:
            print("Invalid option.")

def main_menu():
    print("\n🚀 Billing Engine CLI")
    while True:
        print("1. Login")
        print("2. Signup")
        print("3. Exit")
        choice = input("Select: ").strip()

        if choice == '1':
            email = input("Email: ").strip()
            password = get_input_hidden("Password: ")
            user_id = validate_login(email, password)
            if user_id:
                print("\n✅ Login Successful!")
                dashboard_menu(user_id)
            else:
                print("❌ Invalid credentials.")

        elif choice == '2':
            email = input("Email: ").strip()
            password = get_input_hidden("Password: ")
            
            # Tier
            print("Select Tier: [1] Free [2] Pay-As-You-Go")
            t = input("Choice: ").strip()
            tier = "payg" if t == '2' else "free"
            
            res = create_user(email, password, tier)
            if res:
                uid, key = res
                print(f"\n✅ Signup Complete! API Key: {key}")
                dashboard_menu(uid)

        elif choice == '3':
            sys.exit(0)

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nExiting...")



# import bcrypt

# password="Ram@0117"
# stored_hash=b"$2b$12$5/Hlv5n/H8s1Yo35FG1BSOeRt9eSPlJmiJ5BHAExE86WWzuMD6YUa"

# if bcrypt.checkpw(password.encode(), stored_hash):
#         print("matched")
# else:
#         print("not matched")