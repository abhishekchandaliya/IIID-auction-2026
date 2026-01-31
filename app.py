import streamlit as st
import pandas as pd
import os
import time
import base64
import json
from datetime import datetime

# ==========================================
# 1. CONFIGURATION & CONSTANTS
# ==========================================

st.set_page_config(
    page_title="IIID Sports Auction 2026",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# FILES FOR PERSISTENCE
HISTORY_FILE = "auction_data_v4.csv"
CONFIG_FILE = "auction_config_v4.json"

TEAM_NAMES = [
    "Aditya Avengers",
    "Alfen Royals",
    "Lantern Legends",
    "Primark Superkings",
    "Sai Kripa Soldiers",
    "Taluka Fighters"
]

# Default Rules
DEFAULT_CONFIG = {
    "purse_limit": 10000,
    "max_squad_size": 25,
    "base_price": 10,
    "category_limits": {
        "Cricket": {"A": 5, "B": 5, "C": 5},
        "Badminton": {"A": 5, "B": 5, "C": 5},
        "TT": {"A": 5, "B": 5, "C": 5}
    }
}

# ==========================================
# 2. PERSISTENCE FUNCTIONS
# ==========================================

def save_data():
    """Force saves the player dataframe to disk."""
    if 'players' in st.session_state and not st.session_state.players.empty:
        st.session_state.players.to_csv(HISTORY_FILE, index=False)

def load_data_from_history():
    """Tries to load previous session data."""
    if os.path.exists(HISTORY_FILE):
        return pd.read_csv(HISTORY_FILE)
    return pd.DataFrame()

def save_config():
    """Saves rules to disk."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(st.session_state.config, f)

def load_config():
    """Loads rules from disk."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return DEFAULT_CONFIG

# ==========================================
# 3. INITIALIZATION
# ==========================================

def init_session_state():
    # 1. Load Config
    if 'config' not in st.session_state:
        st.session_state.config = load_config()

    # 2. Load Data
    if 'players' not in st.session_state:
        history = load_data_from_history()
        if not history.empty:
            st.session_state.players = history
        else:
            st.session_state.players = pd.DataFrame(columns=[
                'ID', 'Name', 'Team', 'Price', 'Cricket', 'Badminton', 'TT', 'CaptainFor', 'ContactNo'
            ])
            
    if 'activity_log' not in st.session_state:
        st.session_state.activity_log = []
        
    if 'current_player_id' not in st.session_state:
        st.session_state.current_player_id = None

    if 'admin_mode' not in st.session_state:
        st.session_state.admin_mode = False

# ==========================================
# 4. DATA PROCESSING
# ==========================================

def process_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            
            # Cleaning Headers
            df.columns = df.columns.str.strip()
            
            # Intelligent Renaming
            rename_map = {}
            for col in df.columns:
                c = col.lower().replace(' ', '')
                if c in ['playername', 'name', 'player']: rename_map[col] = 'Name'
                elif 'cric' in c: rename_map[col] = 'Cricket'
                elif 'bad' in c: rename_map[col] = 'Badminton'
                elif 'tt' in c or 'table' in c: rename_map[col] = 'TT'
                elif 'contact' in c: rename_map[col] = 'ContactNo'
            
            df.rename(columns=rename_map, inplace=True)

            # Add Missing Columns
            if 'ID' not in df.columns: df['ID'] = range(1, len(df) + 1)
            for col in ['Team', 'Price', 'CaptainFor', 'ContactNo']:
                if col not in df.columns: df[col] = None

            # Normalize Grades
            for sport in ['Cricket', 'Badminton', 'TT']:
                if sport in df.columns:
                    df[sport] = df[sport].fillna('0').astype(str).str.upper().str.strip()
                    df[sport] = df[sport].apply(lambda x: x if x in ['A', 'B', 'C'] else '0')
                else:
                    df[sport] = '0'

            df['Price'] = df['Price'].fillna(0).astype(int)

            st.session_state.players = df
            save_data() # IMMEDIATE SAVE
            st.success(f"✅ Database Built! {len(df)} players ready.")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

def get_player_image(player_name):
    base_path = "photos"
    if not os.path.exists(base_path): return None
    
    target = str(player_name).strip().lower()
    for f in os.listdir(base_path):
        if os.path.splitext(f)[0].strip().lower() == target:
            return os.path.join(base_path, f)
    
    # Fallback to default
    default = os.path.join(base_path, "default_player.png")
    return default if os.path.exists(default) else None

def calculate_stats():
    df = st.session_state.players
    cfg = st.session_state.config
    stats = []
    
    for team in TEAM_NAMES:
        t_rows = df[df['Team'] == team]
        count = len(t_rows)
        spent = t_rows['Price'].sum()
        
        # Categorical Counts
        cric = len(t_rows[t_rows['Cricket'] != '0'])
        bad = len(t_rows[t_rows['Badminton'] != '0'])
        tt = len(t_rows[t_rows['TT'] != '0'])
        
        # Money Math
        avail = cfg['purse_limit'] - spent
        # Reserve for empty slots
        empty = max(0, cfg['max_squad_size'] - count)
        reserve = empty * cfg['base_price']
        disposable = avail - reserve
        
        stats.append({
            "Name": team, "Count": count, "Spent": spent, 
            "Available": avail, "Disposable": disposable,
            "Cricket": cric, "Badminton": bad, "TT": tt,
            "Cric_A": len(t_rows[t_rows['Cricket'] == 'A']),
            "Cric_B": len(t_rows[t_rows['Cricket'] == 'B']),
            "Cric_C": len(t_rows[t_rows['Cricket'] == 'C']),
            "Bad_A": len(t_rows[t_rows['Badminton'] == 'A']),
            "Bad_B": len(t_rows[t_rows['Badminton'] == 'B']),
            "Bad_C": len(t_rows[t_rows['Badminton'] == 'C']),
            "TT_A": len(t_rows[t_rows['TT'] == 'A']),
            "TT_B": len(t_rows[t_rows['TT'] == 'B']),
            "TT_C": len(t_rows[t_rows['TT'] == 'C']),
        })
    return pd.DataFrame(stats)

# ==========================================
# 5. UI COMPONENTS
# ==========================================

st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: 900; background: -webkit-linear-gradient(left, #ffffff, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .projector-text { text-shadow: 0 0 20px rgba(255,255,255,0.8); }
    .badge { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8rem; margin-right: 5px; }
    .badge-cric { background: #1e40af; color: white; }
    .badge-bad { background: #065f46; color: white; }
    .badge-tt { background: #9a3412; color: white; }
    .block-container { padding-top: 1rem; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

def render_dashboard():
    st.markdown('<div class="main-header">Team Standings</div>', unsafe_allow_html=True)
    
    # Live Auction Card
    if st.session_state.current_player_id:
        try:
            p = st.session_state.players[st.session_state.players['ID'] == st.session_state.current_player_id].iloc[0]
            st.info(f"🔥 **NOW ON AUCTION:** {p['Name']} (Base: {st.session_state.config['base_price']}L)")
        except: pass

    stats = calculate_stats()
    
    # Top Metrics
    total_sold = stats['Count'].sum()
    total_slots = len(TEAM_NAMES) * st.session_state.config['max_squad_size']
    remaining = total_slots - total_sold
    highest = st.session_state.players['Price'].max()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Sold", int(total_sold))
    c2.metric("Remaining Slots", int(remaining))
    c3.metric("Highest Bid", f"₹{highest}L")
    
    # Main Table
    disp = stats[['Name', 'Disposable', 'Count', 'Cricket', 'Badminton', 'TT']].copy()
    disp.columns = ['Team', 'Purse Left', 'Size', '🏏 Cric', '🏸 Bad', '🏓 TT']
    
    st.dataframe(
        disp.style.background_gradient(subset=['Purse Left'], cmap="Greens"),
        use_container_width=True, hide_index=True, height=280
    )
    
    with st.expander("Detailed Category Breakdown"):
        st.dataframe(stats, use_container_width=True)

def render_auction():
    st.markdown('<div class="main-header">Auction Console</div>', unsafe_allow_html=True)
    
    df = st.session_state.players
    unsold = df[df['Team'].isna()]
    
    if unsold.empty:
        st.success("🎉 AUCTION COMPLETE!")
        return

    # 1. Selector
    c1, c2 = st.columns([1, 3])
    with c1:
        st.markdown("### 🎲 Spin")
        sport = st.selectbox("Sport", ["All", "Cricket", "Badminton", "TT"])
        grade = st.selectbox("Grade", ["All", "A", "B", "C"])
        
        if st.button("🎰 SPIN", type="primary", use_container_width=True):
            pool = unsold
            if sport != "All": pool = pool[pool[sport] != '0']
            if grade != "All":
                if sport == "All": pool = pool[(pool['Cricket']==grade)|(pool['Badminton']==grade)|(pool['TT']==grade)]
                else: pool = pool[pool[sport] == grade]
            
            if not pool.empty:
                sel = pool.sample(1).iloc[0]
                st.session_state.current_player_id = sel['ID']
                st.rerun()
            else:
                st.warning("No players found.")

    with c2:
        st.markdown("### 🔍 Search")
        if 'Name' in unsold.columns:
            search = st.selectbox("Find", unsold['Name'].tolist(), index=None, placeholder="Type name...")
            if search:
                pid = unsold[unsold['Name'] == search].iloc[0]['ID']
                if st.session_state.current_player_id != pid:
                    st.session_state.current_player_id = pid
                    st.rerun()

    st.divider()

    # 2. Hero Section
    if st.session_state.current_player_id:
        pid = st.session_state.current_player_id
        # Reload player from fresh dataframe
        try:
            p = df[df['ID'] == pid].iloc[0]
        except:
            st.session_state.current_player_id = None
            st.rerun()
            return

        hc1, hc2 = st.columns([1, 3])
        with hc1:
            img = get_player_image(p['Name'])
            if img: st.image(img, width=250)
            else: st.markdown("<h1>👤</h1>", unsafe_allow_html=True)
        
        with hc2:
            st.markdown(f"<h1 class='projector-text'>{p['Name']}</h1>", unsafe_allow_html=True)
            tags = ""
            if p['Cricket']!='0': tags+=f"<span class='badge badge-cric'>CRIC: {p['Cricket']}</span>"
            if p['Badminton']!='0': tags+=f"<span class='badge badge-bad'>BAD: {p['Badminton']}</span>"
            if p['TT']!='0': tags+=f"<span class='badge badge-tt'>TT: {p['TT']}</span>"
            st.markdown(tags, unsafe_allow_html=True)
            
            # 3. Bidding
            if st.session_state.admin_mode:
                st.write("---")
                stats = calculate_stats()
                valid = stats[stats['Disposable'] >= st.session_state.config['base_price']]
                opts = {r['Name']: f"{r['Name']} (₹{r['Disposable']}L)" for _, r in valid.iterrows()}
                
                b1, b2, b3 = st.columns([2, 1, 1])
                with b1: win_team = st.selectbox("Team", opts.keys(), format_func=lambda x: opts[x])
                with b2: price = st.number_input("Price", value=st.session_state.config['base_price'], step=5)
                with b3:
                    st.write("")
                    st.write("")
                    if st.button("🔨 SOLD", type="primary", use_container_width=True):
                        # Validation
                        t_stat = stats[stats['Name'] == win_team].iloc[0]
                        max_bid = t_stat['Disposable'] + st.session_state.config['base_price']
                        
                        if price > max_bid:
                            st.error(f"Funds exceeded! Max: {max_bid}")
                        else:
                            # Save
                            idx = df.index[df['ID'] == pid].tolist()[0]
                            st.session_state.players.at[idx, 'Team'] = win_team
                            st.session_state.players.at[idx, 'Price'] = price
                            save_data() # FORCE SAVE
                            
                            st.session_state.activity_log.insert(0, f"SOLD: {p['Name']} to {win_team} ({price})")
                            st.balloons()
                            st.session_state.current_player_id = None
                            time.sleep(1)
                            st.rerun()

                if st.button("Pass"):
                    st.session_state.current_player_id = None
                    st.rerun()
            else:
                st.warning("Admin Login Required to Bid")

def render_teams():
    st.markdown('<div class="main-header">Team Rosters</div>', unsafe_allow_html=True)
    df = st.session_state.players
    
    # Recent Activity - SAFE MODE FIXED
    if st.session_state.activity_log:
        safe_logs = []
        for log in st.session_state.activity_log[:3]:
            # Check if log is a dictionary (from old version) or string (new version)
            if isinstance(log, dict):
                safe_logs.append(f"{log.get('time','')}: {log.get('message','')}")
            else:
                safe_logs.append(str(log))
        
        st.caption("Recent Activity: " + " | ".join(safe_logs))
        
    for team in TEAM_NAMES:
        t_df = df[df['Team'] == team]
        count = len(t_df)
        with st.expander(f"{team} ({count})"):
            if not t_df.empty:
                st.dataframe(t_df[['Name', 'Price', 'Cricket', 'Badminton', 'TT', 'CaptainFor']], hide_index=True, use_container_width=True)
            else:
                st.write("No players.")

def render_settings():
    st.markdown('<div class="main-header">Settings</div>', unsafe_allow_html=True)
    
    if not st.session_state.admin_mode:
        pwd = st.text_input("Admin Password", type="password")
        if st.button("Login"):
            if pwd == "ABCD2026":
                st.session_state.admin_mode = True
                st.rerun()
        return

    t1, t2, t3, t4 = st.tabs(["Data", "Rules", "Captains", "Correction"])
    
    with t1:
        st.subheader("Data Management")
        up = st.file_uploader("Upload CSV", type=['csv'])
        if up: process_uploaded_file(up)
        
        st.divider()
        if st.button("🗑️ Factory Reset (Clear All Data)", type="primary"):
            if os.path.exists(HISTORY_FILE): os.remove(HISTORY_FILE)
            st.session_state.players = pd.DataFrame()
            st.session_state.activity_log = []
            st.success("Reset Done.")
            time.sleep(1)
            st.rerun()
            
        st.divider()
        # DOWNLOAD BUTTON
        if not st.session_state.players.empty:
            csv = st.session_state.players.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="final_auction_results.csv">📥 Download Final Results (CSV)</a>'
            st.markdown(href, unsafe_allow_html=True)

    with t2:
        st.subheader("Tournament Rules")
        c1, c2, c3 = st.columns(3)
        np = c1.number_input("Purse", value=st.session_state.config['purse_limit'])
        ns = c2.number_input("Squad Size", value=st.session_state.config['max_squad_size'])
        nb = c3.number_input("Base Price", value=st.session_state.config['base_price'])
        
        if st.button("💾 Save Rules"):
            st.session_state.config['purse_limit'] = np
            st.session_state.config['max_squad_size'] = ns
            st.session_state.config['base_price'] = nb
            save_config() # PERSIST CONFIG
            st.success("Rules Saved!")

    with t3:
        st.subheader("Assign Captains")
        unsold = st.session_state.players[st.session_state.players['Team'].isna()]
        if not unsold.empty:
            c_p = st.selectbox("Select Player", unsold['Name'].unique())
            c_t = st.selectbox("Select Team", TEAM_NAMES)
            c_s = st.selectbox("Sport Category", ["Cricket", "Badminton", "TT"])
            c_price = st.number_input("Captain Price", 0)
            
            if st.button("Assign Captain"):
                idx = st.session_state.players.index[st.session_state.players['Name'] == c_p].tolist()[0]
                st.session_state.players.at[idx, 'Team'] = c_t
                st.session_state.players.at[idx, 'Price'] = c_price
                st.session_state.players.at[idx, 'CaptainFor'] = c_s
                save_data()
                st.success("Captain Assigned!")
                st.rerun()

    with t4:
        st.subheader("Correction (Unsell)")
        sold = st.session_state.players[st.session_state.players['Team'].notna()]
        if not sold.empty:
            p_fix = st.selectbox("Select Sold Player", sold['Name'].unique())
            if st.button("❌ Unsell (Revert)"):
                idx = st.session_state.players.index[st.session_state.players['Name'] == p_fix].tolist()[0]
                st.session_state.players.at[idx, 'Team'] = None
                st.session_state.players.at[idx, 'Price'] = 0
                st.session_state.players.at[idx, 'CaptainFor'] = None
                save_data()
                st.success("Reverted!")
                st.rerun()

# ==========================================
# MAIN
# ==========================================

def developer_profile():
    with st.sidebar:
        st.markdown("### 👨‍💻 Developer")
        try:
            if 'Name' in st.session_state.players.columns:
                dev = st.session_state.players[st.session_state.players['Name'].str.contains("Abhishek", case=False, na=False)]
                if not dev.empty:
                    d = dev.iloc[0]
                    st.success(f"Abhishek Chandaliya\n\nTeam: {d['Team'] if pd.notna(d['Team']) else 'Unsold'}")
                else: st.write("Abhishek Chandaliya")
        except: pass

def main():
    init_session_state()
    developer_profile()
    
    t1, t2, t3, t4 = st.tabs(["📊 Dashboard", "⚖️ Auction", "👥 Teams", "⚙️ Settings"])
    with t1: render_dashboard()
    with t2: render_auction()
    with t3: render_teams()
    with t4: render_settings()

if __name__ == "__main__":
    main()
