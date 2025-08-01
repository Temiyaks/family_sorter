# === Session State to track confirmation ===
if "confirmed" not in st.session_state:
    st.session_state.confirmed = False

if submit and not st.session_state.confirmed:
    if not name:
        st.error("Full Name is required.")
        st.stop()
    if not phone:
        st.error("Phone Number is required.")
        st.stop()

    # === Standardize phone number ===
    if phone.startswith("0"):
        standardized_phone = phone
    elif phone.startswith("234") and len(phone) == 13:
        standardized_phone = "0" + phone[3:]
    elif len(phone) == 10 and phone.isdigit():
        standardized_phone = "0" + phone
    else:
        standardized_phone = phone

    if not (standardized_phone.startswith("0") and len(standardized_phone) == 11 and standardized_phone.isdigit()):
        st.error("Phone number must start with 0 and be exactly 11 digits long (e.g., 08123456789).")
        st.stop()

    # Save inputs to session
    st.session_state.entry = {
        "NAME": name,
        "GENDER": gender.upper(),
        "AGE_RANGE": age_range,
        "PHONE": standardized_phone,
        "TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Show confirmation view
    st.markdown("### ✅ Please confirm your details before final submission:")
    st.info(f"""
    **Name:** {name}  
    **Gender:** {gender}  
    **Age Range:** {age_range}  
    **Phone:** {standardized_phone}
    """)
    if st.button("✅ Confirm and Submit"):
        st.session_state.confirmed = True
        st.experimental_rerun()

# === Final submission after confirmation ===
if st.session_state.confirmed and "entry" in st.session_state:
    entry = st.session_state.entry
    FUZZY_MATCH_THRESHOLD = 80

    # Check against Master
    for _, row in master_df.iterrows():
        name_score = fuzz.token_sort_ratio(entry["NAME"], row["NAME"])
        if name_score >= FUZZY_MATCH_THRESHOLD or entry["PHONE"] == row["PHONE"]:
            st.error(
                f"⚠️ A similar registration already exists: {row['NAME']} (Phone: {row['PHONE']}) "
                f"assigned to {row.get('FAMILY', 'a family')}.\n\nPlease do not register again."
            )
            st.session_state.confirmed = False
            st.stop()

    # Check against Pending
    for _, row in pending_df.iterrows():
        name_score = fuzz.token_sort_ratio(entry["NAME"], row["NAME"])
        if name_score >= FUZZY_MATCH_THRESHOLD or entry["PHONE"] == row["PHONE"]:
            st.warning(
                f"⏳ A similar submission already exists: {row['NAME']} (Phone: {row['PHONE']}) "
                f"submitted on {row['TIMESTAMP']}.\n\nPlease wait to be assigned."
            )
            st.session_state.confirmed = False
            st.stop()

    # Save to sheet
    worksheet.append_row(list(entry.values()))
    st.success("✅ Your registration was successful and is pending approval.")
    st.session_state.confirmed = False
