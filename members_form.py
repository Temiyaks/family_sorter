import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from rapidfuzz import fuzz

# =========================================================
# PAGE CONFIG (MUST BE FIRST)
# =========================================================
st.set_page_config(
    page_title="Youth Family Form",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# =========================================================
# FORM ACCESS WINDOW
# =========================================================
start_date = datetime(2025, 8, 1)
access_days = 400
end_date = start_date + pd.Timedelta(days=access_days)
today = datetime.now()

if not (start_date <= today <= end_date):
    st.error(
        f"⛔ The registration form is currently closed.\n\n"
        f"It was open from {start_date.strftime('%b %d')} to {end_date.strftime('%b %d')}."
    )
    st.stop()

# =========================================================
# HEADER
# =========================================================
st.image("CCCAkokaLogo.PNG", width=150)
st.title("📝 Youth Family Form")

st.info(f"🗓️ This form will remain open until **{end_date.strftime('%B %d, %Y')}**.")
st.info("📱 Android users: If this page fails to load, open it in **Chrome** (not WhatsApp browser).")

st.markdown("""
### 👋 Welcome!

To join a family group, please fill out this form **with your correct full name and phone number**.

- Do **not** use nicknames or initials  
- Use a valid phone number you actively use  
- Please submit **only once**
""")

# =========================================================
# GOOGLE CLIENT (CACHED — CRITICAL)
# =========================================================
@st.cache_resource
def get_gspread_client():
    creds_dict = dict(st.secrets["google_service_account"])
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

# =========================================================
# LOAD DATA (CACHED — MOBILE SAFE)
# =========================================================
@st.cache_data(ttl=300)  # refresh every 5 minutes
def load_data(client):
    sheet = client.open("Youth Family Assignment")

    master = pd.DataFrame(sheet.worksheet("Master").get_all_records())
    pending = pd.DataFrame(sheet.worksheet("Pending").get_all_records())

    if not master.empty:
        master.rename(columns=lambda x: x.strip().upper(), inplace=True)
        master["PHONE"] = master["PHONE"].astype(str).apply(
            lambda x: "0" + x[-10:] if len(x) >= 10 else x
        )

    if not pending.empty:
        pending.rename(columns=lambda x: x.strip().upper(), inplace=True)
        pending["PHONE"] = pending["PHONE"].astype(str).apply(
            lambda x: "0" + x[-10:] if len(x) >= 10 else x
        )

    return master, pending

# =========================================================
# SAFE CONNECTION
# =========================================================
try:
    client = get_gspread_client()
    master_df, pending_df = load_data(client)
except Exception as e:
    st.error("⚠️ Unable to connect to the server. Please refresh or open in Chrome.")
    st.stop()

# =========================================================
# FORM
# =========================================================
with st.form("registration_form"):
    name = st.text_input("Full Name").strip().title()
    gender = st.selectbox("Gender", ["MALE", "FEMALE"])
    age_range = st.selectbox(
        "Age Range",
        ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54"]
    )
    phone = st.text_input("Phone Number (e.g., 08123456789)").strip()

    submit = st.form_submit_button("Submit")

# =========================================================
# SUBMISSION LOGIC (RUNS ONLY AFTER CLICK)
# =========================================================
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

    if not (
        standardized_phone.startswith("0")
        and standardized_phone.isdigit()
        and len(standardized_phone) == 11
    ):
        st.error("Phone number must be 11 digits and start with 0.")
        st.stop()

    FUZZY_MATCH_THRESHOLD = 85

    # Check Master
    for _, row in master_df.iterrows():
        if (
            fuzz.token_sort_ratio(name, row["NAME"]) >= FUZZY_MATCH_THRESHOLD
            or standardized_phone == row["PHONE"]
        ):
            st.error(
                f"⚠️ A similar registration already exists for **{row['NAME']}**.\n\n"
                "Please do not register again."
            )
            st.stop()

    # Check Pending
    for _, row in pending_df.iterrows():
        if (
            fuzz.token_sort_ratio(name, row["NAME"]) >= FUZZY_MATCH_THRESHOLD
            or standardized_phone == row["PHONE"]
        ):
            st.warning(
                f"⏳ A similar submission already exists for **{row['NAME']}**.\n\n"
                "Please wait to be assigned."
            )
            st.stop()

    # Save
    worksheet = client.open("Youth Family Assignment").worksheet("Pending")
    worksheet.append_row([
        name,
        gender,
        age_range,
        standardized_phone,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ])

    st.success("✅ Registration successful! Your entry is pending approval.")
