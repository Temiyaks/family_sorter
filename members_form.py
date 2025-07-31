import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# 👇 Show the logo
st.image("CCCAkokaLogo.PNG", width=150)

st.set_page_config(page_title="Youth Family Form", layout="centered")
st.title("📝 Youth Family Form")




# Read credentials from Streamlit secrets
creds_dict = st.secrets["google_service_account"]

# Save credentials as a dict
creds_json = json.loads(json.dumps(creds_dict))

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
client = gspread.authorize(creds)

# Open Google Sheet
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/your-sheet-id")
worksheet = sheet.sheet1


# === Google Sheet Configuration ===
SHEET_NAME = "Youth Family Assignment"
WORKSHEET_NAME = "Pending"

try:
    sheet = client.open(SHEET_NAME)
except gspread.SpreadsheetNotFound:
    st.error(f"Google Sheet '{SHEET_NAME}' not found. Please create it and share with your service account email.")
    st.stop()

worksheet = sheet.worksheet(WORKSHEET_NAME)

# === Load Master Data ===
try:
    master_df = pd.DataFrame(sheet.worksheet("Master").get_all_records())
    master_df.rename(columns=lambda x: x.strip().upper(), inplace=True)
    master_df["PHONE"] = master_df["PHONE"].astype(str).apply(lambda x: "0" + x[-10:] if len(x) >= 10 else x)
except:
    master_df = pd.DataFrame(columns=["NAME", "GENDER", "AGE_RANGE", "PHONE", "FAMILY"])

# === Load Pending Data ===
try:
    pending_records = worksheet.get_all_records()
    if pending_records:
        pending_df = pd.DataFrame(pending_records)
    else:
        pending_df = pd.DataFrame(columns=["NAME", "GENDER", "AGE_RANGE", "PHONE", "TIMESTAMP"])
except Exception as e:
    st.warning(f"Could not load pending sheet: {e}")
    pending_df = pd.DataFrame(columns=["NAME", "GENDER", "AGE_RANGE", "PHONE", "TIMESTAMP"])

# Clean up pending_df columns
pending_df.rename(columns=lambda x: x.strip().upper(), inplace=True)
pending_df["PHONE"] = pending_df["PHONE"].astype(str).apply(lambda x: "0" + x[-10:] if len(x) >= 10 else x)

# === Streamlit Form ===
with st.form("registration_form"):
    name = st.text_input("Full Name").strip().title()
    gender = st.selectbox("Gender", ["MALE", "FEMALE"])
    age_range = st.selectbox("Age Range", ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54"])
    phone = st.text_input("Phone Number (e.g., 08123456789)").strip()
    submit = st.form_submit_button("Submit")

    if submit:
        if not name:
            st.error(" Full Name is required")
            st.stop()
        if not phone:
            st.error("Phone Number is required")
            st.stop()
        
        # === Standardize Input Phone ===
        if phone.startswith("0"):
            standardized_phone = phone
        elif phone.startswith("234") and len(phone) == 13:
            standardized_phone = "0" + phone[3:]
        elif len(phone) == 10 and phone.isdigit():
            standardized_phone = "0" + phone
        else:
            standardized_phone = phone  # fallback

        # === Phone number validation ===
        if not (standardized_phone.startswith("0") and len(standardized_phone) == 11 and standardized_phone.isdigit()):
            
            st.error("Phone number must start with 0 and be exactly 11 digits long (e.g., 08123456789).")
            st.stop()


        entry = {
            "NAME": name,
            "GENDER": gender.upper(),
            "AGE_RANGE": age_range,
            "PHONE": standardized_phone,
            "TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # === Duplicate Check: Master Sheet ===
        if standardized_phone in master_df["PHONE"].values:
            assigned_family = master_df.loc[master_df["PHONE"] == standardized_phone, "FAMILY"].values[0]
            member_name = master_df.loc[master_df["PHONE"] == standardized_phone, "NAME"].values[0]
            st.error(
                f"⚠️ {member_name} is already registered and assigned to {assigned_family}.\n\n"
                "Please do not register again."
            )
            st.stop()

        # === Duplicate Check: Pending Sheet ===
        if standardized_phone in pending_df["PHONE"].values:
            pending_name = pending_df.loc[pending_df["PHONE"] == standardized_phone, "NAME"].values[0]
            submission_time = pending_df.loc[pending_df["PHONE"] == standardized_phone, "TIMESTAMP"].values[0]
            st.warning(
                f"⏳ {pending_name} already submitted on {submission_time}.\n\n"
                "No need to submit again — we’ll notify you once assigned."
            )
            st.stop()

        # === No Duplicate: Save to Pending Sheet ===
        worksheet.append_row(list(entry.values()))
        st.success("✅ Your registration was successful and is pending approval.")
