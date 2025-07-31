import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="Youth Family Assignment Form", layout="centered")

st.title("📝 Youth Family Assignment Form")

# File paths
MASTER_DATA_PATH = "master_data.csv"
PENDING_DATA_PATH = "pending_data.csv"

# Load or create master_data.csv
if os.path.exists(MASTER_DATA_PATH):
    master_df = pd.read_csv(MASTER_DATA_PATH, dtype={"PHONE": str})
else:
    master_df = pd.DataFrame(columns=["NAME", "GENDER", "AGE_RANGE", "PHONE", "FAMILY"])

# Load or create pending_data.csv
if os.path.exists(PENDING_DATA_PATH):
    pending_df = pd.read_csv(PENDING_DATA_PATH, dtype={"PHONE": str})
else:
    pending_df = pd.DataFrame(columns=["NAME", "GENDER", "AGE_RANGE", "PHONE", "TIMESTAMP"])

# Form
with st.form("registration_form"):
    name = st.text_input("Full Name").strip().title()
    gender = st.selectbox("Gender", ["MALE", "FEMALE"])
    age_range = st.selectbox("Age Range", ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54"])
    phone = st.text_input("Phone Number (e.g., 08123456789)").strip()

    submit = st.form_submit_button("Submit")

    if submit:
        # Standardize phone number by ensuring it starts with zero
        if phone.startswith("0"):
            standardized_phone = phone
        elif phone.startswith("234") and len(phone) == 13:
            standardized_phone = "0" + phone[3:]
        elif len(phone) == 10 and phone.isdigit():
            standardized_phone = "0" + phone
        else:
            standardized_phone = phone  # fallback

        # Capitalize inputs
        entry = {
            "NAME": name,
            "GENDER": gender.upper(),
            "AGE_RANGE": age_range,
            "PHONE": standardized_phone
        }


        # if standardized_phone in master_df["PHONE"].values:
        #     member_name = master_df.loc[master_df["PHONE"] == standardized_phone, "Name"].values[0]
        #     family_name = master_df.loc[master_df["PHONE"] == standardized_phone, "FAMILY"].values[0]
        #     st.error(f"⚠️ {member_name} is already registered and assigned to **{family_name}**. Please do not register again.")


        # Validate against master data
        if standardized_phone in master_df["PHONE"].values:
            assigned_family = master_df.loc[master_df["PHONE"] == standardized_phone, "FAMILY"].values[0]
            member_name = master_df.loc[master_df["PHONE"] == standardized_phone, "Name"].values[0]
            st.error(
                f"⚠️  **{member_name}** is already registered and assigned to **{assigned_family}**.\n\n"
                "Please do not register again."
            )

        # Validate against pending data
        elif standardized_phone in pending_df["PHONE"].values:
            pending_name = pending_df.loc[pending_df["PHONE"] == standardized_phone, "NAME"].values[0]
            submission_time = pending_df.loc[pending_df["PHONE"] == standardized_phone, "TIMESTAMP"].values[0]
            st.warning(
                f"⏳ **{pending_name}** was already submitted on **{submission_time}**.\n\n"
                "Your registration is being reviewed and will be assigned to a family group soon. \n\n"
                 "No need to submit again — we’ll notify you once it’s complete!."
            )

        # Proceed to save
        else:
            entry["TIMESTAMP"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pending_df = pending_df.append(entry, ignore_index=True)
            pending_df.to_csv(PENDING_DATA_PATH, index=False)
            st.success("✅ Your registration was successful and is pending approval.")
