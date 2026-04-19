import streamlit as st
import pandas as pd
from fpdf import FPDF
import matplotlib.pyplot as plt

# ---- PAGE SETUP ----
st.set_page_config(page_title="Family Restructuring", layout="wide")

# ---- LOGO ----
st.image("CCCAkokaLogo.PNG", width=150)

# ---- TITLE ----
st.title("CCC Akoka Youth Family Restructuring Platform")
st.markdown("""
Upload your CSV file with:
- NAME
- AGE
- GENDER

The system balances members into 5 families based on:
- Equal family size (STRICT)
- Gender distribution
- Age distribution
""")

# ---- FILE UPLOAD ----
uploaded_file = st.file_uploader("Upload Member CSV File", type="csv")

# ---- HELPERS ----
def get_stats(df):
    stats = {}
    stats['Gender Distribution'] = df['GENDER'].value_counts().to_frame('Count')
    stats['Age Distribution'] = df['AGE'].value_counts().sort_index().to_frame('Count')
    stats['Age by Gender'] = df.groupby(['GENDER', 'AGE']).size().unstack(fill_value=0)

    if 'Family' in df.columns:
        stats['Family Sizes'] = df['Family'].value_counts().to_frame('Count')
        stats['Gender by Family'] = df.groupby(['Family', 'GENDER']).size().unstack(fill_value=0)
        stats['Age by Family'] = df.groupby(['Family', 'AGE']).size().unstack(fill_value=0)

    return stats


def create_family_pdf(dataframe, save_path):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 12)
            self.cell(0, 10, 'CCC Akoka Youth Family Groups', 0, 1, 'C')
            self.ln(5)

    pdf = PDF()
    families = sorted(dataframe['Family'].unique())

    for fam in families:
        pdf.add_page()
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, fam, ln=True)

        pdf.set_font('Arial', 'B', 10)
        pdf.cell(80, 10, 'Name', 1)
        pdf.cell(40, 10, 'Gender', 1)
        pdf.cell(30, 10, 'Age', 1)
        pdf.ln()

        members = dataframe[dataframe['Family'] == fam]
        for _, row in members.iterrows():
            pdf.set_font('Arial', '', 10)
            pdf.cell(80, 10, str(row['NAME']), 1)
            pdf.cell(40, 10, str(row['GENDER']), 1)
            pdf.cell(30, 10, str(row['AGE']), 1)
            pdf.ln()

    pdf.output(save_path)


# ---- MAIN ----
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # ---- CLEAN DATA ----
    df['NAME'] = df['NAME'].fillna('Unknown')
    df['GENDER'] = df['GENDER'].fillna('UNKNOWN').str.upper()
    df['AGE'] = pd.to_numeric(df['AGE'], errors='coerce')

    df = df.dropna(subset=['AGE'])

    # Shuffle dataset
    df = df.sample(frac=1).reset_index(drop=True)

    stats_before = get_stats(df)

    # ---- FAMILY ASSIGNMENT (FIXED LOGIC) ----
    num_families = 5
    df['Family'] = None

    families = ['Family ' + str(i) for i in range(1, num_families + 1)]

    # Track family sizes
    family_sizes = {fam: 0 for fam in families}

    # Ideal sizes
    total = len(df)
    base_size = total // num_families
    extra = total % num_families

    max_sizes = {}
    for i, fam in enumerate(families):
        if i < extra:
            max_sizes[fam] = base_size + 1
        else:
            max_sizes[fam] = base_size

    # Group by Gender + Age
    grouped = df.groupby(['GENDER', 'AGE'])

    for _, group_df in grouped:
        group_df = group_df.sample(frac=1)

        for idx in group_df.index:
            # Only choose families that are not full
            valid_families = [f for f in families if family_sizes[f] < max_sizes[f]]

            # Pick the smallest family
            valid_families.sort(key=lambda f: family_sizes[f])
            chosen_family = valid_families[0]

            df.at[idx, 'Family'] = chosen_family
            family_sizes[chosen_family] += 1

    stats_after = get_stats(df)

    # ---- SAVE FILES ----
    csv_path = "grouped_families.csv"
    pdf_path = "grouped_families.pdf"

    df.to_csv(csv_path, index=False)
    create_family_pdf(df, pdf_path)

    # ---- DISPLAY ----
    st.subheader("Statistics Before Grouping")
    for title, stat_df in stats_before.items():
        st.write(title)
        st.dataframe(stat_df)

    st.subheader("Statistics After Grouping")

    st.subheader("Family Sizes")
    fig, ax = plt.subplots()
    stats_after['Family Sizes'].plot(kind='bar', ax=ax, legend=False)
    st.pyplot(fig)

    for title, stat_df in stats_after.items():
        st.write(title)
        st.dataframe(stat_df)

    # ---- DOWNLOADS ----
    with open(csv_path, "rb") as f:
        st.download_button("Download CSV", f, file_name="grouped_families.csv")

    with open(pdf_path, "rb") as f:
        st.download_button("Download PDF", f, file_name="grouped_families.pdf")

    st.success("Families successfully balanced!")
