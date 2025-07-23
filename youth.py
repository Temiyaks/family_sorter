import streamlit as st
import pandas as pd
import re
from collections import Counter
from fpdf import FPDF
import os

# ---- PAGE SETUP ----
st.set_page_config(page_title="FBS Family Sorter", layout="wide")

# ---- TITLE ----
st.title("CCC Akoka Youth Family Restructuring Platform")
st.markdown("""
Welcome to the **Family Balancer Tool**  
Upload your member data as a CSV file. The system will sort members into **5 balanced families** based on:
- Age range
- Gender
- Activity level

Let's get started!
""")

# ---- FILE UPLOAD ----
uploaded_file = st.file_uploader(" Upload Member CSV File", type="csv")

# ---- HELPERS ----
@st.cache_data
def age_range_key(age_str):
    if not isinstance(age_str, str):
        return 9999
    match = re.match(r'(\d+)', age_str)
    if match:
        return int(match.group(1))
    return 9999

def get_stats(df):
    stats = {}
    stats['Gender Distribution'] = df['GENDER'].value_counts().to_frame('Count')
    stats['Activity by Gender'] = df.groupby(['GENDER', 'ACTIVITY']).size().unstack(fill_value=0)
    stats['Age Range Distribution'] = df['AGE_RANGE'].value_counts().sort_index().to_frame('Count')
    stats['Age Range by Gender'] = df.groupby(['GENDER', 'AGE_RANGE']).size().unstack(fill_value=0).sort_index(axis=1)

    if 'Family' in df.columns:
        stats['Family Sizes'] = df['Family'].value_counts().to_frame('Count')
        stats['Gender by Family'] = df.groupby(['Family', 'GENDER']).size().unstack(fill_value=0)
        stats['Activity by Family'] = df.groupby(['Family', 'ACTIVITY']).size().unstack(fill_value=0)
        stats['Age Range by Family'] = df.groupby(['Family', 'AGE_RANGE']).size().unstack(fill_value=0).sort_index(axis=1)
    return stats

def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

def create_family_pdf(dataframe, save_path):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 12)
            self.cell(0, 10, 'CCC Akoka Youth Family Groups', 0, 1, 'C')
            self.ln(5)

    pdf = PDF()
    families = dataframe['Family'].unique()
    families.sort()

    for fam in families:
        pdf.add_page()
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, f'{fam}', ln=True)

        pdf.set_font('Arial', 'B', 10)
        pdf.cell(60, 10, 'Name', 1)
        pdf.cell(40, 10, 'Gender', 1)
        pdf.ln()

        members = dataframe[dataframe['Family'] == fam]
        for _, row in members.iterrows():
            pdf.set_font('Arial', '', 10)
            pdf.cell(60, 10, str(row['NAME']), 1)
            pdf.cell(40, 10, str(row['GENDER']), 1)
            pdf.ln()

    pdf.output(save_path)

# ---- MAIN LOGIC ----
if uploaded_file:
    df = pd.read_csv(uploaded_file, dtype={'PHONE': str})

    with st.spinner("🔄 Processing and assigning families..."):
        inactive_mask = df['ACTIVITY'].str.upper() == 'INACTIVE'
        df.loc[inactive_mask, 'GENDER'] = df.loc[inactive_mask, 'GENDER'].fillna('UNKNOWN').str.upper()
        df.loc[inactive_mask, 'AGE_RANGE'] = df.loc[inactive_mask, 'AGE_RANGE'].fillna('UNKNOWN')

        df['GENDER'] = df['GENDER'].str.upper()
        df['NAME'] = df['NAME'].combine_first(df.index.to_series().apply(lambda i: f"Unknown_{i}"))

        df = df.dropna(subset=['AGE_RANGE'])
        unique_age_ranges = sorted(df['AGE_RANGE'].unique(), key=age_range_key)
        if 'UNKNOWN' not in unique_age_ranges:
            unique_age_ranges.append('UNKNOWN')
        df['AGE_RANGE'] = pd.Categorical(df['AGE_RANGE'], categories=unique_age_ranges, ordered=True)

        stats_before = get_stats(df)

        # FAMILY ASSIGNMENT
        num_families = 5
        df['Family'] = None
        all_activity_types = df['ACTIVITY'].dropna().unique().tolist()
        grouped = df.groupby(['GENDER', 'AGE_RANGE', 'ACTIVITY'])

        family_sizes = Counter({f'Family {i}': 0 for i in range(1, num_families + 1)})
        activity_count = {
            f'Family {i}': {atype: 0 for atype in all_activity_types}
            for i in range(1, num_families + 1)
        }

        total_members = len(df)
        base_size = total_members // num_families
        max_size = base_size + (1 if total_members % num_families != 0 else 0)

        def pick_family(family_sizes, activity_count, activity_type):
            min_size = min(family_sizes.values())
            candidates = [fam for fam, size in family_sizes.items() if size < max_size and size == min_size]
            if not candidates:
                candidates = sorted(family_sizes, key=lambda f: family_sizes[f])
            candidates = sorted(candidates, key=lambda fam: activity_count[fam].get(activity_type, 0))
            return candidates[0]

        for group_keys, group_df in grouped:
            indices = group_df.index.tolist()
            gender, age_range, activity = group_keys
            for i in range(len(indices)):
                fam = pick_family(family_sizes, activity_count, activity)
                df.at[indices[i], 'Family'] = fam
                family_sizes[fam] += 1
                activity_count[fam][activity] += 1

        df['AGE_RANGE'] = pd.Categorical(df['AGE_RANGE'], categories=unique_age_ranges, ordered=True)

        stats_after = get_stats(df)

        # Save CSV and PDF to temporary local paths (for download only)
        full_csv_path = "grouped_full.csv"
        pdf_path = "grouped_printable.pdf"

        df.to_csv(full_csv_path, index=False)
        printable_df = df[['NAME', 'GENDER', 'Family']]
        create_family_pdf(printable_df, pdf_path)

    # ---- SUCCESS MESSAGE ----
    st.success("✅ Family assignment completed!")

    # ---- DOWNLOADS ----
    with open(full_csv_path, "rb") as f_csv:
        st.download_button("⬇️ Download Grouped CSV", f_csv, file_name="grouped_families.csv", mime="text/csv")

    with open(pdf_path, "rb") as f_pdf:
        st.download_button("📥 Download Printable PDF", f_pdf, file_name="grouped_printable.pdf", mime="application/pdf")

    # ---- STATISTICS ----
    with st.expander("📊 View Statistics Before Grouping"):
        for title, stat_df in stats_before.items():
            st.markdown(f"**{title}**")
            st.dataframe(stat_df)

    with st.expander("📈 View Statistics After Grouping"):
        for title, stat_df in stats_after.items():
            st.markdown(f"**{title}**")
            st.dataframe(stat_df)
