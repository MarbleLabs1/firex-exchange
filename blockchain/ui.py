import streamlit as st
import requests
import json
import pandas as pd
import websockets
import asyncio
from datetime import datetime
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# Configure page
st.set_page_config(
    page_title="Marble DEX",
    page_icon="💎",
    layout="wide"
)

# API configuration
API_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/orderbook"

# Custom CSS including new Marble Mind elements
st.markdown("""
    <style>
    .main {
        background-color: #1a1b23;
    }
    .stButton>button {
        background-color: #FF0000;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        border: none;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #cc0000;
        box-shadow: 0 0 10px rgba(255, 0, 0, 0.3);
    }
    .dex-container {
        background: linear-gradient(135deg, #1E1E2E 0%, #2A2A3C 100%);
        padding: 2rem;
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }
    .mind-section {
        border: 1px solid #FF0000;
        border-radius: 12px;
        padding: 1.5rem;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(255, 0, 0, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(255, 0, 0, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 0, 0, 0); }
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
if 'orderbook_data' not in st.session_state:
    st.session_state.orderbook_data = {"bids": [], "asks": []}
if 'last_price' not in st.session_state:
    st.session_state.last_price = None

def load_dex_config():
    """Load DEX configuration"""
    try:
        response = requests.get(f"{API_URL}/dex_config")
        return response.json()
    except:
        return {
            "dex": "Marble DEX",
            "color": "#FF0000",
            "logo": "/static/logo.png",
            "pairs": ["MARBLE/USDT", "ETH/USDT"]
        }

def get_ai_predictions():
    """Get AI predictions from the API"""
    try:
        response = requests.get(f"{API_URL}/ia_predict")
        return response.json()
    except:
        return {}

def render_header():
    """Render the header with branding"""
    col1, col2 = st.columns([1, 3])
    with col1:
        st.image("static/logo.png", width=100)
    with col2:
        st.title("Marble DEX")
        st.markdown('<div class="mind-section">🧠 Marble Mind Active</div>', 
                  unsafe_allow_html=True)

def render_sidebar():
    """Render sidebar with wallet connection"""
    with st.sidebar:
        st.markdown("### Wallet")
        if st.button("Connect Wallet"):
            st.session_state.wallet_connected = True
        
        if 'wallet_connected' in st.session_state and st.session_state.wallet_connected:
            st.success("Connected: 0x1234...5678")
            st.metric("Balance", "1000 MARBLE")
            st.metric("USDT Balance", "500 USDT")

def render_swap_tab():
    """Render the swap interface"""
    st.markdown('<div class="dex-container">', unsafe_allow_html=True)
    st.subheader("Swap Tokens")
    
    config = load_dex_config()
    pairs = config.get("pairs", ["MARBLE/USDT"])
    
    col1, col2 = st.columns(2)
    with col1:
        token_pair = st.selectbox("Select Pair", pairs)
        from_token, to_token = token_pair.split("/")
        
    amount = st.number_input(f"Amount {from_token}", min_value=0.0, value=1.0)
    
    # Get AI predictions for selected pair
    predictions = get_ai_predictions()
    if token_pair in predictions:
        pred = predictions[token_pair]
        st.info(f"🧠 Marble Mind Prediction (1h): {pred['prediction_1h']} ({pred['confidence']*100:.1f}% confidence)")
    
    if st.button("Swap"):
        if 'wallet_connected' in st.session_state and st.session_state.wallet_connected:
            st.success(f"Swapped {amount} {from_token} to {amount} {to_token}")
        else:
            st.error("Please connect your wallet first")
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_validate_tab():
    """Render the block validation interface"""
    st.markdown('<div class="dex-container">', unsafe_allow_html=True)
    st.subheader("Block Validation")
    
    block_id = st.text_input("Block ID")
    validation_level = st.slider("Validation Level", 1, 3, 2)
    
    if st.button("Validate Block"):
        if block_id:
            with st.spinner("Validating block..."):
                try:
                    response = requests.post(
                        f"{API_URL}/validate_block",
                        json={
                            "block_id": block_id,
                            "validate_transactions": True,
                            "validation_level": validation_level,
                            "compute_tokens": 100
                        }
                    )
                    result = response.json()
                    st.json(result)
                except:
                    st.error("Error validating block")
        else:
            st.error("Please enter a block ID")
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_marble_mind_tab():
    """Render the Marble Mind AI analytics tab"""
    st.markdown('<div class="dex-container">', unsafe_allow_html=True)
    st.subheader("🧠 Marble Mind Analytics")
    
    predictions = get_ai_predictions()
    
    # Create price prediction charts
    for pair, pred in predictions.items():
        st.markdown(f"### {pair} Analysis")
        
        # Price chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[datetime.now(), datetime.now().replace(hour=datetime.now().hour+1)],
            y=[pred['current'], pred['prediction_1h']],
            mode='lines+markers',
            name='Price Prediction'
        ))
        fig.update_layout(
            title=f"{pair} Price Prediction",
            xaxis_title="Time",
            yaxis_title="Price",
            template="plotly_dark"
        )
        st.plotly_chart(fig)
        
        # Confidence indicator
        st.progress(pred['confidence'])
        st.markdown(f"Prediction Confidence: {pred['confidence']*100:.1f}%")
        
        # Trading signals
        if pred['prediction_1h'] > pred['current']:
            st.success("🔼 Bullish Signal")
        else:
            st.error("🔽 Bearish Signal")
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_orderbook_tab():
    """Render the order book with real-time updates"""
    st.markdown('<div class="dex-container">', unsafe_allow_html=True)
    st.subheader("Order Book")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Bids")
        if st.session_state.orderbook_data["bids"]:
            bids_df = pd.DataFrame(st.session_state.orderbook_data["bids"])
            st.dataframe(bids_df)
        else:
            st.info("No bids available")
            
    with col2:
        st.markdown("### Asks")
        if st.session_state.orderbook_data["asks"]:
            asks_df = pd.DataFrame(st.session_state.orderbook_data["asks"])
            st.dataframe(asks_df)
        else:
            st.info("No asks available")
    
    st.markdown('</div>', unsafe_allow_html=True)

async def update_orderbook():
    """WebSocket connection for real-time order book updates"""
    async with websockets.connect(WS_URL) as websocket:
        while True:
            try:
                data = await websocket.recv()
                st.session_state.orderbook_data = json.loads(data)
                st.experimental_rerun()
            except Exception as e:
                st.error(f"WebSocket error: {e}")
                break

def main():
    """Main application"""
    render_header()
    render_sidebar()
    
    # Auto-refresh for real-time updates
    st_autorefresh(interval=1000, key="orderbook_refresh")
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Swap", "Validate", "Order Book", "🧠 Marble Mind"
    ])
    
    with tab1:
        render_swap_tab()
        
    with tab2:
        render_validate_tab()
        
    with tab3:
        render_orderbook_tab()
        
    with tab4:
        render_marble_mind_tab()

if __name__ == "__main__":
    main()
    # Start WebSocket connection in a separate thread
    asyncio.run(update_orderbook())

import streamlit as st
import requests
import json
import pandas as pd

# Configure page
st.set_page_config(
    page_title="Marble DEX",
    page_icon="💎",
    layout="wide"
)

# Custom CSS with Raydium-like styling
st.markdown("""
    <style>
    .main {
        background-color: #1a1b23;
    }
    .stButton>button {
        background-color: #FF0000;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        border: none;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #cc0000;
        box-shadow: 0 0 10px rgba(255, 0, 0, 0.3);
    }
    .swap-container {
        background-color: #282932;
        padding: 2rem;
        border-radius: 16px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# API endpoint
API_URL = "http://localhost:8000"

def load_dex_config():
    """Load DEX configuration from the API"""
    try:
        response = requests.get(f"{API_URL}/dex_config")
        return response.json()
    except:
        return {
            "dex": "Marble DEX",
            "color": "#FF0000",
            "logo": "/static/logo.png",
            "pairs": ["MARBLE/USDT", "ETH/USDT"]
        }

def get_orderbook_data():
    """Get orderbook data from the API"""
    try:
        response = requests.get(f"{API_URL}/trade")
        return response.json()
    except:
        return {"bids": [], "asks": []}

# Header
def render_header():
    col1, col2 = st.columns([1, 3])
    with col1:
        st.image("static/logo.png", width=100)
    with col2:
        st.title("Marble DEX")

# Sidebar
def render_sidebar():
    with st.sidebar:
        st.markdown("### Wallet")
        if st.button("Connect Wallet"):
            st.session_state.wallet_connected = True
        
        if 'wallet_connected' in st.session_state and st.session_state.wallet_connected:
            st.success("Connected: 0x1234...5678")
            st.metric("Balance", "1000 MARBLE")
            st.metric("USDT Balance", "500 USDT")

# Swap Tab
def render_swap_tab():
    st.markdown('<div class="swap-container">', unsafe_allow_html=True)
    st.subheader("Swap Tokens")
    
    # Get token pairs from config
    config = load_dex_config()
    pairs = config.get("pairs", ["MARBLE/USDT"])
    
    col1, col2 = st.columns(2)
    with col1:
        token_pair = st.selectbox("Select Pair", pairs)
        from_token, to_token = token_pair.split("/")
        
    amount = st.number_input(f"Amount {from_token}", min_value=0.0, value=1.0)
    
    if st.button("Swap"):
        if 'wallet_connected' in st.session_state and st.session_state.wallet_connected:
            st.success(f"Swapped {amount} {from_token} to {amount} {to_token}")
        else:
            st.error("Please connect your wallet first")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Validate Tab
def render_validate_tab():
    st.markdown('<div class="swap-container">', unsafe_allow_html=True)
    st.subheader("Block Validation")
    
    block_id = st.text_input("Block ID")
    validation_level = st.slider("Validation Level", 1, 3, 2)
    
    if st.button("Validate Block"):
        if block_id:
            with st.spinner("Validating block..."):
                try:
                    response = requests.post(
                        f"{API_URL}/validate_block",
                        json={
                            "block_id": block_id,
                            "validate_transactions": True,
                            "validation_level": validation_level,
                            "compute_tokens": 100
                        }
                    )
                    result = response.json()
                    st.json(result)
                except:
                    st.error("Error validating block")
        else:
            st.error("Please enter a block ID")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Order Book Tab
def render_orderbook_tab():
    st.markdown('<div class="swap-container">', unsafe_allow_html=True)
    st.subheader("Order Book")
    
    data = get_orderbook_data()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Bids")
        if data["bids"]:
            bids_df = pd.DataFrame(data["bids"])
            st.dataframe(bids_df)
        else:
            st.info("No bids available")
            
    with col2:
        st.markdown("### Asks")
        if data["asks"]:
            asks_df = pd.DataFrame(data["asks"])
            st.dataframe(asks_df)
        else:
            st.info("No asks available")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Main
def main():
    render_header()
    render_sidebar()
    
    tab1, tab2, tab3 = st.tabs(["Swap", "Validate", "Order Book"])
    
    with tab1:
        render_swap_tab()
        
    with tab2:
        render_validate_tab()
        
    with tab3:
        render_orderbook_tab()

if __name__ == "__main__":
    main()

