# === FORM OR CONFIRMATION ===

if not st.session_state.confirmed:
    # Pre-fill fields if returning to edit
    default_entry = st.session_state.entry if st.session_state.entry else {}
    name = st.text_input("Full Name", value=default_entry.get("NAME", "")).strip().title()
    gender = st.selectbox("Gender", ["MALE", "FEMALE"], index=["MALE", "FEMALE"].index(default_entry.get("GENDER", "MALE")))
    age_range = st.selectbox("Age Range", [
        "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54"
    ], index=["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54"].index(default_entry.get("AGE_RANGE", "20-24")))
    phone = st.text_input("Phone Number (e.g., 08123456789)", value=default_entry.get("PHONE", "")).strip()

    if st.form_submit_button("Submit"):
        if not name:
            st.error("Full Name is required.")
            st.stop()
        if not phone:
            st.error("Phone Number is required.")
            st.stop()

        # Standardize phone
        if phone.startswith("0"):
            standardized_phone = phone
        elif phone.startswith("234") and len(phone) == 13:
            standardized_phone = "0" + phone[3:]
        elif len(phone) == 10 and phone.isdigit():
            standardized_phone = "0" + phone
        else:
            standardized_phone = phone

        if not (standardized_phone.startswith("0") and len(standardized_phone) == 11 and standardized_phone.isdigit()):
            st.error("Phone number must start with 0 and be exactly 11 digits long.")
            st.stop()

        st.session_state.entry = {
            "NAME": name,
            "GENDER": gender.upper(),
            "AGE_RANGE": age_range,
            "PHONE": standardized_phone,
            "TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        st.session_state.confirmed = True

# === CONFIRMATION VIEW ===
if st.session_state.confirmed and st.session_state.entry:
    entry = st.session_state.entry
    st.markdown("### ✅ Please confirm your details before submission:")
    st.info(f"""
    **Name:** {entry['NAME']}  
    **Gender:** {entry['GENDER']}  
    **Age Range:** {entry['AGE_RANGE']}  
    **Phone:** {entry['PHONE']}
    """)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Confirm and Submit"):
            FUZZY_MATCH_THRESHOLD = 85

            # Master sheet check
            for _, row in master_df.iterrows():
                name_score = fuzz.token_sort_ratio(entry["NAME"], row["NAME"])
                if name_score >= FUZZY_MATCH_THRESHOLD or entry["PHONE"] == row["PHONE"]:
                    st.error(
                        f"⚠️ A similar registration already exists: {row['NAME']} (Phone: {row['PHONE']}) "
                        f"assigned to {row.get('FAMILY', 'a family')}."
                    )
                    st.session_state.confirmed = False
                    break

            # Pending check
            for _, row in pending_df.iterrows():
                name_score = fuzz.token_sort_ratio(entry["NAME"], row["NAME"])
                if name_score >= FUZZY_MATCH_THRESHOLD or entry["PHONE"] == row["PHONE"]:
                    st.warning(
                        f"⏳ A similar submission already exists: {row['NAME']} (Phone: {row['PHONE']}) "
                        f"submitted on {row['TIMESTAMP']}.\n\nPlease wait to be assigned."
                    )
                    st.session_state.confirmed = False
                    break

            if st.session_state.confirmed:  # Only append if no issues
                worksheet.append_row(list(entry.values()))
                st.success("✅ Your registration was successful and is pending approval.")
                st.session_state.confirmed = False
                st.session_state.entry = None

    with col2:
        if st.button("✏️ Edit"):
            # Just flip confirmed back to False to return to the form with data intact
            st.session_state.confirmed = False
