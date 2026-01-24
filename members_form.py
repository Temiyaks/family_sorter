import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from rapidfuzz import fuzz

# Page config
st.set_page_config(page_title="Youth Family Form", layout="centered")

# Form access window
start_date = datetime(2025, 8, 1)
access_days = 400
end_date = start_date + pd.Timedelta(days=access_days)
today = datetime.now()

if not (start_date <= today <= end_date):
    st.error("⛔ The registration form is currently closed.")
    st.stop()

st.image("CCCAkokaLogo.PNG", width=150)
st.title("📝 Youth Family Form")
st.info(f"🗓️ This form will remain open until {end_date.strftime('%B %d, %Y')}")

# Form UI (NO Google calls here)
with st.form("registration_form"):
    name = st.text_input("Full Name").strip().title()
    gender = st.selectbox("Gender", ["MALE", "FEMALE"])
    age_range = st.selectbox("Age Range", ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54"])
    phone = st.text_input("Phone Number (e.g., 08123456789)").strip()
    submit = st.form_submit_button("Submit")

# Only now do we connect to Google Sheets
if submit:
    if not name or not phone:
        st.error("Full Name and Phone Number are required.")
        st.stop()

    # Normalize phone
    if phone.startswith("0"):
        standardized_phone = phone
    elif phone.startswith("234") and len(phone) == 13:
        standardized_phone = "0" + phone[3:]
    elif len(phone) == 10 and phone.isdigit():
        standardized_phone = "0" + phone
    else:
        standardized_phone = phone

    if not (standardized_phone.startswith("0") and len(standardized_phone) == 11 and standardized_phone.isdigit()):
        st.error("Phone number must be 11 digits and start with 0.")
        st.stop()

    # Google auth (inside submit)
    creds_dict = dict(st.secrets["google_service_account"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    sheet = client.open("Youth Family Assignment")
    master_df = pd.DataFrame(sheet.worksheet("Master").get_all_records())
    pending_df = pd.DataFrame(sheet.worksheet("Pending").get_all_records())

    master_df.rename(columns=lambda x: x.strip().upper(), inplace=True)
    pending_df.rename(columns=lambda x: x.strip().upper(), inplace=True)

    master_df["PHONE"] = master_df["PHONE"].astype(str).apply(lambda x: "0" + x[-10:] if len(x) >= 10 else x)
    pending_df["PHONE"] = pending_df["PHONE"].astype(str).apply(lambda x: "0" + x[-10:] if len(x) >= 10 else x)

    FUZZY_MATCH_THRESHOLD = 85

    for _, row in master_df.iterrows():
        if fuzz.token_sort_ratio(name, row["NAME"]) >= FUZZY_MATCH_THRESHOLD or standardized_phone == row["PHONE"]:
            st.error("⚠️ A similar registration already exists.")
            st.stop()

    for _, row in pending_df.iterrows():
        if fuzz.token_sort_ratio(name, row["NAME"]) >= FUZZY_MATCH_THRESHOLD or standardized_phone == row["PHONE"]:
            st.warning("⏳ A similar submission already exists. Please wait.")
            st.stop()

    worksheet = sheet.worksheet("Pending")
    worksheet.append_row([
        name, gender, age_range, standardized_phone,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ])

    st.success("✅ Registration successful! Your entry is pending approval.")
