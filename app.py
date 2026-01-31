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
    "purse_limit": 2500,
    "max_squad_size": 35,
    "base_price": 10,
    "category_limits": {
        "Cricket": {"A": 4, "B": 4, "C": 4},
        "Badminton": {"A": 2, "B": 2, "C": 2},
        "TT": {"A": 2, "B": 2, "C": 2}
    }
}

# ==========================================
# 2. CSS STYLING
# ==========================================

st.markdown("""
<style>
    /* Global Font & Theme */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #0f172a;
        color: #e2e8f0;
    }

    /* Header Styling */
    .main-header {
        font-size: 2.5rem;
        font-weight: 900;
        background: -webkit-linear-gradient(left, #ffffff, #94a3b8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    
    .sub-header {
        font-size: 0.9rem;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }

    /* Cards */
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    .hero-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #475569;
        border-radius: 20px;
        padding: 30px;
        text-align: center;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
    }

    /* Projector Text Effect */
    .projector-text {
        text-shadow: 0 0 10px rgba(255,255,255,0.5);
    }

    /* Custom Badges */
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

    /* Remove Streamlit default margin */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
    }
    
    /* Hide Deploy Button */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================

def init_session_state():
    if 'players' not in st.session_state:
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
            
            # Normalize columns
            # Simple mapping if CSV headers are different
            rename_map = {
                'Player Name': 'Name', 'Player': 'Name', 'PLAYER NAME': 'Name',
                'Cric': 'Cricket', 'Batting': 'Cricket',
                'Bad': 'Badminton', 'Shuttle': 'Badminton',
                'Table Tennis': 'TT',
                'Mobile': 'ContactNo', 'Contact': 'ContactNo'
            }
            df = df.rename(columns=rename_map)
            
            # Ensure ID exists
            if 'ID' not in df.columns:
                df['ID'] = range(1, len(df) + 1)
            
            # Ensure standard columns exist
            for col in ['Team', 'Price', 'CaptainFor', 'ContactNo']:
                if col not in df.columns:
                    df[col] = None
                    
            # Normalize Grades (A, B, C, 0)
            for sport in ['Cricket', 'Badminton', 'TT']:
                if sport in df.columns:
                    df[sport] = df[sport].fillna('0').astype(str).str.upper().str.strip()
                    df[sport] = df[sport].apply(lambda x: x if x in ['A', 'B', 'C'] else '0')
                else:
                    df[sport] = '0'

            # Fill Price with 0
            df['Price'] = df['Price'].fillna(0).astype(int)

            st.session_state.players = df
            st.success(f"Loaded {len(df)} players successfully!")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Error parsing CSV: {e}")

def get_player_image(player_name):
    """
    Checks for the player's photo in the 'photos' directory.
    Fallback logic: png -> jpg -> jpeg -> default_player.png
    """
    base_path = "photos"
    if not os.path.exists(base_path):
        # Create if it doesn't exist, just to prevent error
        try:
            os.makedirs(base_path) 
        except:
            pass

    extensions = ['.png', '.jpg', '.jpeg']
    
    # Check exact name match
    for ext in extensions:
        full_path = os.path.join(base_path, f"{player_name}{ext}")
        if os.path.exists(full_path):
            return full_path
            
    # Check default
    default_path = os.path.join(base_path, "default_player.png")
    if os.path.exists(default_path):
        return default_path
        
    return None # Will trigger a UI placeholder if returned None

def calculate_team_stats(players_df, config):
    stats = []
    
    for team_name in TEAM_NAMES:
        team_players = players_df[players_df['Team'] == team_name]
        
        count = len(team_players)
        spent = team_players['Price'].sum()
        
        # Breakdown
        cric = team_players[team_players['Cricket'] != '0']
        bad = team_players[team_players['Badminton'] != '0']
        tt = team_players[team_players['TT'] != '0']
        
        available = config['purse_limit'] - spent
        # Reserve money for empty slots
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
            "Cric_A": len(cric[cric['Cricket'] == 'A']),
            "Cric_B": len(cric[cric['Cricket'] == 'B']),
            "Cric_C": len(cric[cric['Cricket'] == 'C']),
            "Bad_A": len(bad[bad['Badminton'] == 'A']),
            "Bad_B": len(bad[bad['Badminton'] == 'B']),
            "Bad_C": len(bad[bad['Badminton'] == 'C']),
            "TT_A": len(tt[tt['TT'] == 'A']),
            "TT_B": len(tt[tt['TT'] == 'B']),
            "TT_C": len(tt[tt['TT'] == 'C']),
        })
        
    return pd.DataFrame(stats)

def check_fair_play(team_name, player_sport_grades, team_stats_df, config):
    """
    Checks Fair Play limits for a specific player being sold to a specific team.
    player_sport_grades: dict {'Cricket': 'A', 'Badminton': '0', ...}
    """
    team_row = team_stats_df[team_stats_df['Name'] == team_name].iloc[0]
    
    sports = ['Cricket', 'Badminton', 'TT']
    
    for sport in sports:
        grade = player_sport_grades.get(sport)
        if grade in ['A', 'B', 'C']:
            # Get limit from config
            limit = config['category_limits'][sport][grade]
            
            # Get current count for this team
            # Map column name: e.g. "Cric_A", "Bad_B"
            col_prefix = "Cric" if sport == "Cricket" else ("Bad" if sport == "Badminton" else "TT")
            col_name = f"{col_prefix}_{grade}"
            
            current_count = team_row[col_name]
            
            # Constraint Logic
            if current_count >= limit:
                # Check if ALL other teams have reached this limit
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
    # Keep log size manageable
    st.session_state.activity_log = st.session_state.activity_log[:50]

# ==========================================
# 4. TAB COMPONENT: DASHBOARD
# ==========================================

def render_dashboard():
    st.markdown('<div class="main-header">Team Standings</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Live Auction Metrics</div>', unsafe_allow_html=True)
    
    df = st.session_state.players
    config = st.session_state.config
    stats_df = calculate_team_stats(df, config)
    
    # Top Level Metrics
    total_sold = len(df[df['Team'].notna()])
    total_slots = len(TEAM_NAMES) * config['max_squad_size']
    remaining = total_slots - total_sold
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Sold", total_sold)
    col2.metric("Remaining Slots", remaining)
    
    # High Scores
    sold_df = df[df['Team'].notna()]
    highest_bid = sold_df['Price'].max() if not sold_df.empty else 0
    col3.metric("Highest Bid", f"₹{highest_bid}L")
    
    # Main Table
    st.markdown("### 📊 Leaderboard")
    
    # Formatting for display
    display_df = stats_df[['Name', 'Disposable', 'Count', 'Cricket', 'Badminton', 'TT']].copy()
    display_df.columns = ['Team', 'Purse Available', 'Squad Size', '🏏 Cric', '🏸 Bad', '🏓 TT']
    
    st.dataframe(
        display_df.style.background_gradient(subset=['Purse Available'], cmap="Greens"),
        use_container_width=True,
        hide_index=True,
        height=300
    )
    
    # Category Breakdown (Detailed)
    with st.expander("View Detailed Category Breakdown"):
        detailed_df = stats_df[['Name', 
                                'Cric_A', 'Cric_B', 'Cric_C', 
                                'Bad_A', 'Bad_B', 'Bad_C',
                                'TT_A', 'TT_B', 'TT_C']]
        st.dataframe(detailed_df, use_container_width=True, hide_index=True)

# ==========================================
# 5. TAB COMPONENT: AUCTION CONSOLE
# ==========================================

def render_auction_console():
    st.markdown('<div class="main-header">Auction Console</div>', unsafe_allow_html=True)
    
    players = st.session_state.players
    unsold = players[players['Team'].isna()]
    
    if unsold.empty:
        st.info("Auction Complete! All players sold.")
        return

    # --- 1. SELECTION AREA ---
    col_sel1, col_sel2 = st.columns([1, 3])
    
    with col_sel1:
        st.markdown("### 🎲 Selector")
        # Filters for Randomizer
        sport_filter = st.selectbox("Sport", ["All", "Cricket", "Badminton", "TT"])
        grade_filter = st.selectbox("Grade", ["All", "A", "B", "C"])
        
        if st.button("🎰 SPIN WHEEL", type="primary", use_container_width=True):
            # Filtering Logic
            pool = unsold
            if sport_filter != "All":
                pool = pool[pool[sport_filter] != '0']
            if grade_filter != "All":
                if sport_filter == "All":
                    # Grade in ANY sport
                    pool = pool[
                        (pool['Cricket'] == grade_filter) | 
                        (pool['Badminton'] == grade_filter) | 
                        (pool['TT'] == grade_filter)
                    ]
                else:
                    pool = pool[pool[sport_filter] == grade_filter]
            
            if not pool.empty:
                # Animation Effect
                placeholder = st.empty()
                for _ in range(15):
                    random_name = pool.sample(1).iloc[0]['Name']
                    placeholder.markdown(f"<h1 style='text-align: center; color: #64748b;'>{random_name}</h1>", unsafe_allow_html=True)
                    time.sleep(0.1)
                
                selected = pool.sample(1).iloc[0]
                st.session_state.current_player_id = selected['ID']
                placeholder.empty()
                st.rerun()
            else:
                st.warning("No players match filter criteria.")

    with col_sel2:
        st.markdown("### 🔍 Search")
        search_term = st.selectbox(
            "Find Player", 
            options=unsold['Name'].tolist(), 
            index=None, 
            placeholder="Type to search..."
        )
        if search_term:
            player_row = unsold[unsold['Name'] == search_term].iloc[0]
            if st.session_state.current_player_id != player_row['ID']:
                st.session_state.current_player_id = player_row['ID']
                st.rerun()

    st.markdown("---")

    # --- 2. HERO CARD (Player Focus) ---
    if st.session_state.current_player_id:
        p_id = st.session_state.current_player_id
        current_p = players[players['ID'] == p_id].iloc[0]
        
        # Split Layout: Image | Info
        hero_col1, hero_col2 = st.columns([1, 3])
        
        with hero_col1:
            # Display Photo
            img_path = get_player_image(current_p['Name'])
            if img_path:
                st.image(img_path, width=200, caption=f"ID: {current_p['ID']}")
            else:
                # Fallback UI if no image found (though function returns default)
                st.markdown(f"""
                <div style="width:200px; height:200px; background:#334155; display:flex; align-items:center; justify-content:center; border-radius:10px;">
                    <span style="font-size:3rem;">👤</span>
                </div>
                """, unsafe_allow_html=True)
                
        with hero_col2:
            st.markdown(f"<h1 class='projector-text' style='font-size: 4rem; margin:0;'>{current_p['Name']}</h1>", unsafe_allow_html=True)
            
            # Badges
            badges_html = ""
            if current_p['Cricket'] != '0':
                badges_html += f"<span class='badge badge-cricket'>CRICKET: {current_p['Cricket']}</span> "
            if current_p['Badminton'] != '0':
                badges_html += f"<span class='badge badge-badminton'>BADMINTON: {current_p['Badminton']}</span> "
            if current_p['TT'] != '0':
                badges_html += f"<span class='badge badge-tt'>TT: {current_p['TT']}</span> "
            
            st.markdown(f"<div style='margin-top:10px; margin-bottom:20px;'>{badges_html}</div>", unsafe_allow_html=True)
            
            # Base Price
            st.metric("Base Price", f"₹{st.session_state.config['base_price']}L")

        st.markdown("---")

        # --- 3. BIDDING CONTROLS ---
        if st.session_state.admin_mode:
            st.markdown("### 💰 Bidding")
            
            stats_df = calculate_team_stats(players, st.session_state.config)
            
            # 3a. Team Selection
            # Filter teams that have budget
            valid_teams = stats_df[stats_df['Disposable'] >= st.session_state.config['base_price']]
            
            team_options = {row['Name']: f"{row['Name']} (₹{row['Disposable']}L)" for _, row in valid_teams.iterrows()}
            
            b_col1, b_col2, b_col3 = st.columns([2, 1, 1])
            
            with b_col1:
                selected_team_name = st.selectbox("Winning Team", options=team_options.keys(), format_func=lambda x: team_options[x])
            
            with b_col2:
                bid_amount = st.number_input("Sold Price", min_value=st.session_state.config['base_price'], step=5, value=st.session_state.config['base_price'])
                
            with b_col3:
                st.write("") # Spacer
                st.write("")
                if st.button("🔨 SOLD", type="primary", use_container_width=True):
                    # --- VALIDATION LOGIC ---
                    
                    # 1. Budget Check
                    team_stats = stats_df[stats_df['Name'] == selected_team_name].iloc[0]
                    # Logic: If squad is full?
                    if team_stats['Count'] >= st.session_state.config['max_squad_size']:
                        st.error("Team Squad is Full!")
                        return
                    
                    # Logic: Max Bid
                    slots_remaining = st.session_state.config['max_squad_size'] - team_stats['Count']
                    # Disposable is calculated assuming we keep reserve for ALL empty slots including this one.
                    # So actual max bid for THIS player = Disposable + Base_Price
                    max_bid = team_stats['Disposable'] + st.session_state.config['base_price']
                    
                    if bid_amount > max_bid:
                        st.error(f"Insufficient Funds! Max bid allowed: ₹{max_bid}L")
                        return

                    # 2. Fair Play Check
                    player_sports = {
                        'Cricket': current_p['Cricket'],
                        'Badminton': current_p['Badminton'],
                        'TT': current_p['TT']
                    }
                    
                    is_fair, fp_msg = check_fair_play(selected_team_name, player_sports, stats_df, st.session_state.config)
                    
                    if not is_fair:
                        st.error(fp_msg)
                        return

                    # --- EXECUTE SALE ---
                    idx = players.index[players['ID'] == p_id].tolist()[0]
                    st.session_state.players.at[idx, 'Team'] = selected_team_name
                    st.session_state.players.at[idx, 'Price'] = bid_amount
                    
                    log_activity('sale', f"SOLD: **{current_p['Name']}** to {selected_team_name} for ₹{bid_amount}L")
                    
                    st.balloons()
                    st.session_state.current_player_id = None
                    st.success("Sold!")
                    time.sleep(1)
                    st.rerun()
                    
            if st.button("Pass / Unsold", use_container_width=True):
                st.session_state.current_player_id = None
                st.rerun()
        else:
            st.warning("🔒 Login as Admin in Settings to Enable Bidding")
            
    else:
        st.info("Select a player to begin auctioning.")

# ==========================================
# 6. TAB COMPONENT: TEAMS (ROSTER)
# ==========================================

def render_roster_view():
    st.markdown('<div class="main-header">Team Rosters</div>', unsafe_allow_html=True)
    
    players = st.session_state.players
    config = st.session_state.config
    stats_df = calculate_team_stats(players, config)
    
    # Highlight Toggles
    st.markdown("##### 🔦 Auctioneer's Context (Highlight Needs)")
    hl_col1, hl_col2, hl_col3, hl_col4 = st.columns(4)
    highlight = st.radio("Highlight Teams needing:", ["None", "Cricket < 6", "Badminton < 4", "TT < 4"], horizontal=True, label_visibility="collapsed")
    
    for _, team in stats_df.iterrows():
        # Determine highlighting
        is_highlighted = False
        if highlight == "Cricket < 6" and team['Cricket'] < 6: is_highlighted = True
        if highlight == "Badminton < 4" and team['Badminton'] < 4: is_highlighted = True
        if highlight == "TT < 4" and team['TT'] < 4: is_highlighted = True
        
        border_color = "#3b82f6" if is_highlighted else "#334155"
        bg_color = "#1e3a8a" if is_highlighted else "#1e293b"
        
        with st.container():
            st.markdown(f"""
            <div style="border: 2px solid {border_color}; background-color: {bg_color}; padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                <h3 style="margin:0; color: white;">{team['Name']}</h3>
                <div style="display:flex; justify-content:space-between; margin-top:5px; font-size:0.9rem; color:#cbd5e1;">
                    <span>💰 Purse: <b>₹{team['Disposable']}L</b></span>
                    <span>👥 Size: <b>{team['Count']}/{config['max_squad_size']}</b></span>
                    <span>🏏 {team['Cricket']} | 🏸 {team['Badminton']} | 🏓 {team['TT']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander(f"View {team['Name']} Roster"):
                team_players = players[players['Team'] == team['Name']]
                if not team_players.empty:
                    # Formatting columns
                    view_df = team_players[['Name', 'Price', 'Cricket', 'Badminton', 'TT', 'CaptainFor']].copy()
                    
                    # Highlight Captains
                    def highlight_captain(row):
                        return ['background-color: #4338ca' if row['CaptainFor'] else '' for _ in row]
                    
                    st.dataframe(view_df.style.apply(highlight_captain, axis=1), use_container_width=True, hide_index=True)
                else:
                    st.write("No players yet.")

# ==========================================
# 7. TAB COMPONENT: SETTINGS & ADMIN
# ==========================================

def render_settings():
    st.markdown('<div class="main-header">Settings & Admin</div>', unsafe_allow_html=True)
    
    # 1. AUTH
    if not st.session_state.admin_mode:
        with st.form("admin_login"):
            password = st.text_input("Admin Password", type="password")
            if st.form_submit_button("Login"):
                if password == "ABCD2026": # You can change this
                    st.session_state.admin_mode = True
                    st.success("Logged in!")
                    st.rerun()
                else:
                    st.error("Incorrect Password")
        return # Stop rendering if not admin

    if st.button("Logout"):
        st.session_state.admin_mode = False
        st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["⚙️ Config", "👑 Captains", "🛠️ Correction", "💾 Data"])

    # --- CONFIG TAB ---
    with tab1:
        st.subheader("Tournament Rules")
        
        c_col1, c_col2, c_col3 = st.columns(3)
        new_purse = c_col1.number_input("Purse Limit", value=st.session_state.config['purse_limit'])
        new_squad = c_col2.number_input("Max Squad Size", value=st.session_state.config['max_squad_size'])
        new_base = c_col3.number_input("Base Price", value=st.session_state.config['base_price'])
        
        st.subheader("⚖️ Fair Play Limits (Per Sport)")
        
        # Nested Config Logic
        limits = st.session_state.config['category_limits']
        
        # Cricket
        st.markdown("**Cricket**")
        cc1, cc2, cc3 = st.columns(3)
        c_a = cc1.number_input("Min 'A' (Cricket)", value=limits['Cricket']['A'])
        c_b = cc2.number_input("Min 'B' (Cricket)", value=limits['Cricket']['B'])
        c_c = cc3.number_input("Min 'C' (Cricket)", value=limits['Cricket']['C'])

        # Badminton
        st.markdown("**Badminton**")
        bb1, bb2, bb3 = st.columns(3)
        b_a = bb1.number_input("Min 'A' (Badminton)", value=limits['Badminton']['A'])
        b_b = bb2.number_input("Min 'B' (Badminton)", value=limits['Badminton']['B'])
        b_c = bb3.number_input("Min 'C' (Badminton)", value=limits['Badminton']['C'])

        # TT
        st.markdown("**TT**")
        tt1, tt2, tt3 = st.columns(3)
        t_a = tt1.number_input("Min 'A' (TT)", value=limits['TT']['A'])
        t_b = tt2.number_input("Min 'B' (TT)", value=limits['TT']['B'])
        t_c = tt3.number_input("Min 'C' (TT)", value=limits['TT']['C'])
        
        if st.button("Save Rules"):
            st.session_state.config = {
                "purse_limit": new_purse,
                "max_squad_size": new_squad,
                "base_price": new_base,
                "category_limits": {
                    "Cricket": {"A": c_a, "B": c_b, "C": c_c},
                    "Badminton": {"A": b_a, "B": b_b, "C": b_c},
                    "TT": {"A": t_a, "B": t_b, "C": t_c}
                }
            }
            st.success("Configuration Updated!")

    # --- CAPTAINS TAB ---
    with tab2:
        st.subheader("Assign Captains")
        st.info("Assigning a captain moves them to the team and sets their price.")
        
        cap_team = st.selectbox("Team", TEAM_NAMES)
        cap_sport = st.selectbox("Sport", ["Cricket", "Badminton", "TT"])
        
        unsold_players = st.session_state.players[st.session_state.players['Team'].isna()]
        cap_player_name = st.selectbox("Player", unsold_players['Name'].unique())
        cap_price = st.number_input("Captain Price", min_value=0, value=0)
        
        if st.button("Assign Captain"):
            if cap_player_name:
                idx = st.session_state.players.index[st.session_state.players['Name'] == cap_player_name].tolist()[0]
                st.session_state.players.at[idx, 'Team'] = cap_team
                st.session_state.players.at[idx, 'Price'] = cap_price
                st.session_state.players.at[idx, 'CaptainFor'] = cap_sport
                
                log_activity('captain', f"👑 CAPTAIN: {cap_player_name} assigned to {cap_team} ({cap_sport})")
                st.success(f"{cap_player_name} is now captain of {cap_team}!")
                st.rerun()

    # --- CORRECTION TAB ---
    with tab3:
        st.subheader("Correction Manager")
        
        sold_players = st.session_state.players[st.session_state.players['Team'].notna()]
        
        if not sold_players.empty:
            edit_player_name = st.selectbox("Select Player to Edit/Unsell", sold_players['Name'].unique())
            
            if edit_player_name:
                player_idx = st.session_state.players.index[st.session_state.players['Name'] == edit_player_name].tolist()[0]
                player_data = st.session_state.players.loc[player_idx]
                
                st.write(f"Current Team: **{player_data['Team']}** | Price: **{player_data['Price']}**")
                
                col_fix1, col_fix2 = st.columns(2)
                
                with col_fix1:
                    new_team_fix = st.selectbox("New Team", TEAM_NAMES, index=TEAM_NAMES.index(player_data['Team']))
                    new_price_fix = st.number_input("New Price", value=player_data['Price'])
                    
                    if st.button("Update Details"):
                        st.session_state.players.at[player_idx, 'Team'] = new_team_fix
                        st.session_state.players.at[player_idx, 'Price'] = new_price_fix
                        log_activity('correction', f"🛠️ Correction: {edit_player_name} updated.")
                        st.success("Updated!")
                        st.rerun()
                        
                with col_fix2:
                    st.warning("Danger Zone")
                    if st.button("❌ Unsell / Revert"):
                        st.session_state.players.at[player_idx, 'Team'] = None
                        st.session_state.players.at[player_idx, 'Price'] = 0
                        st.session_state.players.at[player_idx, 'CaptainFor'] = None
                        log_activity('revert', f"❌ Reverted: {edit_player_name} moved to unsold.")
                        st.success("Player reverted to Unsold.")
                        st.rerun()

    # --- DATA TAB ---
    with tab4:
        st.subheader("Data Management")
        uploaded_file = st.file_uploader("Upload Master CSV", type=['csv'])
        if uploaded_file:
            load_data(uploaded_file)
            
        if st.button("Download CSV"):
            csv = st.session_state.players.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="auction_data.csv">Download CSV File</a>'
            st.markdown(href, unsafe_allow_html=True)

        if st.button("Factory Reset (Clear Data)"):
            st.session_state.players = pd.DataFrame(columns=[
                'ID', 'Name', 'Team', 'Price', 'Cricket', 'Badminton', 'TT', 'CaptainFor', 'ContactNo'
            ])
            st.session_state.activity_log = []
            st.rerun()

def developer_profile():
    with st.sidebar:
        st.markdown("### 👨‍💻 Developer")
        
        # Check dev stats
        dev_name = "Abhishek Chandaliya"
        
        # --- THE FIX IS HERE ---
        # We now search in 'Name' because load_data renames 'Player Name' to 'Name'
        dev_data = st.session_state.players[st.session_state.players['Name'].str.contains("Abhishek", case=False, na=False)]
        
        status = "Unsold"
        team = "N/A"
        
        if not dev_data.empty:
            p = dev_data.iloc[0]
            if pd.notna(p['Team']):
                status = "Sold"
                team = p['Team']
        
        st.markdown(f"""
        <div style="background:#1e293b; padding:15px; border-radius:10px; border:1px solid #475569;">
            <div style="display:flex; align-items:center; gap:10px;">
                <div style="width:40px; height:40px; border-radius:50%; background:#6366f1; color:white; display:flex; align-items:center; justify-content:center; font-weight:bold;">AC</div>
                <div>
                    <div style="font-weight:bold; color:white;">{dev_name}</div>
                    <div style="font-size:0.8rem; color:#94a3b8;">Auction Architect</div>
                </div>
            </div>
            <hr style="border-color:#334155; margin:10px 0;">
            <div style="font-size:0.85rem;">
                <span style="color:#64748b;">Status:</span> <b style="color:{'#10b981' if status=='Sold' else '#f59e0b'}">{status}</b><br>
                <span style="color:#64748b;">Team:</span> <b style="color:white;">{team}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 📜 Recent Activity")
        for log in st.session_state.activity_log[:5]:
            icon = "💰" if log['type'] == 'sale' else ("❌" if log['type'] == 'revert' else "📝")
            st.markdown(f"<div style='font-size:0.8rem; margin-bottom:5px;'>{icon} {log['message']} <span style='color:#64748b; font-size:0.7rem;'>({log['time']})</span></div>", unsafe_allow_html=True)

# ==========================================
# 8. MAIN APP LOGIC
# ==========================================

def main():
    init_session_state()
    
    # Safely load developer profile (wrapped in try/except just in case)
    try:
        developer_profile()
    except:
        # Fallback if data isn't loaded yet
        with st.sidebar:
            st.write("Developer: Abhishek Chandaliya")

    # Navigation
    tabs = st.tabs(["📊 Dashboard", "⚖️ Auction Console", "👥 Teams", "⚙️ Settings"])
    
    with tabs[0]:
        render_dashboard()
        
    with tabs[1]:
        render_auction_console()
        
    with tabs[2]:
        render_roster_view()
        
    with tabs[3]:
        render_settings()

if __name__ == "__main__":
    main()
