import streamlit as st
import pandas as pd
from datetime import datetime
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 👇 Show the logo
st.image("CCCAkokaLogo.PNG", width=150)

st.set_page_config(page_title="Youth Family Form", layout="centered")

st.title("📝 Youth Family Form")

# === Google Sheets Setup ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(creds)

# === Google Sheet Configuration ===
SHEET_NAME = "Youth Family Assignment"
WORKSHEET_NAME = "Pending"
try:
    sheet = client.open(SHEET_NAME)
except gspread.SpreadsheetNotFound:
    st.error(f"Google Sheet '{SHEET_NAME}' not found. Please create it first and share with the service account email.")
    st.stop()

worksheet = sheet.worksheet(WORKSHEET_NAME)

# Load existing master data from another worksheet
try:
    master_df = pd.DataFrame(sheet.worksheet("Master").get_all_records())
except:
    master_df = pd.DataFrame(columns=["NAME", "GENDER", "AGE_RANGE", "PHONE", "FAMILY"])

# Load existing pending data
try:
    pending_df = pd.DataFrame(worksheet.get_all_records())
except:
    pending_df = pd.DataFrame(columns=["NAME", "GENDER", "AGE_RANGE", "PHONE", "TIMESTAMP"])

# === Streamlit Form ===
with st.form("registration_form"):
    name = st.text_input("Full Name").strip().title()
    gender = st.selectbox("Gender", ["MALE", "FEMALE"])
    age_range = st.selectbox("Age Range", ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54"])
    phone = st.text_input("Phone Number (e.g., 08123456789)").strip()
    submit = st.form_submit_button("Submit")

    if submit:
        # === Standardize phone ===
        if phone.startswith("0"):
            standardized_phone = phone
        elif phone.startswith("234") and len(phone) == 13:
            standardized_phone = "0" + phone[3:]
        elif len(phone) == 10 and phone.isdigit():
            standardized_phone = "0" + phone
        else:
            standardized_phone = phone  # fallback

        entry = {
            "NAME": name,
            "GENDER": gender.upper(),
            "AGE_RANGE": age_range,
            "PHONE": standardized_phone,
            "TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # === Check for duplicates in master sheet ===
        if standardized_phone in master_df["PHONE"].values:
            assigned_family = master_df.loc[master_df["PHONE"] == standardized_phone, "FAMILY"].values[0]
            member_name = master_df.loc[master_df["PHONE"] == standardized_phone, "NAME"].values[0]
            st.error(
                f"⚠️ **{member_name}** is already registered and assigned to **{assigned_family}**.\n\n"
                "Please do not register again."
            )

        # === Check for duplicates in pending sheet ===
        elif standardized_phone in pending_df["PHONE"].values:
            pending_name = pending_df.loc[pending_df["PHONE"] == standardized_phone, "NAME"].values[0]
            submission_time = pending_df.loc[pending_df["PHONE"] == standardized_phone, "TIMESTAMP"].values[0]
            st.warning(
                f"⏳ **{pending_name}** already submitted on **{submission_time}**.\n\n"
                "No need to submit again — we’ll notify you once assigned."
            )

        # === Save to Google Sheet ===
        else:
            worksheet.append_row(list(entry.values()))
            st.success("✅ Your registration was successful and is pending approval.")
