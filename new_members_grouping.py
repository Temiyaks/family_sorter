import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF
from io import BytesIO

st.set_page_config(page_title="Assign Families", layout="centered")

# === CONSTANTS ===
USERNAME = "admin"
PASSWORD = "cccakoka2025"
SHEET_NAME = "Youth Family Assignment"
MASTER_WS = "Master"
PENDING_WS = "Pending"
PRIORITY_FAMILY = "Family 2"

# === AUTHENTICATION ===
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    with st.form("login_form"):
        st.title("Assign new members to Families")
        st.subheader("Login to Assign Families")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.form_submit_button("Login")

    if login_button:
        if username == USERNAME and password == PASSWORD:
            st.session_state.authenticated = True
        else:
            st.error("❌ Invalid username or password.")
    st.stop()

# === MAIN APP ===
st.title("Assign new members to Families")
st.success("✅ Logged in successfully!")

st.markdown("""
### Welcome to the Family Grouping Page

This tool helps us assign new youth members to one of our existing family groups.

How it works:
- We take the list of pending members who have registered.
- Based on their **gender**, **age range**, and current **family sizes**,  
  they are evenly distributed into existing families.

🧾 Once assigned, new members are automatically moved to the Master Sheet and tagged with a timestamp.

Ready to create new connections? Hit the button below to get started!
""")

# === GOOGLE SHEETS SETUP ===
creds_dict = dict(st.secrets["google_service_account"])
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

try:
    sheet = client.open(SHEET_NAME)
    master_ws = sheet.worksheet(MASTER_WS)
    pending_ws = sheet.worksheet(PENDING_WS)
except Exception as e:
    st.error(f"Could not open sheet: {e}")
    st.stop()

# === LOAD DATA ===
master_df = pd.DataFrame(master_ws.get_all_records())
if not master_df.empty:
    master_df.rename(columns=lambda x: x.strip().upper(), inplace=True)
else:
    master_df = pd.DataFrame(columns=["NAME", "GENDER", "AGE_RANGE", "PHONE", "FAMILY"])

pending_df = pd.DataFrame(pending_ws.get_all_records())
if pending_df.empty:
    st.success("✅ No pending entries to assign.")
    st.stop()
pending_df.rename(columns=lambda x: x.strip().upper(), inplace=True)

if "FAMILY" not in master_df.columns:
    st.error("Master data must contain 'FAMILY' column.")
    st.stop()

# === FAMILY COUNTS (with priority adjustment) ===
family_list = master_df["FAMILY"].dropna().unique().tolist()
family_counts = {family: len(master_df[master_df["FAMILY"] == family]) for family in family_list}

# Prioritize Family 2
if PRIORITY_FAMILY in family_counts:
    family_counts[PRIORITY_FAMILY] = max(0, family_counts[PRIORITY_FAMILY] - 1)

# === ASSIGN MEMBERS ===
grouped = pending_df.groupby(["GENDER", "AGE_RANGE"])
assigned_rows = []

for (gender, age_range), group_df in grouped:
    group_df = group_df.copy()
    group_df.reset_index(drop=True, inplace=True)

    for idx in range(len(group_df)):
        sorted_families = sorted(family_counts.items(), key=lambda x: x[1])
        target_family = sorted_families[0][0]

        member = group_df.loc[idx]
        assigned_rows.append({
            "NAME": member["NAME"],
            "GENDER": gender,
            "AGE_RANGE": age_range,
            "PHONE": str(member["PHONE"]),
            "FAMILY": target_family,
            "TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        family_counts[target_family] += 1

# === PDF GENERATOR ===
def generate_assignment_pdf(assigned_rows):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 14)
            self.cell(0, 10, 'CCC Akoka Youth - Family Assignment Summary', 0, 1, 'C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

        def add_family_section(self, family, members):
            self.set_font('Arial', 'B', 12)
            self.cell(0, 10, family, ln=True)
            self.set_font('Arial', 'B', 10)
            self.cell(90, 8, "Name", 1)
            self.cell(40, 8, "Gender", 1)
            self.ln()

            self.set_font('Arial', '', 10)
            for row in members:
                self.cell(90, 8, row["NAME"], 1)
                self.cell(40, 8, row["GENDER"], 1)
                self.ln()
                if self.get_y() > 270:
                    self.add_page()
                    self.cell(90, 8, "Name", 1)
                    self.cell(40, 8, "Gender", 1)
                    self.ln()

    df = pd.DataFrame(assigned_rows)
    grouped = df.groupby("FAMILY")

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    for family, group_df in grouped:
        members = group_df.to_dict("records")
        pdf.add_family_section(family, members)
        pdf.ln(5)

    pdf_buffer = BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer

# === ASSIGNMENT BUTTON ===
if st.button("✅ Assign Pending to Families"):
    for row in assigned_rows:
        master_ws.append_row(list(row.values()))

    # Reset Pending Sheet
    pending_ws.clear()
    pending_ws.append_row(["NAME", "GENDER", "AGE_RANGE", "PHONE", "TIMESTAMP"])

    st.success(f"✅ {len(assigned_rows)} members have been assigned to families and added to the master sheet.")
    st.info("Old entries in the master have no timestamp. Newly assigned members now include a timestamp.")

    # Generate PDF
    pdf_file = generate_assignment_pdf(assigned_rows)
    st.download_button(
        label="📥 Download Assignment Summary (PDF)",
        data=pdf_file,
        file_name="assigned_families.pdf",
        mime="application/pdf"
    )
