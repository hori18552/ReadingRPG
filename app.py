import streamlit as st
import json
import os
import uuid
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# --- ページ設定 ---
st.set_page_config(
    page_title="読書RPG - Reading RPG",
    page_icon="📚",
    layout="wide"
)

# --- 定数・設定 ---
MASTER_FILE = "books_master.json"
ASSETS_DIR = "assets"
SPREADSHEET_NAME = "ReadingRPG_Data" # 共有したスプレッドシートの名前

# 初期データ構造
INITIAL_DATA = {
    "user": {
        "level": 1,
        "exp": 0,
        "next_level_exp": 250,
        "combo": 0,
        "last_read_date": None,
        "job": "見習い (Novice)",
        "total_investment": 0,
        "total_hours": 0.0,
        "weapons": []
    },
    "books": [],
    "logs": []
}

# --- ジャンル・データ定義 (変更なし) ---
GENRES = {
    "ビジネス": ["business_basic", "business_strategy", "business_marketing", "business_finance", "business_organization", "business_leadership", "business_decision", "business_general"],
    "教養": ["liberal_philosophy", "liberal_history", "liberal_psychology", "liberal_medicine", "liberal_engineering", "liberal_biology", "liberal_anthropology"]
}

ALL_GENRES = []
for category_genres in GENRES.values():
    ALL_GENRES.extend(category_genres)

WEAPON_MAP = {
    "liberal_philosophy": "杖 (Staff)", "liberal_history": "巻物 (Scroll)", "liberal_psychology": "鏡 (Mirror)",
    "liberal_medicine": "薬瓶 (Potion)", "liberal_engineering": "ガジェット銃 (Gun)", "liberal_biology": "使い魔 (Pet)", "liberal_anthropology": "コンパス (Compass)"
}

GENRE_NAMES = {
    "liberal_philosophy": "哲学", "liberal_history": "歴史", "liberal_psychology": "心理学", "liberal_medicine": "医学",
    "liberal_engineering": "工学", "liberal_biology": "生物学", "liberal_anthropology": "文化人類学"
}

WEAPON_ICONS = {
    "杖 (Staff)": "🪄", "巻物 (Scroll)": "📜", "鏡 (Mirror)": "🪞", "薬瓶 (Potion)": "🧪",
    "ガジェット銃 (Gun)": "🔫", "使い魔 (Pet)": "🐾", "コンパス (Compass)": "🧭"
}

GENRE_TO_JOB = {
    ("business_strategy", "business_marketing"): "騎士 (Knight)",
    ("business_finance", "business_organization"): "参謀 (Tactician)",
    ("business_leadership", "business_decision"): "聖騎士 (Paladin)",
    ("business_general",): "賢者 (Sage)"
}

# --- Google Sheets 接続関数 ---
@st.cache_resource
def get_gspread_client():
    """Google Sheetsへの接続クライアントを取得（キャッシュ対応）"""
    try:
        # StreamlitのSecretsから認証情報を取得
        key_dict = json.loads(st.secrets["gcp_service_account"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Google Cloud接続エラー: {e}")
        return None

def load_data() -> Dict:
    """スプレッドシートからデータを読み込む"""
    client = get_gspread_client()
    if not client:
        return INITIAL_DATA.copy()
    
    try:
        # スプレッドシートを開く
        sheet = client.open(SPREADSHEET_NAME).sheet1
        # A1セルの値（JSON文字列）を取得
        json_str = sheet.acell('A1').value
        
        if not json_str:
            # データがない場合は初期データを返す
            return INITIAL_DATA.copy()
        
        data = json.loads(json_str)
        
        # データの整合性チェックと補完（旧load_dataのロジックを統合）
        if "user" not in data:
             data["user"] = INITIAL_DATA["user"].copy()
        if "books" not in data:
            data["books"] = []
        if "logs" not in data:
            data["logs"] = []
            
        # user内のキー不足を補完
        user = data["user"]
        default_user = INITIAL_DATA["user"]
        for key in default_user:
            if key not in user:
                user[key] = default_user[key]
        
        return data

    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"スプレッドシート『{SPREADSHEET_NAME}』が見つかりません。Google側で作成し、Botのアドレスを招待してください。")
        return INITIAL_DATA.copy()
    except Exception as e:
        # まだデータがない場合など
        return INITIAL_DATA.copy()

def save_data(data: Dict):
    """スプレッドシートにデータを保存する"""
    client = get_gspread_client()
    if not client:
        st.error("保存に失敗しました（接続エラー）")
        return

    try:
        sheet = client.open(SPREADSHEET_NAME).sheet1
        # データをJSON文字列に変換
        json_str = json.dumps(data, ensure_ascii=False)
        
        # A1セルに書き込み
        sheet.update_acell('A1', json_str)
        
    except Exception as e:
        st.error(f"データ保存エラー: {e}")

# --- 以下、ロジック関数（変更なし） ---

def get_today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def calculate_combo(user_data: Dict, read_date: str) -> int:
    last_date = user_data.get("last_read_date")
    if last_date is None:
        return 1
    try:
        last = datetime.strptime(last_date, "%Y-%m-%d")
        current = datetime.strptime(read_date, "%Y-%m-%d")
        diff = (current - last).days
        if diff == 0 or diff == 1:
            return user_data.get("combo", 0) + 1
        else:
            return 1
    except:
        return 1

def get_combo_multiplier(combo_days: int) -> float:
    multiplier = 1.0 + (combo_days * 0.1)
    return min(multiplier, 1.5)

def calculate_level_up(user_data: Dict, exp_gained: int) -> Dict:
    new_exp = user_data["exp"] + exp_gained
    new_level = user_data["level"]
    next_level_exp = user_data["next_level_exp"]
    while new_exp >= next_level_exp:
        new_exp -= next_level_exp
        new_level += 1
        next_level_exp = 250 # 固定あるいは計算式
    user_data["exp"] = new_exp
    user_data["level"] = new_level
    user_data["next_level_exp"] = next_level_exp
    return user_data

def count_basic_books(data: Dict) -> int:
    count = 0
    for book in data.get("books", []):
        if book.get("genre") == "business_basic" and book.get("read_count", 0) > 0:
            count += 1
    return count

def get_player_avatar_path(data: Dict) -> str:
    basic_count = count_basic_books(data)
    user = data.get("user", {})
    if basic_count < 6:
        level_num = min(basic_count + 1, 6)
        filename = f"novice_lv{level_num}.png"
    else:
        job_class = user.get("job", "見習い (Novice)")
        level = user.get("level", 1)
        if "騎士" in job_class or "Knight" in job_class:
            prefix = "knight"
        elif "参謀" in job_class or "Tactician" in job_class:
            prefix = "tactician"
        elif "聖騎士" in job_class or "Paladin" in job_class:
            prefix = "paladin"
        elif "賢者" in job_class or "Sage" in job_class:
            prefix = "sage"
        else:
            prefix = "novice"
        
        if level < 54: suffix = "lv1"
        elif level < 126: suffix = "lv2"
        else: suffix = "lv3"
        filename = f"{prefix}_{suffix}.png"
    return os.path.join(ASSETS_DIR, filename)

def display_player_avatar(data: Dict):
    try:
        avatar_path = get_player_avatar_path(data)
        if os.path.exists(avatar_path):
            st.sidebar.image(avatar_path, width=200, use_container_width=True)
        else:
            fallback_path = os.path.join(ASSETS_DIR, "novice_lv1.png")
            if os.path.exists(fallback_path):
                st.sidebar.image(fallback_path, width=200, use_container_width=True)
            else:
                st.sidebar.info("アバター画像が見つかりません")
    except Exception as e:
        st.sidebar.error(f"画像読み込みエラー: {e}")

def get_enemy_avatar_path(total_pages: int) -> str:
    if total_pages < 100: filename = "enemy_swarm.png"
    elif total_pages < 200: filename = "enemy_slime.png"
    elif total_pages < 300: filename = "enemy_mimic.png"
    elif total_pages < 400: filename = "enemy_golem.png"
    elif total_pages < 500: filename = "enemy_dragon.png"
    else: filename = "enemy_demon.png"
    return os.path.join(ASSETS_DIR, filename)

def display_enemy_avatar(total_pages: int):
    try:
        enemy_path = get_enemy_avatar_path(total_pages)
        if os.path.exists(enemy_path):
            st.image(enemy_path, width=150, use_container_width=False)
        else:
            fallback_path = os.path.join(ASSETS_DIR, "enemy_swarm.png")
            if os.path.exists(fallback_path):
                st.image(fallback_path, width=150, use_container_width=False)
            else:
                st.info("敵画像が見つかりません")
    except Exception as e:
        st.error(f"画像読み込みエラー: {e}")

def update_job_class(data: Dict):
    genre_count = {}
    for book in data.get("books", []):
        if book.get("read_count", 0) > 0:
            genre = book.get("genre", "")
            genre_count[genre] = genre_count.get(genre, 0) + 1
    if not genre_count: return
    max_genre = max(genre_count.items(), key=lambda x: x[1])[0]
    new_job = "見習い (Novice)"
    for genres, job in GENRE_TO_JOB.items():
        if max_genre in genres:
            new_job = job
            break
    data["user"]["job"] = new_job

def get_next_book_id(books: List[Dict]) -> int:
    if not books: return 1
    return max(b.get("id", 0) for b in books) + 1

def load_master_data() -> List[Dict]:
    try:
        if os.path.exists(MASTER_FILE):
            with open(MASTER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except: pass
    return []

def acquire_weapon(user: Dict, genre: str) -> Optional[str]:
    if genre in WEAPON_MAP:
        weapon = WEAPON_MAP[genre]
        if "weapons" not in user: user["weapons"] = []
        user["weapons"].append(weapon)
        return weapon
    return None

def get_weapon_genre_name(weapon: str) -> str:
    for genre, weapon_name in WEAPON_MAP.items():
        if weapon_name == weapon:
            return GENRE_NAMES.get(genre, genre)
    return ""

def display_result_screen(completed_data: Dict, data: Dict):
    st.balloons()
    st.title("🎉 CONGRATULATIONS! 読破おめでとうございます！")
    st.divider()
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("倒した敵")
        display_enemy_avatar(completed_data.get("book_max_hp", 0))
    with col2:
        st.subheader(completed_data.get("book_title", ""))
        st.caption(f"ジャンル: {completed_data.get('book_genre', '')}")
    st.divider()
    st.subheader("📊 獲得報酬")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("獲得経験値", f"{completed_data.get('exp_gained', 0)} EXP")
    if completed_data.get("leveled_up", False):
        old_level = completed_data.get("old_level", 1)
        new_level = completed_data.get("new_level", 1)
        with col2:
            st.markdown(f"### 🎯 LEVEL UP!")
            st.markdown(f"**Lv {old_level} → Lv {new_level}**")
    else:
        with col2:
            st.metric("現在のレベル", completed_data.get("new_level", 1))
    acquired_weapon = completed_data.get("acquired_weapon")
    if acquired_weapon:
        with col3:
            st.markdown("### 🎁 ITEM GET!")
            weapon_icon = WEAPON_ICONS.get(acquired_weapon, "⚔️")
            genre_name = get_weapon_genre_name(acquired_weapon)
            st.markdown(f"**{weapon_icon} {acquired_weapon}**")
            if genre_name: st.caption(f"[{genre_name}]")
    else:
        with col3:
            st.metric("獲得武器", "なし")
    st.divider()
    st.subheader("📝 レビューを記録")
    with st.form("result_review_form"):
        review_good = st.text_area("良かった点", key="result_review_good")
        review_learn = st.text_area("学び", key="result_review_learn")
        review_action = st.text_area("ネクストアクション", key="result_review_action")
        submitted = st.form_submit_button("冒険を続ける（完了）", use_container_width=True)
        if submitted:
            book_id = completed_data.get("book_id")
            if book_id:
                for b in data.get("books", []):
                    if b["id"] == book_id:
                        b["review"] = {"good": review_good, "learn": review_learn, "action": review_action}
                        break
                save_data(data)
            if "completed_book_data" in st.session_state:
                del st.session_state.completed_book_data
            st.rerun()

def main():
    st.title("📚 読書RPG - Cloud ver.")
    
    # データ読み込み（スプレッドシートから）
    data = load_data()
    
    # --- リザルト画面チェック ---
    if "completed_book_data" in st.session_state and st.session_state.completed_book_data:
        display_result_screen(st.session_state.completed_book_data, data)
        return

    # --- サイドバー ---
    display_player_avatar(data)
    st.sidebar.divider()
    
    user = data.get("user", {})
    weapons = user.get("weapons", [])
    
    with st.sidebar.expander("🎒 所持アイテム / 装備"):
        if weapons:
            weapon_counter = Counter(weapons)
            for weapon, count in weapon_counter.items():
                weapon_icon = WEAPON_ICONS.get(weapon, "⚔️")
                genre_name = get_weapon_genre_name(weapon)
                st.write(f"{weapon_icon} {weapon}" + (f" - [{genre_name}]" if genre_name else "") + f" **x {count}**")
        else:
            st.info("まだアイテムを持っていません")
    
    st.sidebar.divider()
    st.sidebar.title("メニュー")
    sidebar_tab = st.sidebar.radio("選択", ["記録", "管理"])
    
    # --- メインヘッダー ---
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        st.metric("レベル", user.get("level", 1))
    with col2:
        st.metric("職業", user.get("job", "見習い (Novice)"))
        exp_progress = user.get("exp", 0) / user.get("next_level_exp", 250)
        st.progress(exp_progress)
        st.caption(f"経験値: {user.get('exp', 0)} / {user.get('next_level_exp', 250)} EXP")
    with col3:
        combo_days = user.get("combo", 0)
        if combo_days > 1:
            combo_mult = get_combo_multiplier(combo_days)
            st.info(f"🔥 {combo_days}日連続")
            st.caption(f"EXP {combo_mult:.1f}倍")
        else:
            st.info("📖 読書開始")
    
    st.divider()
    main_tab = st.tabs(["ステータス", "履歴・分析", "本棚"])
    
    # --- タブ1: ステータス ---
    with main_tab[0]:
        if sidebar_tab == "記録":
            st.header("📖 読書記録")
            active_books = [b for b in data.get("books", []) if b.get("status") in ["active", "reread"]]
            
            if not active_books:
                st.warning("現在攻略中の本がありません。「管理」タブから本を開始してください。")
            else:
                book_options = {}
                for b in active_books:
                    status_label = "再読中" if b.get("status") == "reread" else ""
                    display_name = f"{b['title']} " + (f"({status_label}) " if status_label else "") + f"(残り{b['current_hp']}/{b['max_hp']}ページ)"
                    book_options[display_name] = b["id"]
                
                selected_title = st.selectbox("読書する本を選択", options=list(book_options.keys()))
                selected_book_id = book_options.get(selected_title) if selected_title else None
                
                if selected_book_id:
                    book = next((b for b in data["books"] if b["id"] == selected_book_id), None)
                    if book:
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.subheader("敵")
                            display_enemy_avatar(book["max_hp"])
                        with col2:
                            st.subheader(book["title"])
                            st.caption(f"ジャンル: {book.get('genre', '')} | 総ページ数: {book['max_hp']}ページ")
                            current_hp = book.get("current_hp", book["max_hp"])
                            st.progress(current_hp / book["max_hp"])
                            st.caption(f"残りHP: {int(current_hp)}/{book['max_hp']}")
                        
                        st.divider()
                        
                        with st.form(key=f"reading_form_{book['id']}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                pages_input = st.number_input("読んだページ数", min_value=1, max_value=min(book["current_hp"], book["max_hp"]), value=min(10, book["current_hp"]))
                                minutes_input = st.number_input("読書時間（分）", min_value=0, value=0)
                            with col2:
                                rating_input = st.selectbox("評価（1-5星）", options=[0, 1, 2, 3, 4, 5], format_func=lambda x: f"{x}星" if x > 0 else "未評価")
                                memo_input = st.text_area("メモ", height=100)
                            
                            submitted = st.form_submit_button("📖 読書記録（攻撃）", use_container_width=True)
                            
                            if submitted:
                                if pages_input > book["current_hp"]:
                                    st.error(f"残りページ数（{book['current_hp']}ページ）を超えています。")
                                else:
                                    read_date = get_today_str()
                                    new_combo = calculate_combo(user, read_date)
                                    user["combo"] = new_combo
                                    user["last_read_date"] = read_date
                                    combo_mult = get_combo_multiplier(new_combo)
                                    
                                    damage = pages_input
                                    exp_gained = int(pages_input * combo_mult)
                                    
                                    user = calculate_level_up(user, exp_gained)
                                    book["current_hp"] = max(0, book["current_hp"] - damage)
                                    if minutes_input > 0:
                                        user["total_hours"] = user.get("total_hours", 0.0) + (minutes_input / 60.0)
                                    if rating_input > 0: book["rating"] = rating_input
                                    
                                    log_entry = {
                                        "id": str(uuid.uuid4()), "date": read_date, "book_id": book["id"],
                                        "pages": pages_input, "minutes": minutes_input, "exp_gained": exp_gained,
                                        "rating": rating_input, "memo": memo_input
                                    }
                                    data["logs"].append(log_entry)
                                    
                                    old_level = user.get("level", 1)
                                    leveled_up = False
                                    
                                    if book["current_hp"] <= 0:
                                        book["status"] = "completed"
                                        book["read_count"] = book.get("read_count", 0) + 1
                                        user["total_investment"] = user.get("total_investment", 0) + book.get("price", 0)
                                        update_job_class(data)
                                        new_level = user.get("level", 1)
                                        leveled_up = (new_level > old_level)
                                        book_genre = book.get("genre", "")
                                        acquired_weapon = acquire_weapon(user, book_genre)
                                        
                                        st.session_state.completed_book_data = {
                                            "book_id": book["id"], "book_title": book.get("title", ""),
                                            "book_genre": book_genre, "book_max_hp": book.get("max_hp", 0),
                                            "exp_gained": exp_gained, "old_level": old_level, "new_level": new_level,
                                            "leveled_up": leveled_up, "acquired_weapon": acquired_weapon
                                        }
                                    
                                    data["user"] = user
                                    save_data(data)
                                    st.rerun()

        elif sidebar_tab == "管理":
            st.header("📚 書籍管理")
            management_tab = st.tabs(["新規追加", "編集・削除"])
            
            with management_tab[0]:
                st.subheader("新規書籍の追加")
                master_books = load_master_data()
                
                # Session State Initialize
                if "new_title" not in st.session_state: st.session_state.new_title = ""
                if "new_genre" not in st.session_state: st.session_state.new_genre = ALL_GENRES[0] if ALL_GENRES else ""
                if "new_pages" not in st.session_state: st.session_state.new_pages = 300
                if "new_price" not in st.session_state: st.session_state.new_price = 0
                if "master_select_idx" not in st.session_state: st.session_state.master_select_idx = 0

                if master_books:
                    master_options = ["マスタから選ぶ（任意）"] + [f"{b.get('title', '')} ({b.get('genre', '')})" for b in master_books]
                    selected_master_idx = st.selectbox("マスタから選ぶ（任意）", options=range(len(master_options)), format_func=lambda x: master_options[x], key="master_select")
                    
                    if selected_master_idx != st.session_state.master_select_idx:
                        st.session_state.master_select_idx = selected_master_idx
                        if selected_master_idx > 0:
                            m_book = master_books[selected_master_idx - 1]
                            st.session_state.new_title = m_book.get("title", "")
                            if m_book.get("genre") in ALL_GENRES: st.session_state.new_genre = m_book.get("genre")
                            st.session_state.new_pages = m_book.get("pages", 300)
                            st.session_state.new_price = m_book.get("price", 0)

                st.divider()

                def add_new_book():
                    title = st.session_state.new_title
                    genre = st.session_state.new_genre
                    pages = st.session_state.new_pages
                    price = st.session_state.new_price
                    if not title or not genre or pages <= 0:
                        st.session_state.add_error = "入力内容を確認してください"
                        return
                    
                    current_data = load_data()
                    new_book = {
                        "id": get_next_book_id(current_data.get("books", [])),
                        "title": title, "genre": genre, "max_hp": pages, "current_hp": pages,
                        "price": price, "status": "active", "rating": 0,
                        "review": {"good": "", "learn": "", "action": ""}, "read_count": 0
                    }
                    current_data["books"].append(new_book)
                    save_data(current_data)
                    st.session_state.add_success = f"『{title}』を追加しました"
                    st.session_state.new_title = ""

                st.text_input("タイトル *", key="new_title")
                st.selectbox("ジャンル *", options=ALL_GENRES, key="new_genre")
                st.number_input("ページ数 *", min_value=1, key="new_pages")
                st.number_input("価格（円）", min_value=0, key="new_price")
                
                if "add_error" in st.session_state and st.session_state.add_error:
                    st.error(st.session_state.add_error)
                    del st.session_state.add_error
                if "add_success" in st.session_state and st.session_state.add_success:
                    st.success(st.session_state.add_success)
                    del st.session_state.add_success
                
                st.button("追加", on_click=add_new_book, use_container_width=True)

            with management_tab[1]:
                st.subheader("書籍の編集・削除")
                books = data.get("books", [])
                if not books:
                    st.info("本がありません")
                else:
                    book_options = {f"{b['title']} ({b.get('status', 'unread')})": b["id"] for b in books}
                    selected_title = st.selectbox("編集する本を選択", options=list(book_options.keys()), key="edit_target_select")
                    selected_book_id = book_options.get(selected_title) if selected_title else None
                    
                    if selected_book_id:
                        book = next((b for b in books if b["id"] == selected_book_id), None)
                        if book:
                            if "last_edit_target" not in st.session_state or st.session_state.last_edit_target != selected_title:
                                st.session_state.edit_title = book.get("title", "")
                                st.session_state.edit_genre = book.get("genre", "")
                                st.session_state.edit_max_hp = book.get("max_hp", 300)
                                st.session_state.edit_current_hp = book.get("current_hp", 300)
                                st.session_state.edit_price = book.get("price", 0)
                                st.session_state.edit_status = book.get("status", "unread")
                                st.session_state.last_edit_target = selected_title
                            
                            with st.form("edit_book_form"):
                                st.write(f"ID: {book['id']}")
                                new_title = st.text_input("タイトル", key="edit_title")
                                new_genre = st.selectbox("ジャンル", options=ALL_GENRES, index=ALL_GENRES.index(st.session_state.edit_genre) if st.session_state.edit_genre in ALL_GENRES else 0, key="edit_genre")
                                col1, col2 = st.columns(2)
                                with col1:
                                    new_max_hp = st.number_input("総ページ数", min_value=1, key="edit_max_hp")
                                    new_current_hp = st.number_input("現在のHP", min_value=0, max_value=new_max_hp, key="edit_current_hp")
                                with col2:
                                    new_price = st.number_input("価格", min_value=0, key="edit_price")
                                    status_opts = ["unread", "active", "completed", "reread"]
                                    new_status = st.selectbox("ステータス", options=status_opts, index=status_opts.index(st.session_state.edit_status) if st.session_state.edit_status in status_opts else 0, key="edit_status")
                                
                                c1, c2 = st.columns(2)
                                save = c1.form_submit_button("保存", use_container_width=True)
                                delete = c2.form_submit_button("削除", use_container_width=True)
                                
                                if save:
                                    book["title"] = new_title
                                    book["genre"] = new_genre
                                    book["max_hp"] = new_max_hp
                                    book["current_hp"] = new_current_hp
                                    book["price"] = new_price
                                    book["status"] = new_status
                                    save_data(data)
                                    st.success("保存しました")
                                    st.rerun()
                                if delete:
                                    data["books"] = [b for b in data["books"] if b["id"] != book["id"]]
                                    data["logs"] = [l for l in data["logs"] if l.get("book_id") != book["id"]]
                                    save_data(data)
                                    st.success("削除しました")
                                    st.rerun()

    # --- タブ2: 履歴・分析 ---
    with main_tab[1]:
        st.header("📊 履歴・分析")
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("総投資額", f"¥{user.get('total_investment', 0):,}")
        with col2: st.metric("総読書時間", f"{user.get('total_hours', 0.0):.1f}時間")
        with col3: st.metric("読了書籍数", f"{len([b for b in data.get('books', []) if b.get('status') == 'completed'])}冊")
        
        st.divider()
        st.subheader("読書ログ")
        logs = data.get("logs", [])
        if not logs:
            st.info("記録がありません")
        else:
            logs_data = []
            for log in logs:
                b = next((b for b in data.get("books", []) if b["id"] == log.get("book_id")), None)
                logs_data.append({
                    "日付": log.get("date"), "書籍": b.get("title", "不明") if b else "不明",
                    "P": log.get("pages"), "分": log.get("minutes"), "EXP": log.get("exp_gained")
                })
            st.dataframe(pd.DataFrame(logs_data), use_container_width=True)

    # --- タブ3: 本棚 ---
    with main_tab[2]:
        st.header("📚 本棚")
        status_filter = st.selectbox("フィルタ", ["全て", "未読", "読書中", "読了", "再読中"])
        books = data.get("books", [])
        filtered_books = books
        if status_filter == "未読": filtered_books = [b for b in books if b.get("status") == "unread"]
        elif status_filter == "読書中": filtered_books = [b for b in books if b.get("status") == "active"]
        elif status_filter == "読了": filtered_books = [b for b in books if b.get("status") == "completed"]
        elif status_filter == "再読中": filtered_books = [b for b in books if b.get("status") == "reread"]
        
        for book in filtered_books:
            with st.expander(f"{book['title']} ({book.get('status')})"):
                st.write(f"ジャンル: {book.get('genre')} | P: {book['max_hp']}")
                if book.get("review", {}).get("good"): st.write(f"Good: {book['review']['good']}")

if __name__ == "__main__":
    main()