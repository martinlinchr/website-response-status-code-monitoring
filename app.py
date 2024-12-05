import streamlit as st
import sqlite3
import requests
import pandas as pd
from datetime import datetime
import time
import smtplib
from email.message import EmailMessage
import statistics

HTTP_CODES = {
    100: "Continue", 101: "Switching protocols", 102: "Processing", 103: "Early Hints",
    200: "OK", 201: "Created", 202: "Accepted", 203: "Non-Authoritative Information",
    204: "No Content", 205: "Reset Content", 206: "Partial Content", 207: "Multi-Status",
    208: "Already Reported", 226: "IM Used",
    300: "Multiple Choices", 301: "Moved Permanently", 302: "Found",
    303: "See Other", 304: "Not Modified", 305: "Use Proxy", 307: "Temporary Redirect",
    308: "Permanent Redirect",
    400: "Bad Request", 401: "Unauthorized", 402: "Payment Required", 403: "Forbidden",
    404: "Not Found", 405: "Method Not Allowed", 406: "Not Acceptable",
    407: "Proxy Authentication Required", 408: "Request Timeout", 409: "Conflict",
    410: "Gone", 411: "Length Required", 412: "Precondition Failed",
    413: "Payload Too Large", 414: "URI Too Long", 415: "Unsupported Media Type",
    416: "Range Not Satisfiable", 417: "Expectation Failed", 418: "I'm a Teapot",
    421: "Misdirected Request", 422: "Unprocessable Entity", 423: "Locked",
    424: "Failed Dependency", 425: "Too Early", 426: "Upgrade Required",
    428: "Precondition Required", 429: "Too Many Requests",
    431: "Request Header Fields Too Large", 451: "Unavailable For Legal Reasons",
    500: "Internal Server Error", 501: "Not Implemented", 502: "Bad Gateway",
    503: "Service Unavailable", 504: "Gateway Timeout",
    505: "HTTP Version Not Supported", 506: "Variant Also Negotiates",
    507: "Insufficient Storage", 508: "Loop Detected", 510: "Not Extended",
    511: "Network Authentication Required"
}

def init_db():
    conn = sqlite3.connect('monitor.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS domains
                 (url TEXT PRIMARY KEY, 
                  speed_threshold REAL DEFAULT 2.0,
                  enabled INTEGER DEFAULT 1)''')
    conn.commit()
    return conn

def add_domain(conn, url, speed_threshold=2.0):
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO domains (url, speed_threshold) VALUES (?, ?)',
              (url, speed_threshold))
    conn.commit()

def get_domains(conn):
    c = conn.cursor()
    c.execute('SELECT url, speed_threshold FROM domains WHERE enabled = 1')
    return c.fetchall()

def remove_domain(conn, url):
    c = conn.cursor()
    c.execute('DELETE FROM domains WHERE url = ?', (url,))
    conn.commit()

def get_status_description(code):
    return HTTP_CODES.get(code, "Unknown Status Code")

def send_alert(url: str, status_code: int, speed: float = None, error: str = None):
    status_desc = get_status_description(status_code)
    smtp_server = st.secrets["email"]["smtp_server"]
    smtp_port = st.secrets["email"]["smtp_port"]
    sender_email = st.secrets["email"]["sender_email"]
    password = st.secrets["email"]["sender_password"]
    recipient = st.secrets["email"]["recipient_email"]

    msg = EmailMessage()
    msg.set_content(f"""
    Alert for {url}
    Status Code: {status_code} - {status_desc}
    Speed: {f'{speed:.2f}s' if speed else 'N/A'}
    Error: {error if error else 'N/A'}
    Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """)

    msg['Subject'] = f'Website Alert - {url} ({status_code} {status_desc})'
    msg['From'] = sender_email
    msg['To'] = recipient

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, password)
        server.send_message(msg)

def check_website(url: str, speed_threshold: float) -> dict:
    speeds = []
    for _ in range(3):
        try:
            start = time.time()
            response = requests.get(url, timeout=10)
            speed = time.time() - start
            speeds.append(speed)
        except:
            continue
    
    avg_speed = statistics.mean(speeds) if speeds else None
    
    try:
        response = requests.get(url, timeout=10)
        status_desc = get_status_description(response.status_code)
        
        result = {
            'URL': url,
            'Status Code': f'{response.status_code} - {status_desc}',
            'Speed (s)': round(avg_speed, 2) if avg_speed else None,
            'Last Checked': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if response.status_code != 200 or (avg_speed and avg_speed > speed_threshold):
            send_alert(url, response.status_code, avg_speed)
            
        return result
        
    except requests.RequestException as e:
        send_alert(url, 0, error=str(e))
        return {
            'URL': url,
            'Status Code': 'Error - Connection Failed',
            'Speed (s)': None,
            'Last Checked': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Error': str(e)
        }

# Streamlit UI
st.title('Website Monitor')

# Email setup form
with st.expander("Email Settings"):
    if "email" not in st.secrets:
        st.warning("Email settings not configured!")
        smtp_server = st.text_input("SMTP Server", "smtp.gmail.com")
        smtp_port = st.number_input("SMTP Port", value=587)
        sender_email = st.text_input("Sender Email")
        sender_password = st.text_input("App Password", type="password")
        recipient_email = st.text_input("Recipient Email")
        
        if st.button("Save Email Settings"):
            st.secrets["email"] = {
                "smtp_server": smtp_server,
                "smtp_port": smtp_port,
                "sender_email": sender_email,
                "sender_password": sender_password,
                "recipient_email": recipient_email
            }
    else:
        st.success("Email configured!")

# Initialize database
conn = init_db()

# Website management
col1, col2 = st.columns(2)
with col1:
    new_website = st.text_input('Add website (include https://)')
    speed_threshold = st.number_input('Speed Alert Threshold (seconds)', value=2.0, step=0.1)
    if st.button('Add') and new_website:
        add_domain(conn, new_website, speed_threshold)
        st.success(f'Added {new_website}')

# Display current domains
st.write("Current domains in database:")
domains = get_domains(conn)
st.write(domains)

# Display monitoring results
if domains:
    results = []
    for url, threshold in domains:
        result = check_website(url, threshold)
        results.append(result)
    
    df = pd.DataFrame(results)
    styled_df = df.style.applymap(lambda v: 'color: red' if 'Error' in str(v) else 'color: green')
    st.dataframe(styled_df, use_container_width=True)
    
    # Remove website option
    to_remove = st.selectbox('Select website to remove', [d[0] for d in domains])
    if st.button('Remove'):
        remove_domain(conn, to_remove)
        st.experimental_rerun()

# Auto-refresh
check_interval = st.number_input('Check Interval (minutes)', value=15, min_value=1)
if st.checkbox(f'Auto-refresh ({check_interval}min)'):
    time.sleep(check_interval * 60)
    st.experimental_rerun()
