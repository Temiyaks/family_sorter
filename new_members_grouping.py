import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Assign Families", layout="centered")
st.title("👨‍👩‍👧‍👦 Assign new members to Families")

st.markdown("""
### 👋 Welcome to the Family Assignment Page

This tool helps us *assign new youth members* to one of our existing family groups.

📌 *How it works*:
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

# === Sheet Config ===
SHEET_NAME = "Youth Family Assignment"
MASTER_WS = "Master"
PENDING_WS = "Pending"

try:
    sheet = client.open(SHEET_NAME)
    master_ws = sheet.worksheet(MASTER_WS)
    pending_ws = sheet.worksheet(PENDING_WS)
except Exception as e:
    st.error(f"Could not open sheet: {e}")
    st.stop()

# === Load Master Data ===
master_df = pd.DataFrame(master_ws.get_all_records())
if not master_df.empty:
    master_df.rename(columns=lambda x: x.strip().upper(), inplace=True)
else:
    master_df = pd.DataFrame(columns=["NAME", "GENDER", "AGE_RANGE", "PHONE", "FAMILY"])

# === Load Pending Data ===
pending_df = pd.DataFrame(pending_ws.get_all_records())
if pending_df.empty:
    st.success("✅ No pending entries to assign.")
    st.stop()
pending_df.rename(columns=lambda x: x.strip().upper(), inplace=True)

# === Determine Existing Families and Their Counts ===
if "FAMILY" not in master_df.columns:
    st.error("Master data must contain 'FAMILY' column.")
    st.stop()

family_list = master_df["FAMILY"].dropna().unique().tolist()
family_counts = {family: len(master_df[master_df["FAMILY"] == family]) for family in family_list}

# === Assign People ===
assigned_rows = []
for idx, row in pending_df.iterrows():
    gender = row["GENDER"]
    age_range = row["AGE_RANGE"]
    
    # Find family with the least count
    target_family = min(family_counts, key=family_counts.get)
    family_counts[target_family] += 1  # Increment count for balancing

    assigned_row = {
        "NAME": row["NAME"],
        "GENDER": gender,
        "AGE_RANGE": age_range,
        "PHONE": str(row["PHONE"]),
        "FAMILY": target_family,
        "TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    assigned_rows.append(assigned_row)

# === Confirm Assignment ===
if st.button("✅ Assign Pending to Families"):
    # Append to Master
    for row in assigned_rows:
        master_ws.append_row(list(row.values()))
    
    # Clear Pending Sheet
    pending_ws.clear()
    pending_ws.append_row(["NAME", "GENDER", "AGE_RANGE", "PHONE", "TIMESTAMP"])
    
    st.success(f"✅ {len(assigned_rows)} members have been assigned to families and added to the master sheet.")
    st.info("Old entries in the master have no timestamp. Newly assigned members now include a timestamp.")
    st.dataframe(pd.DataFrame(assigned_rows))


