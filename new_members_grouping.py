import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
import json
import random


st.set_page_config(page_title="Assign Families", layout="centered")
st.title("Assign new members to Families")


# === AUTHENTICATION ===
USERNAME = "admin"
PASSWORD = "cccakoka2025"

with st.form("login_form"):
    st.subheader("Login to Assign Families")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_button = st.form_submit_button("Login")

if not login_button or username != USERNAME or password != PASSWORD:
    st.stop()

st.success("✅ Logged in successfully!")

st.markdown("""
###  Welcome to the Family Grouping Page

This tool helps us *assign new youth members* to one of our existing family groups.

 *How it works*:
- We take the list of pending members who have registered.
- Based on their *gender, **age range*, and current family sizes,
- They are *evenly distributed* into existing families.

🧾 Once assigned, new members are automatically moved to the *Master Sheet* and tagged with a timestamp so we can always tell who was recently added.

Ready to create new connections? Hit the button below to get started!
""")



creds_dict = dict(st.secrets["google_service_account"])

# Save credentials as a dict
# creds_json = json.loads(json.dumps(creds_dict))

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)


# # === Google Sheets Setup ===
# scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["google_service_account"], scope)
# client = gspread.authorize(creds)


# Open Google Sheet
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1uM4EbZIGlAyhefZwHG39XdsGt_OXiwP8fc0vB8vKwxU/edit?gid=0#gid=0")
worksheet = sheet.sheet1


SHEET_NAME = "Youth Family Assignment"
MASTER_SHEET = "Master"
PENDING_SHEET = "Pending"

try:
    sheet = client.open(SHEET_NAME)
except gspread.SpreadsheetNotFound:
    st.error("❌ Could not find sheet.")
    st.stop()

master_ws = sheet.worksheet(MASTER_SHEET)
pending_ws = sheet.worksheet(PENDING_SHEET)

# === LOAD DATA ===
master_df = pd.DataFrame(master_ws.get_all_records())
pending_df = pd.DataFrame(pending_ws.get_all_records())

# Ensure consistent column names
master_df.rename(columns=lambda x: x.strip().upper(), inplace=True)
pending_df.rename(columns=lambda x: x.strip().upper(), inplace=True)

# Standardize phone numbers
master_df["PHONE"] = master_df["PHONE"].astype(str).apply(lambda x: "0" + x[-10:] if x.isdigit() and len(x) >= 10 else x)
pending_df["PHONE"] = pending_df["PHONE"].astype(str).apply(lambda x: "0" + x[-10:] if x.isdigit() and len(x) >= 10 else x)

# === EXIT IF NO PENDING USERS ===
if pending_df.empty:
    st.info("✅ No pending registrations to assign.")
    st.stop()

# === EXISTING FAMILIES ===
existing_families = master_df["FAMILY"].unique().tolist()

# === FAMILY LOAD ===
family_counts = master_df["FAMILY"].value_counts().to_dict()
for fam in existing_families:
    family_counts.setdefault(fam, 0)

# === SHUFFLE PENDING FOR VARIETY ===
pending_df = pending_df.sample(frac=1, random_state=random.randint(1, 10000)).reset_index(drop=True)

# === ASSIGNMENT LOGIC ===
new_entries = []

for _, row in pending_df.iterrows():
    gender = row["GENDER"].upper()
    age = row["AGE_RANGE"]

    # Find families with lowest count
    least_loaded = sorted(family_counts.items(), key=lambda x: x[1])[0][0]

    new_entries.append({
        "NAME": row["NAME"],
        "GENDER": gender,
        "AGE_RANGE": age,
        "PHONE": f'0{str(row["PHONE"])[-10:]}' if str(row["PHONE"]).isdigit() else row["PHONE"],
        "FAMILY": least_loaded,
        "TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    # Update count
    family_counts[least_loaded] += 1

# === WRITE TO MASTER SHEET ===
for entry in new_entries:
    master_ws.append_row(list(entry.values()))

# === CLEAR PENDING SHEET ===
pending_ws.clear()
pending_ws.append_row(["NAME", "GENDER", "AGE_RANGE", "PHONE", "TIMESTAMP"])

# === CONFIRMATION ===
st.success("🎉 All pending members have been assigned to families!")

# === DISPLAY NEWLY ASSIGNED MEMBERS ===
st.markdown("### 👥 Newly Assigned Members")