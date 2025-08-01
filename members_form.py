import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from rapidfuzz import fuzz  # 👈 Fuzzy matching for names

# === CONFIGURE FORM ACCESS WINDOW ===
start_date = datetime(2025, 8, 1)  # 🗓️ Set this to form start date
access_days = 5                   # ⏳ Number of days form stays open
end_date = start_date + pd.Timedelta(days=access_days)
today = datetime.now()

# === Check Form Access ===
if not (start_date <= today <= end_date):
    st.error(f"⛔ The registration form is currently closed.\n\n"
             f"It was open from {start_date.strftime('%b %d')} to {end_date.strftime('%b %d')}.")
    st.stop()

# === PAGE SETUP ===
st.set_page_config(page_title="Youth Family Form", layout="centered")
st.image("CCCAkokaLogo.PNG", width=150)
st.title("📝 Youth Family Form")



st.markdown("""
### 👋 Welcome!

To join a family group, please fill out this form **with your correct full name and phone number**.

- Do **not** use nicknames, initials, or alternate spellings.
- Use a valid phone number that you actively use.
- Duplicate or suspicious entries may be rejected.


Please fill this form **only once** — submitting more than once may delay your assignment to the family
""")




# === Load Google Service Account Credentials ===
creds_dict = dict(st.secrets["google_service_account"])
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# === Open Google Sheets ===
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
    pending_df = pd.DataFrame(pending_records) if pending_records else pd.DataFrame(columns=["NAME", "GENDER", "AGE_RANGE", "PHONE", "TIMESTAMP"])
except Exception as e:
    st.warning(f"Could not load pending sheet: {e}")
    pending_df = pd.DataFrame(columns=["NAME", "GENDER", "AGE_RANGE", "PHONE", "TIMESTAMP"])

# Clean up pending_df
pending_df.rename(columns=lambda x: x.strip().upper(), inplace=True)
pending_df["PHONE"] = pending_df["PHONE"].astype(str).apply(lambda x: "0" + x[-10:] if len(x) >= 10 else x)

# === FORM UI ===
with st.form("registration_form"):
    name = st.text_input("Full Name").strip().title()
    gender = st.selectbox("Gender", ["MALE", "FEMALE"])
    age_range = st.selectbox("Age Range", ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54"])
    phone = st.text_input("Phone Number (e.g., 08123456789)").strip()
    submit = st.form_submit_button("Submit")

    if submit:
        if not name:
            st.error("Full Name is required.")
            st.stop()
        if not phone:
            st.error("Phone Number is required.")
            st.stop()

        # === Standardize Phone Number ===
        if phone.startswith("0"):
            standardized_phone = phone
        elif phone.startswith("234") and len(phone) == 13:
            standardized_phone = "0" + phone[3:]
        elif len(phone) == 10 and phone.isdigit():
            standardized_phone = "0" + phone
        else:
            standardized_phone = phone

        # === Phone Format Validation ===
        if not (standardized_phone.startswith("0") and len(standardized_phone) == 11 and standardized_phone.isdigit()):
            st.error("Phone number must start with 0 and be exactly 11 digits long (e.g., 08123456789).")
            st.stop()

        # Show confirmation
        st.markdown("### ✅ Please confirm your details before final submission:")
        st.info(f"""
        **Name:** {name}  
        **Gender:** {gender}  
        **Age Range:** {age_range}  
        **Phone:** {standardized_phone}
        """)


        confirm = st.radio("Are these details correct?", ["Yes, submit", "No, go back"])

        if confirm == "Yes, submit":
            entry = {
                "NAME": name,
                "GENDER": gender.upper(),
                "AGE_RANGE": age_range,
                "PHONE": standardized_phone,
                "TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }





        # entry = {
        #     "NAME": name,
        #     "GENDER": gender.upper(),
        #     "AGE_RANGE": age_range,
        #     "PHONE": standardized_phone,
        #     "TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # }

        # === DUPLICATE CHECKS ===
        FUZZY_MATCH_THRESHOLD = 70

        # Check against Master (already assigned)
        for _, row in master_df.iterrows():
            name_score = fuzz.token_sort_ratio(name, row["NAME"])
            if name_score >= FUZZY_MATCH_THRESHOLD or standardized_phone == row["PHONE"]:
                st.error(
                    f"⚠️ A similar registration already exists: {row['NAME']} (Phone: {row['PHONE']}) "
                    f"assigned to {row.get('FAMILY', 'a family')}.\n\nPlease do not register again."
                )
                st.stop()

        # Check against Pending (waiting)
        for _, row in pending_df.iterrows():
            name_score = fuzz.token_sort_ratio(name, row["NAME"])
            if name_score >= FUZZY_MATCH_THRESHOLD or standardized_phone == row["PHONE"]:
                st.warning(
                    f"⏳ A similar submission already exists: {row['NAME']} (Phone: {row['PHONE']}) "
                    f"submitted on {row['TIMESTAMP']}.\n\nPlease wait to be assigned."
                )
                st.stop()

        # === Save Entry to Pending Sheet ===
        worksheet.append_row(list(entry.values()))
        st.success("✅ Your registration was successful and is pending approval.")
    

    else:
        st.warning("Please review and correct your information before submitting.")
