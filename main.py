import streamlit as st
import time

st.sidebar.markdown(
    "<h1 style='font-family: Comic Sans MS; color: #FF5733;'>Welcome to AlgoTrade</h1>",
    unsafe_allow_html=True
)

st.sidebar.markdown(
    """
    <hr style='border: 2px solid white;'>
    """,
    unsafe_allow_html=True
)



connect_ = st.sidebar.button('connect' , use_container_width=True)
mode = st.sidebar.radio(':red[***Select the Mode of trading:***]',['***Simulation***','***Live***'])

def countdown(seconds):
    for i in range(seconds, 0, -1):
        timer_placeholder.text(f"Time remaining: {i} seconds")
        time.sleep(1)
    timer_placeholder.text("Time's up!")

# Create a placeholder for the countdown timer
timer_placeholder = st.empty()

# Set the countdown duration (e.g., 10 seconds)
countdown_duration = 100000

# Start the countdown
countdown(countdown_duration)
