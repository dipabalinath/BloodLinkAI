import streamlit as st

def load_custom_css():
    """Injects custom CSS to modernize the UI/UX."""
    custom_css = """
    <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        
        /* Global Typography & Background */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            background-color: #F6F8FB;
        }

        /* Adjust standard container width */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
           
        }

        /* Metric Cards overriding */
        div[data-testid="metric-container"] {
            background-color: white;
            border: 1px solid #E0E5EC;
            padding: 1.25rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
        }
        div[data-testid="metric-container"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }
        div[data-testid="metric-container"] > div {
            color: #1565C0; /* Secondary medical blue for metric labels */
            font-weight: 600;
        }

        /* Primary Button Overrides (Blood Red) */
        .stButton>button[kind="primary"] {
            background-color: #C62828 !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.5rem 1rem !important;
            font-weight: 600 !important;
            transition: all 0.2s ease;
        }
        .stButton>button[kind="primary"]:hover {
            background-color: #B71C1C !important;
            box-shadow: 0 4px 12px rgba(198, 40, 40, 0.3);
        }

        /* Secondary Button Overrides */
        .stButton>button[kind="secondary"] {
            background-color: white !important;
            color: #1565C0 !important;
            border: 1px solid #1565C0 !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease;
        }
        .stButton>button[kind="secondary"]:hover {
            background-color: #F8FBFF !important;
            border-color: #0D47A1 !important;
            color: #0D47A1 !important;
        }

        /* Custom Badges/Alerts inside Markdown */
        .badge-live {
            background: #2E7D32;
            color: white;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            animation: pulse-green 2s infinite;
        }
        
        .alert-card-red {
            background: #FFEBEE;
            border-left: 4px solid #C62828;
            padding: 1rem;
            border-radius: 0 8px 8px 0;
            margin-bottom: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        /* Expandable Panels (st.expander) */
        .streamlit-expanderHeader {
            font-weight: 600 !important;
            color: #1565C0 !important;
            background-color: white;
            border-radius: 8px;
            border: 1px solid #E0E5EC;
        }
        
        /* Animations */
        @keyframes pulse-green {
            0% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0.4); }
            70% { box-shadow: 0 0 0 6px rgba(46, 125, 50, 0); }
            100% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0); }
        }
        
        @keyframes pulse-red {
            0% { box-shadow: 0 0 0 0 rgba(198, 40, 40, 0.4); }
            70% { box-shadow: 0 0 0 8px rgba(198, 40, 40, 0); }
            100% { box-shadow: 0 0 0 0 rgba(198, 40, 40, 0); }
        }
        
        .pulse-danger {
            animation: pulse-red 2s infinite;
            border-radius: 12px;
        }
        
        /* Header typography */
        h1, h2, h3 {
            color: #1A1A1A;
            font-weight: 700;
        }
        
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: transparent;
            border-radius: 4px 4px 0px 0px;
            gap: 1px;
            padding-top: 10px;
            padding-bottom: 10px;
            font-weight: 600;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
