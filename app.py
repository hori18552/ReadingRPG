import streamlit as st
import json
import os
import uuid
import pandas as pd
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# ページ設定
st.set_page_config(
    page_title="読書RPG - Reading RPG",
    page_icon="📚",
    layout="wide"
)

# データファイルのパス
DATA_FILE = "reading_data.json"
MASTER_FILE = "books_master.json"
ASSETS_DIR = "assets"

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

# ジャンル定義
GENRES = {
    "ビジネス": [
        "business_basic",
        "business_strategy",
        "business_marketing",
        "business_finance",
        "business_organization",
        "business_leadership",
        "business_decision",
        "business_general"
    ],
    "教養": [
        "liberal_philosophy",
        "liberal_history",
        "liberal_psychology",
        "liberal_medicine",
        "liberal_engineering",
        "liberal_biology",
        "liberal_anthropology"
    ]
}

# 全ジャンルリスト（フラット）
ALL_GENRES = []
for category_genres in GENRES.values():
    ALL_GENRES.extend(category_genres)

# 武器対応表
WEAPON_MAP = {
    "liberal_philosophy": "杖 (Staff)",
    "liberal_history": "巻物 (Scroll)",
    "liberal_psychology": "鏡 (Mirror)",
    "liberal_medicine": "薬瓶 (Potion)",
    "liberal_engineering": "ガジェット銃 (Gun)",
    "liberal_biology": "使い魔 (Pet)",
    "liberal_anthropology": "コンパス (Compass)"
}

# ジャンル名の日本語マッピング
GENRE_NAMES = {
    "liberal_philosophy": "哲学",
    "liberal_history": "歴史",
    "liberal_psychology": "心理学",
    "liberal_medicine": "医学",
    "liberal_engineering": "工学",
    "liberal_biology": "生物学",
    "liberal_anthropology": "文化人類学"
}

# 武器アイコンマッピング
WEAPON_ICONS = {
    "杖 (Staff)": "🪄",
    "巻物 (Scroll)": "📜",
    "鏡 (Mirror)": "🪞",
    "薬瓶 (Potion)": "🧪",
    "ガジェット銃 (Gun)": "🔫",
    "使い魔 (Pet)": "🐾",
    "コンパス (Compass)": "🧭"
}

# ジャンル別職業マッピング
GENRE_TO_JOB = {
    ("business_strategy", "business_marketing"): "騎士 (Knight)",
    ("business_finance", "business_organization"): "参謀 (Tactician)",
    ("business_leadership", "business_decision"): "聖騎士 (Paladin)",
    ("business_general",): "賢者 (Sage)"
}

def load_data() -> Dict:
    """データを読み込む（互換性処理付き）"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 旧形式からの移行処理
                if "user" not in data:
                    # 旧形式のデータを新形式に変換
                    data = migrate_old_data(data)
                # キー不足を補完
                if "books" not in data:
                    data["books"] = []
                if "logs" not in data:
                    data["logs"] = []
                if "user" not in data:
                    data["user"] = INITIAL_DATA["user"].copy()
                # user内のキー不足を補完
                user = data["user"]
                default_user = INITIAL_DATA["user"]
                for key in default_user:
                    if key not in user:
                        user[key] = default_user[key]
                # weaponsがリストでない場合は初期化
                if "weapons" not in user or not isinstance(user["weapons"], list):
                    user["weapons"] = []
                return data
        except Exception as e:
            st.error(f"データ読み込みエラー: {e}")
            return INITIAL_DATA.copy()
    else:
        return INITIAL_DATA.copy()

def migrate_old_data(old_data: Dict) -> Dict:
    """旧形式のデータを新形式に移行"""
    new_data = INITIAL_DATA.copy()
    
    # user情報の移行
    if "level" in old_data:
        new_data["user"]["level"] = old_data.get("level", 1)
    if "current_exp" in old_data:
        new_data["user"]["exp"] = old_data.get("current_exp", 0)
    if "next_level_exp" in old_data:
        new_data["user"]["next_level_exp"] = old_data.get("next_level_exp", 250)
    if "combo_days" in old_data:
        new_data["user"]["combo"] = old_data.get("combo_days", 0)
    if "last_read_date" in old_data:
        new_data["user"]["last_read_date"] = old_data.get("last_read_date")
    if "job_class" in old_data:
        new_data["user"]["job"] = old_data.get("job_class", "見習い (Novice)")
    
    # books_master.jsonから書籍情報を読み込む（存在する場合）
    master_file = "books_master.json"
    if os.path.exists(master_file):
        try:
            with open(master_file, "r", encoding="utf-8") as f:
                master_books = json.load(f)
                for book in master_books:
                    new_book = {
                        "id": book.get("id"),
                        "title": book.get("title", ""),
                        "genre": book.get("genre", ""),
                        "max_hp": book.get("pages", 0),
                        "current_hp": book.get("current_hp", book.get("pages", 0)),
                        "price": book.get("price", 0),
                        "status": book.get("status", "unread"),
                        "rating": book.get("rating", 0),
                        "review": {
                            "good": book.get("review", {}).get("good", ""),
                            "learn": book.get("review", {}).get("learn", ""),
                            "action": book.get("review", {}).get("action", "")
                        },
                        "read_count": book.get("read_count", 0)
                    }
                    new_data["books"].append(new_book)
        except:
            pass
    
    return new_data

def save_data(data: Dict):
    """データを保存"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"データ保存エラー: {e}")

def get_today_str() -> str:
    """今日の日付をYYYY-MM-DD形式で返す"""
    return datetime.now().strftime("%Y-%m-%d")

def calculate_combo(user_data: Dict, read_date: str) -> int:
    """コンボ日数を計算"""
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
    """コンボ倍率を計算（最大1.5倍）"""
    multiplier = 1.0 + (combo_days * 0.1)
    return min(multiplier, 1.5)

def calculate_level_up(user_data: Dict, exp_gained: int) -> Dict:
    """経験値追加とレベルアップ処理"""
    new_exp = user_data["exp"] + exp_gained
    new_level = user_data["level"]
    next_level_exp = user_data["next_level_exp"]
    
    while new_exp >= next_level_exp:
        new_exp -= next_level_exp
        new_level += 1
        next_level_exp = 250
    
    user_data["exp"] = new_exp
    user_data["level"] = new_level
    user_data["next_level_exp"] = next_level_exp
    
    return user_data

def count_basic_books(data: Dict) -> int:
    """基礎マンダラ（business_basic）の読了数をカウント"""
    count = 0
    for book in data.get("books", []):
        if book.get("genre") == "business_basic" and book.get("read_count", 0) > 0:
            count += 1
    return count

def get_player_avatar_path(data: Dict) -> str:
    """プレイヤーアバターの画像パスを取得"""
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
        
        if level < 54:
            suffix = "lv1"
        elif level < 126:
            suffix = "lv2"
        else:
            suffix = "lv3"
        
        filename = f"{prefix}_{suffix}.png"
    
    return os.path.join(ASSETS_DIR, filename)

def display_player_avatar(data: Dict):
    """プレイヤーアバターを表示"""
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
    """敵アバターの画像パスを取得"""
    if total_pages < 100:
        filename = "enemy_swarm.png"
    elif total_pages < 200:
        filename = "enemy_slime.png"
    elif total_pages < 300:
        filename = "enemy_mimic.png"
    elif total_pages < 400:
        filename = "enemy_golem.png"
    elif total_pages < 500:
        filename = "enemy_dragon.png"
    else:
        filename = "enemy_demon.png"
    
    return os.path.join(ASSETS_DIR, filename)

def display_enemy_avatar(total_pages: int):
    """敵アバターを表示"""
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
    """読了した本のジャンルから職業を判定"""
    genre_count = {}
    for book in data.get("books", []):
        if book.get("read_count", 0) > 0:
            genre = book.get("genre", "")
            genre_count[genre] = genre_count.get(genre, 0) + 1
    
    if not genre_count:
        return
    
    max_genre = max(genre_count.items(), key=lambda x: x[1])[0]
    new_job = "見習い (Novice)"
    
    for genres, job in GENRE_TO_JOB.items():
        if max_genre in genres:
            new_job = job
            break
    
    data["user"]["job"] = new_job

def get_next_book_id(books: List[Dict]) -> int:
    """次の書籍IDを取得"""
    if not books:
        return 1
    return max(b.get("id", 0) for b in books) + 1

def load_master_data() -> List[Dict]:
    """マスタデータを読み込む"""
    try:
        if os.path.exists(MASTER_FILE):
            with open(MASTER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        pass  # エラーにならず空リストを返す
    return []

def acquire_weapon(user: Dict, genre: str) -> Optional[str]:
    """教養書を読破した際に武器を獲得（重複可）"""
    if genre in WEAPON_MAP:
        weapon = WEAPON_MAP[genre]
        if "weapons" not in user:
            user["weapons"] = []
        # 重複チェックを撤廃し、必ず追加
        user["weapons"].append(weapon)
        return weapon
    return None

def get_weapon_genre_name(weapon: str) -> str:
    """武器名からジャンル名（日本語）を取得"""
    for genre, weapon_name in WEAPON_MAP.items():
        if weapon_name == weapon:
            return GENRE_NAMES.get(genre, genre)
    return ""

def display_result_screen(completed_data: Dict, data: Dict):
    """読破リザルト画面を表示"""
    st.balloons()
    
    st.title("🎉 CONGRATULATIONS! 読破おめでとうございます！")
    st.divider()
    
    # 倒した敵（本）の情報
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("倒した敵")
        display_enemy_avatar(completed_data.get("book_max_hp", 0))
    
    with col2:
        st.subheader(completed_data.get("book_title", ""))
        st.caption(f"ジャンル: {completed_data.get('book_genre', '')}")
    
    st.divider()
    
    # 獲得報酬
    st.subheader("📊 獲得報酬")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("獲得経験値", f"{completed_data.get('exp_gained', 0)} EXP")
    
    # レベルアップ表示
    if completed_data.get("leveled_up", False):
        old_level = completed_data.get("old_level", 1)
        new_level = completed_data.get("new_level", 1)
        with col2:
            st.markdown(f"### 🎯 LEVEL UP!")
            st.markdown(f"**Lv {old_level} → Lv {new_level}**")
    else:
        with col2:
            st.metric("現在のレベル", completed_data.get("new_level", 1))
    
    # 武器獲得表示
    acquired_weapon = completed_data.get("acquired_weapon")
    if acquired_weapon:
        with col3:
            st.markdown("### 🎁 ITEM GET!")
            weapon_icon = WEAPON_ICONS.get(acquired_weapon, "⚔️")
            genre_name = get_weapon_genre_name(acquired_weapon)
            if genre_name:
                st.markdown(f"**{weapon_icon} {acquired_weapon}**")
                st.caption(f"[{genre_name}]")
            else:
                st.markdown(f"**{weapon_icon} {acquired_weapon}**")
    else:
        with col3:
            st.metric("獲得武器", "なし")
    
    st.divider()
    
    # レビュー入力フォーム
    st.subheader("📝 レビューを記録")
    
    with st.form("result_review_form"):
        review_good = st.text_area("良かった点", key="result_review_good")
        review_learn = st.text_area("学び", key="result_review_learn")
        review_action = st.text_area("ネクストアクション", key="result_review_action")
        
        submitted = st.form_submit_button("冒険を続ける（完了）", use_container_width=True)
        
        if submitted:
            # レビューを保存
            book_id = completed_data.get("book_id")
            if book_id:
                for b in data.get("books", []):
                    if b["id"] == book_id:
                        b["review"] = {
                            "good": review_good,
                            "learn": review_learn,
                            "action": review_action
                        }
                        break
                save_data(data)
            
            # リザルト画面をクリア
            if "completed_book_data" in st.session_state:
                del st.session_state.completed_book_data
            
            st.rerun()

def main():
    st.title("📚 読書RPG - Reading RPG")
    
    # データ読み込み
    data = load_data()
    
    # リザルト画面チェック（最優先）
    if "completed_book_data" in st.session_state and st.session_state.completed_book_data:
        display_result_screen(st.session_state.completed_book_data, data)
        return
    
    # サイドバー
    display_player_avatar(data)
    st.sidebar.divider()
    
    # 所持アイテム一覧
    user = data.get("user", {})
    weapons = user.get("weapons", [])
    
    with st.sidebar.expander("🎒 所持アイテム / 装備"):
        if weapons:
            # Counterを使ってアイテムの個数を集計
            weapon_counter = Counter(weapons)
            for weapon, count in weapon_counter.items():
                weapon_icon = WEAPON_ICONS.get(weapon, "⚔️")
                genre_name = get_weapon_genre_name(weapon)
                if genre_name:
                    st.write(f"{weapon_icon} {weapon} - [{genre_name}] **x {count}**")
                else:
                    st.write(f"{weapon_icon} {weapon} **x {count}**")
        else:
            st.info("まだアイテムを持っていません")
    
    st.sidebar.divider()
    
    st.sidebar.title("メニュー")
    sidebar_tab = st.sidebar.radio("選択", ["記録", "管理"])
    
    # メイン画面のヘッダー
    user = data.get("user", {})
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
    
    # メイン画面のタブ
    main_tab = st.tabs(["ステータス", "履歴・分析", "本棚"])
    
    # タブ1: ステータス
    with main_tab[0]:
        if sidebar_tab == "記録":
            st.header("📖 読書記録")
            
            # 現在攻略中の本を選択（active または reread）
            active_books = [b for b in data.get("books", []) if b.get("status") in ["active", "reread"]]
            
            if not active_books:
                st.warning("現在攻略中の本がありません。「管理」タブから本を開始してください。")
            else:
                if "selected_book_id" not in st.session_state:
                    st.session_state.selected_book_id = active_books[0].get("id")
                
                # ドロップダウンの表示名を生成（再読中の場合は表示を工夫）
                book_options = {}
                for b in active_books:
                    status_label = "再読中" if b.get("status") == "reread" else ""
                    if status_label:
                        display_name = f"{b['title']} ({status_label}) (残り{b['current_hp']}/{b['max_hp']}ページ)"
                    else:
                        display_name = f"{b['title']} (残り{b['current_hp']}/{b['max_hp']}ページ)"
                    book_options[display_name] = b["id"]
                selected_title = st.selectbox(
                    "読書する本を選択",
                    options=list(book_options.keys()),
                    index=0 if active_books else None
                )
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
                            hp_ratio = current_hp / book["max_hp"]
                            st.progress(hp_ratio)
                            st.caption(f"残りHP: {int(current_hp)}/{book['max_hp']}")
                        
                        st.divider()
                        
                        # 読書記録フォーム
                        with st.form(key=f"reading_form_{book['id']}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                pages_input = st.number_input(
                                    "読んだページ数",
                                    min_value=1,
                                    max_value=min(book["current_hp"], book["max_hp"]),
                                    value=min(10, book["current_hp"]),
                                    key=f"pages_{book['id']}"
                                )
                                minutes_input = st.number_input(
                                    "読書時間（分）",
                                    min_value=0,
                                    value=0,
                                    key=f"minutes_{book['id']}"
                                )
                            
                            with col2:
                                rating_input = st.selectbox(
                                    "評価（1-5星）",
                                    options=[0, 1, 2, 3, 4, 5],
                                    format_func=lambda x: f"{x}星" if x > 0 else "未評価",
                                    key=f"rating_{book['id']}"
                                )
                                memo_input = st.text_area(
                                    "メモ",
                                    key=f"memo_{book['id']}",
                                    height=100
                                )
                            
                            submitted = st.form_submit_button("📖 読書記録（攻撃）", use_container_width=True)
                            
                            if submitted:
                                if pages_input > book["current_hp"]:
                                    st.error(f"残りページ数（{book['current_hp']}ページ）を超えています。")
                                else:
                                    read_date = get_today_str()
                                    
                                    # コンボ計算
                                    new_combo = calculate_combo(user, read_date)
                                    user["combo"] = new_combo
                                    user["last_read_date"] = read_date
                                    
                                    # コンボ倍率
                                    combo_mult = get_combo_multiplier(new_combo)
                                    
                                    # ダメージとEXP
                                    damage = pages_input
                                    exp_gained = int(pages_input * combo_mult)
                                    
                                    # 経験値追加とレベルアップ
                                    user = calculate_level_up(user, exp_gained)
                                    
                                    # 本のHPを更新
                                    book["current_hp"] = max(0, book["current_hp"] - damage)
                                    
                                    # 読書時間を累計
                                    if minutes_input > 0:
                                        user["total_hours"] = user.get("total_hours", 0.0) + (minutes_input / 60.0)
                                    
                                    # 評価を更新（最新の評価を保持）
                                    if rating_input > 0:
                                        book["rating"] = rating_input
                                    
                                    # ログに記録
                                    log_entry = {
                                        "id": str(uuid.uuid4()),
                                        "date": read_date,
                                        "book_id": book["id"],
                                        "pages": pages_input,
                                        "minutes": minutes_input,
                                        "exp_gained": exp_gained,
                                        "rating": rating_input,
                                        "memo": memo_input
                                    }
                                    data["logs"].append(log_entry)
                                    
                                    # 読了判定
                                    old_level = user.get("level", 1)
                                    leveled_up = False
                                    
                                    if book["current_hp"] <= 0:
                                        book["status"] = "completed"
                                        book["read_count"] = book.get("read_count", 0) + 1
                                        user["total_investment"] = user.get("total_investment", 0) + book.get("price", 0)
                                        update_job_class(data)
                                        
                                        # レベルアップ判定
                                        new_level = user.get("level", 1)
                                        leveled_up = (new_level > old_level)
                                        
                                        # 教養書の場合、武器を獲得
                                        book_genre = book.get("genre", "")
                                        acquired_weapon = acquire_weapon(user, book_genre)
                                        
                                        # リザルト画面用のデータを保存
                                        st.session_state.completed_book_data = {
                                            "book_id": book["id"],
                                            "book_title": book.get("title", ""),
                                            "book_genre": book_genre,
                                            "book_max_hp": book.get("max_hp", 0),
                                            "exp_gained": exp_gained,
                                            "old_level": old_level,
                                            "new_level": new_level,
                                            "leveled_up": leveled_up,
                                            "acquired_weapon": acquired_weapon
                                        }
                                    
                                    # データ保存
                                    data["user"] = user
                                    save_data(data)
                                    
                                    # 読了した場合はリザルト画面に遷移、そうでなければ通常画面に戻る
                                    if book["current_hp"] <= 0:
                                        st.rerun()
                                    else:
                                        st.rerun()
        
        elif sidebar_tab == "管理":
            st.header("📚 書籍管理")
            
            management_tab = st.tabs(["新規追加", "編集・削除"])
            
            with management_tab[0]:
                st.subheader("新規書籍の追加")
                
                # マスタデータ読み込み
                master_books = load_master_data()
                
                # session_stateの初期化
                if "new_title" not in st.session_state:
                    st.session_state.new_title = ""
                if "new_genre" not in st.session_state:
                    st.session_state.new_genre = ALL_GENRES[0] if ALL_GENRES else ""
                if "new_pages" not in st.session_state:
                    st.session_state.new_pages = 300
                if "new_price" not in st.session_state:
                    st.session_state.new_price = 0
                if "master_select_idx" not in st.session_state:
                    st.session_state.master_select_idx = 0
                
                # マスタから選択（フォームの外に配置）
                if master_books:
                    master_options = ["マスタから選ぶ（任意）"] + [f"{b.get('title', '')} ({b.get('genre', '')})" for b in master_books]
                    
                    # 前回の選択インデックスを保存
                    prev_idx = st.session_state.get("master_select_idx", 0)
                    
                    selected_master_idx = st.selectbox(
                        "マスタから選ぶ（任意）",
                        options=range(len(master_options)),
                        format_func=lambda x: master_options[x],
                        key="master_select",
                        index=prev_idx
                    )
                    
                    # マスタ選択が変更された場合、session_stateを更新
                    if selected_master_idx != prev_idx:
                        st.session_state.master_select_idx = selected_master_idx
                        if selected_master_idx > 0:
                            master_selected = master_books[selected_master_idx - 1]
                            if master_selected:
                                st.session_state.new_title = master_selected.get("title", "")
                                selected_genre = master_selected.get("genre", "")
                                if selected_genre in ALL_GENRES:
                                    st.session_state.new_genre = selected_genre
                                else:
                                    st.session_state.new_genre = ALL_GENRES[0] if ALL_GENRES else ""
                                st.session_state.new_pages = master_selected.get("pages", 300)
                                st.session_state.new_price = master_selected.get("price", 0)
                
                st.divider()
                
                # 登録処理を行うコールバック関数
                def add_new_book():
                    # 入力チェック
                    title = st.session_state.get("new_title", "")
                    genre = st.session_state.get("new_genre", "")
                    pages = st.session_state.get("new_pages", 0)
                    price = st.session_state.get("new_price", 0)
                    
                    if not title or not genre or pages <= 0:
                        st.session_state.add_book_error = "タイトル、ジャンル、ページ数は必須です。"
                        return
                    
                    # エラーをクリア
                    st.session_state.add_book_error = None
                    
                    # データ読み込み
                    current_data = load_data()
                    
                    # 新規書籍の作成
                    new_book = {
                        "id": get_next_book_id(current_data.get("books", [])),
                        "title": title,
                        "genre": genre,
                        "max_hp": pages,
                        "current_hp": pages,
                        "price": price,
                        "status": "active",
                        "rating": 0,
                        "review": {
                            "good": "",
                            "learn": "",
                            "action": ""
                        },
                        "read_count": 0
                    }
                    
                    # データに追加
                    current_data["books"].append(new_book)
                    save_data(current_data)
                    
                    # 完了メッセージをsession_stateに保存
                    st.session_state.add_book_success = f"『{title}』を登録しました！"
                    
                    # フォームをクリア（コールバック内なら安全）
                    st.session_state.new_title = ""
                    st.session_state.new_genre = ALL_GENRES[0] if ALL_GENRES else ""
                    st.session_state.new_pages = 300
                    st.session_state.new_price = 0
                    st.session_state.master_select_idx = 0
                
                # フォーム項目（session_stateと連動）
                title = st.text_input(
                    "タイトル *",
                    value=st.session_state.new_title,
                    key="new_title"
                )
                
                # ジャンルをselectboxに変更
                current_genre = st.session_state.new_genre
                genre_index = ALL_GENRES.index(current_genre) if current_genre in ALL_GENRES else 0
                genre = st.selectbox(
                    "ジャンル *",
                    options=ALL_GENRES,
                    index=genre_index,
                    key="new_genre"
                )
                
                pages = st.number_input(
                    "ページ数 *",
                    min_value=1,
                    value=st.session_state.new_pages,
                    key="new_pages"
                )
                price = st.number_input(
                    "価格（円）",
                    min_value=0,
                    value=st.session_state.new_price,
                    key="new_price"
                )
                
                # エラーメッセージ表示
                if "add_book_error" in st.session_state and st.session_state.add_book_error:
                    st.error(st.session_state.add_book_error)
                    st.session_state.add_book_error = None
                
                # 成功メッセージ表示
                if "add_book_success" in st.session_state and st.session_state.add_book_success:
                    st.success(st.session_state.add_book_success)
                    st.toast(st.session_state.add_book_success, icon="✅")
                    st.session_state.add_book_success = None
                    st.rerun()
                
                # ボタンにコールバックを紐付け
                st.button("追加", on_click=add_new_book, use_container_width=True)
            
            with management_tab[1]:
                st.subheader("書籍の編集・削除")
                
                books = data.get("books", [])
                if not books:
                    st.info("登録されている本がありません。")
                else:
                    book_options = {f"{b['title']} ({b.get('status', 'unread')})": b["id"] for b in books}
                    selected_title = st.selectbox("編集する本を選択", options=list(book_options.keys()), key="edit_target_select")
                    selected_book_id = book_options.get(selected_title) if selected_title else None
                    
                    if selected_book_id:
                        book = next((b for b in books if b["id"] == selected_book_id), None)
                        if book:
                            # 選択変更時にフォームの値を強制更新
                            if "last_edit_target" not in st.session_state or st.session_state.last_edit_target != selected_title:
                                st.session_state.edit_title = book.get("title", "")
                                st.session_state.edit_genre = book.get("genre", "")
                                st.session_state.edit_max_hp = book.get("max_hp", 300)
                                st.session_state.edit_current_hp = book.get("current_hp", book.get("max_hp", 300))
                                st.session_state.edit_price = book.get("price", 0)
                                st.session_state.edit_status = book.get("status", "unread")
                                st.session_state.edit_rating = book.get("rating", 0)
                                st.session_state.edit_review_good = book.get("review", {}).get("good", "")
                                st.session_state.edit_review_learn = book.get("review", {}).get("learn", "")
                                st.session_state.edit_review_action = book.get("review", {}).get("action", "")
                                # 最後に選択状態を保存
                                st.session_state.last_edit_target = selected_title
                            
                            with st.form("edit_book_form"):
                                st.write(f"**ID: {book['id']}**")
                                
                                title = st.text_input("タイトル", value=st.session_state.get("edit_title", ""), key="edit_title")
                                
                                # ジャンルをselectboxに変更
                                current_genre = st.session_state.get("edit_genre", "")
                                genre_index = ALL_GENRES.index(current_genre) if current_genre in ALL_GENRES else 0
                                genre = st.selectbox(
                                    "ジャンル",
                                    options=ALL_GENRES,
                                    index=genre_index,
                                    key="edit_genre"
                                )
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    max_hp = st.number_input("総ページ数", min_value=1, value=st.session_state.get("edit_max_hp", 300), key="edit_max_hp")
                                    current_hp = st.number_input("現在のHP", min_value=0, max_value=max_hp, value=st.session_state.get("edit_current_hp", max_hp), key="edit_current_hp")
                                with col2:
                                    price = st.number_input("価格（円）", min_value=0, value=st.session_state.get("edit_price", 0), key="edit_price")
                                    status_options = ["unread", "active", "completed", "reread"]
                                    current_status = st.session_state.get("edit_status", "unread")
                                    status_index = status_options.index(current_status) if current_status in status_options else 0
                                    status = st.selectbox(
                                        "ステータス",
                                        options=status_options,
                                        index=status_index,
                                        key="edit_status"
                                    )
                                
                                rating = st.selectbox(
                                    "評価",
                                    options=[0, 1, 2, 3, 4, 5],
                                    index=st.session_state.get("edit_rating", 0),
                                    format_func=lambda x: f"{x}星" if x > 0 else "未評価",
                                    key="edit_rating"
                                )
                                
                                st.subheader("レビュー")
                                review_good = st.text_area("良かった点", value=st.session_state.get("edit_review_good", ""), key="edit_review_good")
                                review_learn = st.text_area("学び", value=st.session_state.get("edit_review_learn", ""), key="edit_review_learn")
                                review_action = st.text_area("ネクストアクション", value=st.session_state.get("edit_review_action", ""), key="edit_review_action")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    save_btn = st.form_submit_button("保存", use_container_width=True)
                                with col2:
                                    delete_btn = st.form_submit_button("削除", use_container_width=True)
                                
                                if save_btn:
                                    if not title or not genre or max_hp <= 0:
                                        st.error("タイトル、ジャンル、総ページ数は必須です。")
                                    else:
                                        book["title"] = title
                                        book["genre"] = genre
                                        book["max_hp"] = max_hp
                                        book["current_hp"] = min(current_hp, max_hp)
                                        book["price"] = price
                                        book["status"] = status
                                        book["rating"] = rating
                                        book["review"] = {
                                            "good": review_good,
                                            "learn": review_learn,
                                            "action": review_action
                                        }
                                        save_data(data)
                                        st.success("保存しました！")
                                        st.rerun()
                                
                                if delete_btn:
                                    # 関連するログも削除
                                    data["logs"] = [log for log in data["logs"] if log.get("book_id") != book["id"]]
                                    data["books"] = [b for b in data["books"] if b["id"] != book["id"]]
                                    save_data(data)
                                    st.success("削除しました！")
                                    st.rerun()
                            
                            # 再読ボタン（読了済みの場合）
                            if book.get("status") == "completed":
                                if st.button("再読を開始", key=f"reread_edit_{book['id']}"):
                                    book["status"] = "reread"
                                    book["current_hp"] = book["max_hp"]
                                    save_data(data)
                                    st.success("再読を開始しました！")
                                    st.rerun()
    
    # タブ2: 履歴・分析
    with main_tab[1]:
        st.header("📊 履歴・分析")
        
        user = data.get("user", {})
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("総投資額", f"¥{user.get('total_investment', 0):,}")
        with col2:
            total_hours = user.get("total_hours", 0.0)
            st.metric("総読書時間", f"{total_hours:.1f}時間")
        with col3:
            completed_count = len([b for b in data.get("books", []) if b.get("status") == "completed"])
            st.metric("読了書籍数", f"{completed_count}冊")
        
        st.divider()
        
        st.subheader("読書ログ")
        logs = data.get("logs", [])
        
        if not logs:
            st.info("読書記録がありません。")
        else:
            # ログを編集可能なテーブル形式で表示
            logs_df_data = []
            for log in logs:
                book = next((b for b in data.get("books", []) if b["id"] == log.get("book_id")), None)
                book_title = book.get("title", "不明") if book else "不明"
                logs_df_data.append({
                    "ID": log.get("id", ""),
                    "日付": log.get("date", ""),
                    "書籍": book_title,
                    "ページ数": log.get("pages", 0),
                    "時間(分)": log.get("minutes", 0),
                    "獲得EXP": log.get("exp_gained", 0),
                    "評価": f"{log.get('rating', 0)}星" if log.get("rating", 0) > 0 else "未評価",
                    "メモ": log.get("memo", "")
                })
            
            df = pd.DataFrame(logs_df_data)
            
            # 日付カラムをdatetime型に変換
            if not df.empty and "日付" in df.columns:
                df["日付"] = pd.to_datetime(df["日付"], errors='coerce')
            
            # 編集可能なテーブル
            edited_df = st.data_editor(
                df,
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "ID": st.column_config.TextColumn("ID", disabled=True),
                    "日付": st.column_config.DateColumn("日付"),
                    "書籍": st.column_config.TextColumn("書籍", disabled=True),
                    "ページ数": st.column_config.NumberColumn("ページ数", min_value=0),
                    "時間(分)": st.column_config.NumberColumn("時間(分)", min_value=0),
                    "獲得EXP": st.column_config.NumberColumn("獲得EXP", min_value=0),
                    "評価": st.column_config.TextColumn("評価"),
                    "メモ": st.column_config.TextColumn("メモ")
                }
            )
            
            if st.button("変更を保存", use_container_width=True):
                # 編集されたデータを反映
                for idx, row in edited_df.iterrows():
                    log_id = row["ID"]
                    log = next((l for l in logs if l.get("id") == log_id), None)
                    if log:
                        # 日付の更新
                        if pd.notna(row["日付"]):
                            if isinstance(row["日付"], str):
                                log["date"] = row["日付"]
                            else:
                                log["date"] = row["日付"].strftime("%Y-%m-%d")
                        
                        # 数値の更新
                        log["pages"] = int(row["ページ数"]) if pd.notna(row["ページ数"]) else log.get("pages", 0)
                        log["minutes"] = int(row["時間(分)"]) if pd.notna(row["時間(分)"]) else log.get("minutes", 0)
                        log["exp_gained"] = int(row["獲得EXP"]) if pd.notna(row["獲得EXP"]) else log.get("exp_gained", 0)
                        
                        # 評価の更新
                        rating_str = str(row["評価"]) if pd.notna(row["評価"]) else "0"
                        rating = 0
                        if "星" in rating_str:
                            try:
                                rating = int(rating_str.replace("星", ""))
                            except:
                                rating = 0
                        log["rating"] = rating
                        
                        log["memo"] = str(row["メモ"]) if pd.notna(row["メモ"]) else ""
                
                save_data(data)
                st.success("変更を保存しました！")
                st.rerun()
            
            # ログ削除
            st.subheader("ログ削除")
            if logs:
                log_options = {f"{log.get('date', '')} - {next((b.get('title', '不明') for b in data.get('books', []) if b.get('id') == log.get('book_id')), '不明')} ({log.get('pages', 0)}ページ)": log.get('id') for log in logs}
                selected_log_title = st.selectbox("削除するログを選択", options=list(log_options.keys()))
                selected_log_id = log_options.get(selected_log_title) if selected_log_title else None
                
                if selected_log_id and st.button("選択したログを削除", use_container_width=True):
                    data["logs"] = [log for log in logs if log.get("id") != selected_log_id]
                    save_data(data)
                    st.success("ログを削除しました！")
                    st.rerun()
    
    # タブ3: 本棚
    with main_tab[2]:
        st.header("📚 本棚")
        
        books = data.get("books", [])
        if not books:
            st.info("登録されている本がありません。")
        else:
            # ステータスでフィルタ
            status_filter = st.selectbox(
                "ステータスでフィルタ",
                options=["全て", "未読", "読書中", "読了", "再読中"],
                key="status_filter"
            )
            
            filtered_books = books
            if status_filter == "未読":
                filtered_books = [b for b in books if b.get("status") == "unread"]
            elif status_filter == "読書中":
                filtered_books = [b for b in books if b.get("status") == "active"]
            elif status_filter == "読了":
                filtered_books = [b for b in books if b.get("status") == "completed"]
            elif status_filter == "再読中":
                filtered_books = [b for b in books if b.get("status") == "reread"]
            
            for i, book in enumerate(filtered_books):
                with st.expander(f"{book['title']} ({book.get('status', 'unread')})"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**ジャンル:** {book.get('genre', '')}")
                        st.write(f"**ページ数:** {book['max_hp']}ページ")
                        if book.get("status") in ["active", "reread"]:
                            current_hp = book.get("current_hp", book["max_hp"])
                            hp_ratio = current_hp / book["max_hp"]
                            st.progress(hp_ratio)
                            st.caption(f"進捗: {book['max_hp'] - current_hp}/{book['max_hp']}ページ ({((book['max_hp'] - current_hp) / book['max_hp'] * 100):.1f}%)")
                        st.write(f"**価格:** ¥{book.get('price', 0):,}")
                        if book.get("rating", 0) > 0:
                            st.write(f"**評価:** {'⭐' * book['rating']}")
                        if book.get("read_count", 0) > 0:
                            st.write(f"**読了回数:** {book['read_count']}回")
                    
                    with col2:
                        if book.get("status") in ["active", "reread"]:
                            display_enemy_avatar(book["max_hp"])
                    
                    # レビュー表示
                    review = book.get("review", {})
                    if review.get("good") or review.get("learn") or review.get("action"):
                        st.subheader("レビュー")
                        if review.get("good"):
                            st.write("**良かった点:**")
                            st.write(review["good"])
                        if review.get("learn"):
                            st.write("**学び:**")
                            st.write(review["learn"])
                        if review.get("action"):
                            st.write("**ネクストアクション:**")
                            st.write(review["action"])
                    
                    # アクションボタン
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if book.get("status") == "unread":
                            if st.button("開始", key=f"start_{book['id']}_{i}"):
                                # 他のactiveをunreadに戻す（オプション）
                                for b in data["books"]:
                                    if b.get("status") == "active" and b["id"] != book["id"]:
                                        b["status"] = "unread"
                                book["status"] = "active"
                                book["current_hp"] = book["max_hp"]
                                save_data(data)
                                st.rerun()
                    with col2:
                        if book.get("status") == "completed":
                            if st.button("再読", key=f"reread_{book['id']}_{i}"):
                                book["status"] = "reread"
                                book["current_hp"] = book["max_hp"]
                                save_data(data)
                                st.rerun()
                    with col3:
                        if st.button("編集", key=f"edit_{book['id']}_{i}"):
                            st.session_state.edit_book_id = book["id"]
                            st.rerun()

if __name__ == "__main__":
    main()
