import streamlit as st
import fyers_api
import pandas as pd
import numpy as np


# Title of the app
st.title("Simple Streamlit App")

# Text input field
user_input = st.text_input("Enter some text:")

# Button to display the input text
if st.button("Display Text"):
    st.write("You entered:", user_input)
