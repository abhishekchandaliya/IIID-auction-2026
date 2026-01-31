import streamlit as st
import pandas as pd
import os
import time
import random
import json
import base64
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

TEAM_NAMES = [
    "Aditya Avengers",
    "Alfen Royals",
    "Lantern Legends",
    "Primark Superkings",
    "Sai Kripa Soldiers",
    "Taluka Fighters"
]

DEFAULT_CONFIG = {
    "purse_limit": 10000,  # Increased default based on your screenshot
    "max_squad_size": 25,
    "base_price": 10,
    "category_limits": {
        "Cricket": {"A": 5, "B": 5, "C": 5},
        "Badminton": {"A": 5, "B": 5, "C": 5},
        "TT": {"A": 5, "B": 5, "C": 5}
    }
}

# File to store progress automatically
HISTORY_FILE = "auction_history_v2.csv"

# ==========================================
# 2. CSS STYLING
# ==========================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #0f172a;
        color: #e2e8f0;
    }

    .main-header {
        font-size: 2.5rem;
        font-weight: 900;
        background: -webkit-linear-gradient(left, #ffffff, #94a3b8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    
    .projector-text {
        text-shadow: 0 0 15px rgba(255,255,255,0.6);
    }

    .badge {
        display: inline-block;
        padding: 0.25em 0.6em;
        font-size: 0.75em;
        font-weight: 700;
        line-height: 1;
        text-align: center;
        white-space: nowrap;
        vertical-align: baseline;
        border-radius: 0.375rem;
    }
    .badge-cricket { background-color: #1d4ed8; color: #dbeafe; border: 1px solid #3b82f6; }
    .badge-badminton { background-color: #047857; color: #d1fae5; border: 1px solid #10b981; }
    .badge-tt { background-color: #c2410c; color: #ffedd5; border: 1px solid #f97316; }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================

def save_progress():
    """Autosaves the current player data to a CSV so data isn't lost on refresh."""
    if 'players' in st.session_state and not st.session_state.players.empty:
        st.session_state.players.to_csv(HISTORY_FILE, index=False)

def load_progress():
    """Loads history if it exists."""
    if os.path.exists(HISTORY_FILE):
        return pd.read_csv(HISTORY_FILE)
    return None

def init_session_state():
    if 'players' not in st.session_state:
        # Try to load previous session history first
        history = load_progress()
        if history is not None:
            st.session_state.players = history
            st.toast("🔄 Restored previous auction progress!", icon="💾")
        else:
            st.session_state.players = pd.DataFrame(columns=[
                'ID', 'Name', 'Team', 'Price', 'Cricket', 'Badminton', 'TT', 'CaptainFor', 'ContactNo'
            ])
    
    if 'config' not in st.session_state:
        st.session_state.config = DEFAULT_CONFIG
        
    if 'activity_log' not in st.session_state:
        st.session_state.activity_log = []
        
    if 'current_player_id' not in st.session_state:
        st.session_state.current_player_id = None

    if 'admin_mode' not in st.session_state:
        st.session_state.admin_mode = False

def load_data(uploaded_file):
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            
            # 1. Clean Headers
            df.columns = df.columns.str.strip()
            
            # 2. Intelligent Renaming
            for col in df.columns:
                clean_col = col.lower().replace(' ', '')
                if clean_col in ['playername', 'player', 'name']:
                    df.rename(columns={col: 'Name'}, inplace=True)
                elif 'cric' in clean_col or 'batting' in clean_col:
                    df.rename(columns={col: 'Cricket'}, inplace=True)
                elif 'bad' in clean_col or 'shuttle' in clean_col:
                    df.rename(columns={col: 'Badminton'}, inplace=True)
                elif 'table' in clean_col or 'tt' in clean_col:
                    df.rename(columns={col: 'TT'}, inplace=True)
                elif 'mobile' in clean_col or 'contact' in clean_col:
                    df.rename(columns={col: 'ContactNo'}, inplace=True)

            # 3. Add Missing Columns
            if 'ID' not in df.columns:
                df['ID'] = range(1, len(df) + 1)
            
            for col in ['Team', 'Price', 'CaptainFor', 'ContactNo']:
                if col not in df.columns:
                    df[col] = None
                    
            # 4. Normalize Data
            for sport in ['Cricket', 'Badminton', 'TT']:
                if sport in df.columns:
                    df[sport] = df[sport].fillna('0').astype(str).str.upper().str.strip()
                    # Keep only A, B, C. Convert others to 0
                    df[sport] = df[sport].apply(lambda x: x if x in ['A', 'B', 'C'] else '0')
                else:
                    df[sport] = '0'

            df['Price'] = df['Price'].fillna(0).astype(int)

            st.session_state.players = df
            save_progress() # Save immediately
            st.success(f"✅ Loaded {len(df)} players successfully!")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Error parsing CSV: {e}")

def get_player_image(player_name):
    """
    Robust Image Finder (Case Insensitive)
    """
    base_path = "photos"
    if not os.path.exists(base_path):
        return None

    # Get list of all files in photos folder
    all_files = os.listdir(base_path)
    
    # Clean target name
    target_name = str(player_name).strip().lower()
    
    for filename in all_files:
        # Remove extension and lowercase
        file_clean = os.path.splitext(filename)[0].strip().lower()
        
        if file_clean == target_name:
            return os.path.join(base_path, filename)
            
    # Default fallback
    return os.path.join(base_path, "default_player.png") if os.path.exists(os.path.join(base_path, "default_player.png")) else None

def calculate_team_stats(players_df, config):
    stats = []
    for team_name in TEAM_NAMES:
        team_players = players_df[players_df['Team'] == team_name]
        count = len(team_players)
        spent = team_players['Price'].sum()
        
        cric = team_players[team_players['Cricket'] != '0']
        bad = team_players[team_players['Badminton'] != '0']
        tt = team_players[team_players['TT'] != '0']
        
        available = config['purse_limit'] - spent
        empty_slots = max(0, config['max_squad_size'] - count)
        reserve = empty_slots * config['base_price']
        disposable = available - reserve

        stats.append({
            "Name": team_name,
            "Count": count,
            "Spent": spent,
            "Available": available,
            "Disposable": disposable,
            "Cricket": len(cric),
            "Badminton": len(bad),
            "TT": len(tt),
            "Cric_A": len(cric[cric['Cricket'] == 'A']), "Cric_B": len(cric[cric['Cricket'] == 'B']), "Cric_C": len(cric[cric['Cricket'] == 'C']),
            "Bad_A": len(bad[bad['Badminton'] == 'A']), "Bad_B": len(bad[bad['Badminton'] == 'B']), "Bad_C": len(bad[bad['Badminton'] == 'C']),
            "TT_A": len(tt[tt['TT'] == 'A']), "TT_B": len(tt[tt['TT'] == 'B']), "TT_C": len(tt[tt['TT'] == 'C']),
        })
    return pd.DataFrame(stats)

def check_fair_play(team_name, player_sport_grades, team_stats_df, config):
    team_row = team_stats_df[team_stats_df['Name'] == team_name].iloc[0]
    sports = ['Cricket', 'Badminton', 'TT']
    
    for sport in sports:
        grade = player_sport_grades.get(sport)
        if grade in ['A', 'B', 'C']:
            limit = config['category_limits'][sport][grade]
            col_prefix = "Cric" if sport == "Cricket" else ("Bad" if sport == "Badminton" else "TT")
            col_name = f"{col_prefix}_{grade}"
            current_count = team_row[col_name]
            
            if current_count >= limit:
                other_teams = team_stats_df[team_stats_df['Name'] != team_name]
                others_lagging = any(other_teams[col_name] < limit)
                if others_lagging:
                    return False, f"🚫 {sport} QUOTA: All teams must have {limit} Grade '{grade}' players in {sport} before you can buy more."
    return True, ""

def log_activity(type, message):
    st.session_state.activity_log.insert(0, {
        "id": str(time.time()),
        "type": type,
        "message": message,
        "time": datetime.now().strftime("%H:%M:%S")
    })
    st.session_state.activity_log = st.session_state.activity_log[:50]

# ==========================================
# 4. DASHBOARD TAB (Updated)
# ==========================================

def render_dashboard():
    st.markdown('<div class="main-header">Team Standings</div>', unsafe_allow_html=True)
    
    # --- LIVE AUCTION STATUS CARD (New Feature) ---
    if st.session_state.current_player_id:
        p_id = st.session_state.current_player_id
        try:
            live_p = st.session_state.players[st.session_state.players['ID'] == p_id].iloc[0]
            
            st.markdown(f"""
            <div style="background: linear-gradient(90deg, #b91c1c 0%, #7f1d1d 100%); padding: 15px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #ef4444; display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 20px;">
                    <span style="font-size: 2rem;">🔥</span>
                    <div>
                        <div style="color: #fca5a5; font-size: 0.8rem; font-weight: bold; letter-spacing: 1px;">NOW ON AUCTION</div>
                        <div style="color: white; font-size: 1.8rem; font-weight: 800;">{live_p['Name']}</div>
                    </div>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 5px 15px; border-radius: 50px; color: white;">
                    Base: ₹{st.session_state.config['base_price']}L
                </div>
            </div>
            """, unsafe_allow_html=True)
        except:
            pass # Handle case where ID might be stale

    df = st.session_state.players
    config = st.session_state.config
    stats_df = calculate_team_stats(df, config)
    
    total_sold = len(df[df['Team'].notna()])
    total_slots = len(TEAM_NAMES) * config['max_squad_size']
    remaining = total_slots - total_sold
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Sold", total_sold)
    col2.metric("Remaining Slots", remaining)
    
    sold_df = df[df['Team'].notna()]
    highest_bid = sold_df['Price'].max() if not sold_df.empty else 0
    col3.metric("Highest Bid", f"₹{highest_bid}L")
    
    st.markdown("### 📊 Leaderboard")
    display_df = stats_df[['Name', 'Disposable', 'Count', 'Cricket', 'Badminton', 'TT']].copy()
    display_df.columns = ['Team', 'Purse Available', 'Squad Size', '🏏 Cric', '🏸 Bad', '🏓 TT']
    
    st.dataframe(
        display_df.style.background_gradient(subset=['Purse Available'], cmap="Greens"),
        use_container_width=True,
        hide_index=True,
        height=300
    )
    
    with st.expander("View Detailed Category Breakdown"):
        detailed_df = stats_df[['Name', 'Cric_A', 'Cric_B', 'Cric_C', 'Bad_A', 'Bad_B', 'Bad_C', 'TT_A', 'TT_B', 'TT_C']]
        st.dataframe(detailed_df, use_container_width=True, hide_index=True)

# ==========================================
# 5. AUCTION CONSOLE
# ==========================================

def render_auction_console():
    st.markdown('<div class="main-header">Auction Console</div>', unsafe_allow_html=True)
    
    players = st.session_state.players
    unsold = players[players['Team'].isna()]
    
    if unsold.empty:
        st.info("Auction Complete!")
        return

    # Selector
    col_sel1, col_sel2 = st.columns([1, 3])
    with col_sel1:
        st.markdown("### 🎲 Selector")
        sport_filter = st.selectbox("Sport", ["All", "Cricket", "Badminton", "TT"])
        grade_filter = st.selectbox("Grade", ["All", "A", "B", "C"])
        
        if st.button("🎰 SPIN WHEEL", type="primary", use_container_width=True):
            pool = unsold
            if sport_filter != "All": pool = pool[pool[sport_filter] != '0']
            if grade_filter != "All":
                if sport_filter == "All":
                    pool = pool[(pool['Cricket'] == grade_filter) | (pool['Badminton'] == grade_filter) | (pool['TT'] == grade_filter)]
                else:
                    pool = pool[pool[sport_filter] == grade_filter]
            
            if not pool.empty:
                placeholder = st.empty()
                for _ in range(10):
                    placeholder.markdown(f"<h2 style='text-align:center; color:#64748b;'>{pool.sample(1).iloc[0]['Name']}</h2>", unsafe_allow_html=True)
                    time.sleep(0.1)
                selected = pool.sample(1).iloc[0]
                st.session_state.current_player_id = selected['ID']
                placeholder.empty()
                st.rerun()
            else:
                st.warning("No players match criteria.")

    with col_sel2:
        st.markdown("### 🔍 Search")
        if 'Name' in unsold.columns:
            search_term = st.selectbox("Find Player", options=unsold['Name'].tolist(), index=None, placeholder="Type to search...")
            if search_term:
                player_row = unsold[unsold['Name'] == search_term].iloc[0]
                if st.session_state.current_player_id != player_row['ID']:
                    st.session_state.current_player_id = player_row['ID']
                    st.rerun()
        else:
            st.error("Data missing 'Name' column.")

    st.markdown("---")

    # Hero Card
    if st.session_state.current_player_id:
        try:
            current_p = players[players['ID'] == st.session_state.current_player_id].iloc[0]
        except IndexError:
            st.session_state.current_player_id = None
            st.rerun()

        hero_col1, hero_col2 = st.columns([1, 3])
        with hero_col1:
            img_path = get_player_image(current_p['Name'])
            if img_path:
                st.image(img_path, width=250)
                st.caption(f"File found: {os.path.basename(img_path)}") # Debugging help
            else:
                st.markdown("<div style='width:200px; height:200px; background:#334155; display:flex; align-items:center; justify-content:center; border-radius:10px;'><span style='font-size:3rem;'>👤</span></div>", unsafe_allow_html=True)
                st.caption("No image found in 'photos' folder")

        with hero_col2:
            st.markdown(f"<h1 class='projector-text' style='font-size: 3.5rem; margin:0;'>{current_p['Name']}</h1>", unsafe_allow_html=True)
            badges_html = ""
            if current_p['Cricket'] != '0': badges_html += f"<span class='badge badge-cricket'>CRICKET: {current_p['Cricket']}</span> "
            if current_p['Badminton'] != '0': badges_html += f"<span class='badge badge-badminton'>BADMINTON: {current_p['Badminton']}</span> "
            if current_p['TT'] != '0': badges_html += f"<span class='badge badge-tt'>TT: {current_p['TT']}</span> "
            st.markdown(f"<div style='margin-top:10px; margin-bottom:20px;'>{badges_html}</div>", unsafe_allow_html=True)
            st.metric("Base Price", f"₹{st.session_state.config['base_price']}L")

        # Bidding
        if st.session_state.admin_mode:
            st.markdown("### 💰 Bidding Control")
            stats_df = calculate_team_stats(players, st.session_state.config)
            valid_teams = stats_df[stats_df['Disposable'] >= st.session_state.config['base_price']]
            team_options = {row['Name']: f"{row['Name']} (₹{row['Disposable']}L)" for _, row in valid_teams.iterrows()}
            
            b1, b2, b3 = st.columns([2, 1, 1])
            with b1:
                selected_team = st.selectbox("Winning Team", options=team_options.keys(), format_func=lambda x: team_options[x])
            with b2:
                sold_price = st.number_input("Sold Price", min_value=st.session_state.config['base_price'], step=5)
            with b3:
                st.write("")
                st.write("")
                if st.button("🔨 SOLD", type="primary", use_container_width=True):
                    # Validation Logic
                    t_stat = stats_df[stats_df['Name'] == selected_team].iloc[0]
                    if t_stat['Count'] >= st.session_state.config['max_squad_size']:
                        st.error("Squad Full!")
                        return
                    
                    max_bid = t_stat['Disposable'] + st.session_state.config['base_price']
                    if sold_price > max_bid:
                        st.error(f"Insufficient Funds! Max: {max_bid}")
                        return
                        
                    # Fair Play
                    p_grades = {'Cricket': current_p['Cricket'], 'Badminton': current_p['Badminton'], 'TT': current_p['TT']}
                    fair, msg = check_fair_play(selected_team, p_grades, stats_df, st.session_state.config)
                    if not fair:
                        st.error(msg)
                        return

                    # Execute Sale
                    idx = players.index[players['ID'] == st.session_state.current_player_id].tolist()[0]
                    st.session_state.players.at[idx, 'Team'] = selected_team
                    st.session_state.players.at[idx, 'Price'] = sold_price
                    
                    # SAVE STATE IMMEDIATELY
                    save_progress()
                    
                    log_activity('sale', f"SOLD: **{current_p['Name']}** to {selected_team} for ₹{sold_price}L")
                    st.balloons()
                    st.session_state.current_player_id = None
                    st.success("Sold & Saved!")
                    time.sleep(1)
                    st.rerun()

            if st.button("Skip / Pass"):
                st.session_state.current_player_id = None
                st.rerun()
        else:
            st.warning("Login to enable controls")
    else:
        st.info("Waiting for spin...")

# ==========================================
# 6. TEAMS TAB
# ==========================================

def render_teams():
    st.markdown('<div class="main-header">Team Rosters</div>', unsafe_allow_html=True)
    players = st.session_state.players
    config = st.session_state.config
    stats = calculate_team_stats(players, config)
    
    # Last Sold Context
    last_sales = st.session_state.activity_log[:3]
    if last_sales:
        st.markdown("##### 🕒 Recent Activity")
        for log in last_sales:
            st.caption(f"{log['time']} - {log['message']}")
            
    st.markdown("---")

    for _, team in stats.iterrows():
        with st.expander(f"{team['Name']} | Used: {team['Count']}/{config['max_squad_size']} | Purse: ₹{team['Disposable']}L"):
            t_players = players[players['Team'] == team['Name']]
            if not t_players.empty:
                st.dataframe(t_players[['Name', 'Price', 'Cricket', 'Badminton', 'TT']], use_container_width=True, hide_index=True)
            else:
                st.write("No players.")

# ==========================================
# 7. SETTINGS
# ==========================================

def render_settings():
    st.markdown('<div class="main-header">Admin Settings</div>', unsafe_allow_html=True)
    
    if not st.session_state.admin_mode:
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            if pwd == "ABCD2026":
                st.session_state.admin_mode = True
                st.rerun()
        return

    tab1, tab2, tab3 = st.tabs(["Data", "Rules", "Correction"])
    
    with tab1:
        st.subheader("Data Management")
        up_file = st.file_uploader("Upload Master CSV", type=['csv'])
        if up_file: load_data(up_file)
        
        if st.button("🗑️ Reset Auction (New Game)", type="primary"):
            if os.path.exists(HISTORY_FILE): os.remove(HISTORY_FILE)
            st.session_state.players = pd.DataFrame()
            st.session_state.activity_log = []
            st.success("Reset Complete. Please upload CSV.")
            st.rerun()

    with tab2:
        st.write("Edit Config in code for safety during auction.")
        st.json(st.session_state.config)

    with tab3:
        st.subheader("Undo/Fix Sale")
        sold = st.session_state.players[st.session_state.players['Team'].notna()]
        if not sold.empty:
            if 'Name' in sold.columns:
                p_fix = st.selectbox("Select Player", sold['Name'].unique())
                if p_fix:
                    idx = st.session_state.players.index[st.session_state.players['Name'] == p_fix].tolist()[0]
                    if st.button("❌ Revert to Unsold"):
                        st.session_state.players.at[idx, 'Team'] = None
                        st.session_state.players.at[idx, 'Price'] = 0
                        save_progress()
                        st.success("Reverted!")
                        st.rerun()

# ==========================================
# MAIN
# ==========================================

def developer_profile():
    with st.sidebar:
        st.markdown("### 👨‍💻 Developer")
        try:
            # Safe Search for Developer
            if 'Name' in st.session_state.players.columns:
                dev = st.session_state.players[st.session_state.players['Name'].str.contains("Abhishek", case=False, na=False)]
                if not dev.empty:
                    st.success(f"Playing for: {dev.iloc[0]['Team'] if pd.notna(dev.iloc[0]['Team']) else 'Unsold'}")
                else:
                    st.write("Abhishek Chandaliya")
        except:
            pass

def main():
    init_session_state()
    developer_profile()
    
    tabs = st.tabs(["📊 Dashboard", "⚖️ Auction Console", "👥 Teams", "⚙️ Settings"])
    with tabs[0]: render_dashboard()
    with tabs[1]: render_auction_console()
    with tabs[2]: render_teams()
    with tabs[3]: render_settings()

if __name__ == "__main__":
    main()
