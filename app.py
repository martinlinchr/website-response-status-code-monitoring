import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

def check_website(url: str) -> dict:
    try:
        response = requests.get(url, timeout=10)
        return {
            'URL': url,
            'Status Code': response.status_code,
            'Status': 'OK' if response.status_code == 200 else 'Error',
            'Last Checked': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Response Time (s)': round(response.elapsed.total_seconds(), 2)
        }
    except requests.RequestException as e:
        return {
            'URL': url,
            'Status Code': None,
            'Status': 'Error',
            'Last Checked': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Response Time (s)': None,
            'Error': str(e)
        }

# App title and description
st.title('Website Status Monitor')
st.write('Monitor website availability and response times')

# Input for new websites
new_website = st.text_input('Add a website to monitor (include https://)')
if new_website:
    if 'websites' not in st.session_state:
        st.session_state.websites = set()
    st.session_state.websites.add(new_website)

# Display and manage monitored websites
if 'websites' in st.session_state and st.session_state.websites:
    st.subheader('Monitored Websites')
    
    # Create columns for the status board
    results = []
    for url in st.session_state.websites:
        result = check_website(url)
        results.append(result)
    
    # Convert results to DataFrame
    df = pd.DataFrame(results)
    
    # Style the DataFrame based on status
    def color_status(val):
        color = 'green' if val == 'OK' else 'red'
        return f'color: {color}'
    
    styled_df = df.style.applymap(color_status, subset=['Status'])
    st.dataframe(styled_df, use_container_width=True)

    # Remove website option
    if st.button('Remove All Websites'):
        st.session_state.websites.clear()

# Auto-refresh option
auto_refresh = st.checkbox('Auto-refresh (30 seconds)')
if auto_refresh:
    time.sleep(30)
    st.experimental_rerun()
