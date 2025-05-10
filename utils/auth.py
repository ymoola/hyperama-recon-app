import streamlit as st
import ast

def check_auth():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.subheader("🔐 Login to Access App")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        valid_users = ast.literal_eval(st.secrets["APP_USERS"])

        if st.button("Login"):
            if username in valid_users and password == valid_users[username]:
                st.session_state.logged_in = True
                st.success("✅ Logged in successfully")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
        return False
    return True