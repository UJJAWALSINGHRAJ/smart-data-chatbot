import re
import sqlite3
from difflib import SequenceMatcher

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Smart Data Assistant",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ----------------------------
# Database helpers
# ----------------------------
def run_query(query: str) -> pd.DataFrame:
    conn = sqlite3.connect("olist_ecommerce.db")
    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


def get_kpis():
    total_orders = run_query("SELECT COUNT(*) AS value FROM orders").iloc[0, 0]
    total_payments = run_query("SELECT COUNT(*) AS value FROM payments").iloc[0, 0]
    total_reviews = run_query("SELECT COUNT(*) AS value FROM reviews").iloc[0, 0]
    total_states = run_query(
        "SELECT COUNT(DISTINCT customer_state) AS value FROM customers"
    ).iloc[0, 0]
    return total_orders, total_payments, total_reviews, total_states


def format_number(value):
    try:
        value = int(value)
        if value >= 1_000_000:
            return f"{value/1_000_000:.1f}M+"
        if value >= 1_000:
            return f"{value/1_000:.0f}K+"
        return str(value)
    except Exception:
        return str(value)


# ----------------------------
# Text helpers
# ----------------------------
def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s?]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def contains_any(text: str, patterns: list[str]) -> bool:
    return any(p in text for p in patterns)


# ----------------------------
# Intent detection
# ----------------------------
def detect_intent(user_input: str) -> str:
    text = normalize_text(user_input)

    general_patterns = {
        "greeting": [
            "hi", "hello", "hey", "hii", "heyy",
            "good morning", "good afternoon", "good evening"
        ],
        "how_are_you": [
            "how are you", "how r you", "how are u", "kaise ho", "kese ho"
        ],
        "who_are_you": [
            "who are you", "what are you", "tell me about yourself"
        ],
        "thanks": [
            "thank you", "thanks", "thnx", "thanku"
        ],
        "bye": [
            "bye", "goodbye", "see you", "see you later"
        ],
        "project_explain": [
            "what is this project", "explain this project", "about this project",
            "what does this app do", "tell me about this project",
            "what is smart data assistant"
        ],
        "sql_explain": [
            "what is sql", "define sql", "explain sql", "sql meaning"
        ],
        "help": [
            "help", "what can you do", "supported questions", "commands"
        ],
    }

    data_patterns = {
        "total_orders": [
            "total orders", "how many orders", "orders count", "number of orders",
            "count orders", "total order"
        ],
        "total_revenue": [
            "total revenue", "show revenue", "sales amount", "total sales",
            "revenue amount", "how much revenue", "sales revenue"
        ],
        "top_cities": [
            "top 5 cities", "top cities", "best cities", "city with highest orders",
            "which city has highest orders", "top cities by orders", "city orders"
        ],
        "payment_method": [
            "payment method", "payment type", "payment distribution",
            "payment breakup", "payment trend", "show payment methods"
        ],
        "reviews_summary": [
            "reviews summary", "review summary", "review score", "customer reviews",
            "summarize review scores", "review distribution"
        ],
        "top_products": [
            "top products", "best products", "most ordered products",
            "popular products", "highest ordered products"
        ],
        "total_customers": [
            "total customers", "how many customers", "customers count",
            "customer count", "number of customers"
        ],
        "states": [
            "states", "state count", "customer states", "state distribution",
            "customers by state"
        ],
        "average_payment": [
            "average payment", "avg payment", "mean payment", "average payment value"
        ],
        "monthly_trend": [
            "monthly trend", "monthly orders", "order trend",
            "monthly sales trend", "orders by month", "month wise orders"
        ],
    }

    for intent, patterns in general_patterns.items():
        if contains_any(text, patterns):
            return intent

    for intent, patterns in data_patterns.items():
        if contains_any(text, patterns):
            return intent

    if "order" in text and ("count" in text or "how many" in text or "total" in text):
        return "total_orders"
    if "revenue" in text or ("sales" in text and "trend" not in text):
        return "total_revenue"
    if "city" in text or "cities" in text:
        return "top_cities"
    if "payment" in text:
        return "payment_method"
    if "review" in text:
        return "reviews_summary"
    if "product" in text:
        return "top_products"
    if "customer" in text and "state" in text:
        return "states"
    if "customer" in text:
        return "total_customers"
    if "month" in text or "trend" in text:
        return "monthly_trend"

    best_intent = "unknown"
    best_score = 0.0

    for intent, patterns in data_patterns.items():
        for pattern in patterns:
            score = similarity(text, pattern)
            if score > best_score:
                best_score = score
                best_intent = intent

    if best_score >= 0.82:
        return best_intent

    return "unknown"


# ----------------------------
# Multi-question splitter
# ----------------------------
def split_multi_input(user_input: str) -> list[str]:
    raw = user_input.strip()

    if not raw:
        return []

    # Strong split by punctuation first
    parts = re.split(r"[?!.]+", raw)
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) > 1:
        return parts[:5]

    # Soft split by connectors
    text = normalize_text(raw)

    split_markers = [
        " and ",
        " also ",
        " then ",
    ]

    segments = [text]
    for marker in split_markers:
        new_segments = []
        for seg in segments:
            if marker in seg:
                new_segments.extend([s.strip() for s in seg.split(marker) if s.strip()])
            else:
                new_segments.append(seg)
        segments = new_segments

    # Extra split when multiple known questions are chained
    trigger_phrases = [
        "hello", "how are you", "who are you", "what is sql", "explain this project",
        "how many orders", "total orders", "total revenue", "payment method",
        "reviews summary", "monthly trend", "top cities", "which city has highest orders"
    ]

    final_parts = []
    for seg in segments:
        found_positions = []
        for phrase in trigger_phrases:
            idx = seg.find(phrase)
            if idx != -1:
                found_positions.append((idx, phrase))

        found_positions.sort()

        if len(found_positions) <= 1:
            final_parts.append(seg.strip())
        else:
            for i, (start, phrase) in enumerate(found_positions):
                end = found_positions[i + 1][0] if i + 1 < len(found_positions) else len(seg)
                piece = seg[start:end].strip()
                if piece:
                    final_parts.append(piece)

    cleaned = []
    for item in final_parts:
        item = item.strip()
        if item and item not in cleaned:
            cleaned.append(item)

    return cleaned[:5]


# ----------------------------
# Single response engine
# ----------------------------
def get_single_response(user_input: str):
    intent = detect_intent(user_input)

    if intent == "greeting":
        return {
            "text": "Hello! I’m Smart Data Assistant. How can I help you today?",
            "df": None,
            "sql": None,
            "chart": None,
            "summary": "You can ask me normal questions or business data questions."
        }

    if intent == "how_are_you":
        return {
            "text": "I’m fine, thank you! How can I help you today?",
            "df": None,
            "sql": None,
            "chart": None,
            "summary": "You can ask me about orders, revenue, payments, reviews, cities, products, or this project."
        }

    if intent == "who_are_you":
        return {
            "text": "I’m Smart Data Assistant, an AI-style SQL analytics chatbot built for business data insights.",
            "df": None,
            "sql": None,
            "chart": None,
            "summary": "I can answer general questions and also analyze the e-commerce database."
        }

    if intent == "thanks":
        return {
            "text": "You’re welcome!",
            "df": None,
            "sql": None,
            "chart": None,
            "summary": "Ask another question whenever you’re ready."
        }

    if intent == "bye":
        return {
            "text": "Goodbye! Have a great day.",
            "df": None,
            "sql": None,
            "chart": None,
            "summary": ""
        }

    if intent == "project_explain":
        return {
            "text": "This project is a Smart Data Assistant built with Python, Streamlit, SQLite, and a real e-commerce dataset.",
            "df": None,
            "sql": None,
            "chart": None,
            "summary": "It answers business questions using SQL queries, charts, and insight summaries."
        }

    if intent == "sql_explain":
        return {
            "text": "SQL stands for Structured Query Language.",
            "df": None,
            "sql": None,
            "chart": None,
            "summary": "It is used to store, manage, and query data from databases. In this project, SQL is used to generate business insights."
        }

    if intent == "help":
        return {
            "text": "I can help with both general conversation and business data analysis.",
            "df": None,
            "sql": None,
            "chart": None,
            "summary": "Try asking: total orders, total revenue, top 5 cities, payment method, reviews summary, top products, total customers, states, average payment, monthly trend."
        }

    if intent == "total_orders":
        query = """
        SELECT COUNT(*) AS total_orders
        FROM orders
        """
        return {
            "text": "Here is the total number of orders.",
            "df": run_query(query),
            "sql": query,
            "chart": None,
            "summary": "The platform has processed a large number of orders, which shows strong transaction activity."
        }

    if intent == "total_revenue":
        query = """
        SELECT ROUND(SUM(payment_value), 2) AS total_revenue
        FROM payments
        """
        return {
            "text": "Here is the total revenue.",
            "df": run_query(query),
            "sql": query,
            "chart": None,
            "summary": "This value shows the total payment volume captured in the dataset."
        }

    if intent == "top_cities":
        query = """
        SELECT c.customer_city, COUNT(o.order_id) AS total_orders
        FROM customers c
        JOIN orders o
            ON c.customer_id = o.customer_id
        GROUP BY c.customer_city
        ORDER BY total_orders DESC
        LIMIT 5
        """
        df = run_query(query)
        top_city = df.iloc[0, 0]
        top_orders = df.iloc[0, 1]
        return {
            "text": "These are the top 5 cities by number of orders.",
            "df": df,
            "sql": query,
            "chart": "bar",
            "summary": f"{top_city} is the leading city with {top_orders} orders among the top 5 cities."
        }

    if intent == "payment_method":
        query = """
        SELECT payment_type, COUNT(*) AS total_count
        FROM payments
        GROUP BY payment_type
        ORDER BY total_count DESC
        """
        df = run_query(query)
        top_method = df.iloc[0, 0]
        top_count = df.iloc[0, 1]
        return {
            "text": "Here is the payment method distribution.",
            "df": df,
            "sql": query,
            "chart": "bar",
            "summary": f"The most used payment method is {top_method}, with {top_count} transactions."
        }

    if intent == "reviews_summary":
        query = """
        SELECT review_score, COUNT(*) AS total_reviews
        FROM reviews
        GROUP BY review_score
        ORDER BY review_score
        """
        df = run_query(query)
        top_score = df.loc[df["total_reviews"].idxmax(), "review_score"]
        top_count = df.loc[df["total_reviews"].idxmax(), "total_reviews"]
        return {
            "text": "Here is the reviews summary by score.",
            "df": df,
            "sql": query,
            "chart": "bar",
            "summary": f"Review score {top_score} appears most often, with {top_count} reviews."
        }

    if intent == "top_products":
        query = """
        SELECT
            oi.product_id,
            COUNT(*) AS total_orders
        FROM order_items oi
        GROUP BY oi.product_id
        ORDER BY total_orders DESC
        LIMIT 10
        """
        return {
            "text": "These are the top ordered products.",
            "df": run_query(query),
            "sql": query,
            "chart": "bar",
            "summary": "These products appear most frequently in customer orders, which suggests high demand."
        }

    if intent == "total_customers":
        query = """
        SELECT COUNT(*) AS total_customers
        FROM customers
        """
        return {
            "text": "Here is the total number of customers.",
            "df": run_query(query),
            "sql": query,
            "chart": None,
            "summary": "This shows the total customer records available in the dataset."
        }

    if intent == "states":
        query = """
        SELECT customer_state, COUNT(*) AS total_customers
        FROM customers
        GROUP BY customer_state
        ORDER BY total_customers DESC
        """
        df = run_query(query)
        top_state = df.iloc[0, 0]
        top_state_count = df.iloc[0, 1]
        return {
            "text": "Here is the customer distribution by state.",
            "df": df,
            "sql": query,
            "chart": "bar",
            "summary": f"{top_state} has the highest customer count with {top_state_count} customers."
        }

    if intent == "average_payment":
        query = """
        SELECT ROUND(AVG(payment_value), 2) AS average_payment_value
        FROM payments
        """
        return {
            "text": "Here is the average payment value.",
            "df": run_query(query),
            "sql": query,
            "chart": None,
            "summary": "This indicates the average amount paid per payment record."
        }

    if intent == "monthly_trend":
        query = """
        SELECT
            substr(order_purchase_timestamp, 1, 7) AS order_month,
            COUNT(*) AS total_orders
        FROM orders
        GROUP BY substr(order_purchase_timestamp, 1, 7)
        ORDER BY order_month
        """
        return {
            "text": "Here is the monthly order trend.",
            "df": run_query(query),
            "sql": query,
            "chart": "line",
            "summary": "This trend shows how order volume changes month by month."
        }

    return {
        "text": "I did not fully understand that question yet.",
        "df": None,
        "sql": None,
        "chart": None,
        "summary": "Please ask in another way. Example: how are you, what is sql, explain this project, how many orders do we have, total revenue, payment method, or monthly trend."
    }


# ----------------------------
# Chart rendering
# ----------------------------
def show_chart(df: pd.DataFrame, chart_type: str):
    if df is None or df.empty or len(df.columns) < 2 or not chart_type:
        return

    chart_df = df.copy()
    first_col = chart_df.columns[0]
    second_col = chart_df.columns[1]

    if chart_type == "bar":
        chart_df = chart_df.set_index(first_col)
        st.bar_chart(chart_df[second_col])

    elif chart_type == "line":
        chart_df = chart_df.set_index(first_col)
        st.line_chart(chart_df[second_col])


# ----------------------------
# UI Styling
# ----------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at 10% 10%, rgba(0, 255, 200, 0.10), transparent 22%),
        radial-gradient(circle at 90% 20%, rgba(120, 119, 255, 0.16), transparent 28%),
        radial-gradient(circle at 50% 100%, rgba(255, 0, 128, 0.10), transparent 25%),
        linear-gradient(135deg, #060816 0%, #0b1020 45%, #0a0f1c 100%);
    color: white;
}

section[data-testid="stSidebar"] {
    background: rgba(8, 12, 26, 0.92);
    border-right: 1px solid rgba(255,255,255,0.06);
}

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 1rem;
    max-width: 1400px;
}

.hero {
    overflow: hidden;
    padding: 42px 42px 34px 42px;
    border-radius: 30px;
    background:
        linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03)),
        linear-gradient(120deg, rgba(34,211,238,0.08), rgba(168,85,247,0.08));
    border: 1px solid rgba(255,255,255,0.08);
    box-shadow: 0 20px 50px rgba(0,0,0,0.30);
    margin-bottom: 24px;
}

.tag {
    display: inline-block;
    padding: 8px 15px;
    border-radius: 999px;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.10);
    color: #cbd5e1;
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 18px;
}

.hero-title {
    font-size: 62px;
    line-height: 1.0;
    font-weight: 800;
    letter-spacing: -1.8px;
    margin-bottom: 16px;
    max-width: 780px;
}

.hero-gradient {
    background: linear-gradient(90deg, #ffffff 0%, #8be9fd 35%, #c084fc 75%, #ffffff 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.hero-text {
    color: #cbd5e1;
    font-size: 18px;
    line-height: 1.7;
    max-width: 760px;
    margin-bottom: 22px;
}

.hero-mini {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
}

.mini-pill {
    padding: 11px 14px;
    border-radius: 14px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    color: #e5e7eb;
    font-size: 14px;
    font-weight: 500;
}

.kpi {
    background: linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.04));
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 24px;
    padding: 26px 24px;
    min-height: 150px;
    box-shadow: 0 14px 30px rgba(0,0,0,0.22);
}

.kpi-icon {
    font-size: 28px;
    margin-bottom: 14px;
}

.kpi-value {
    font-size: 38px;
    font-weight: 800;
    margin-bottom: 6px;
}

.kpi-label {
    color: #cbd5e1;
    font-size: 15px;
    font-weight: 500;
}

.panel {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 24px;
    padding: 24px;
    box-shadow: 0 10px 26px rgba(0,0,0,0.20);
    height: 100%;
}

.panel-title {
    font-size: 24px;
    font-weight: 700;
    margin-bottom: 14px;
}

.prompt-btn {
    display: inline-block;
    margin: 6px 8px 0 0;
    padding: 11px 15px;
    border-radius: 999px;
    background: rgba(13, 18, 35, 0.88);
    border: 1px solid rgba(255,255,255,0.10);
    color: #f1f5f9;
    font-size: 14px;
}

.note {
    color: #94a3b8;
    font-size: 13px;
    margin-top: 14px;
}

.side-top {
    font-size: 26px;
    font-weight: 800;
    color: white;
    margin-bottom: 2px;
}

.side-sub {
    color: #94a3b8;
    font-size: 13px;
    margin-bottom: 18px;
}

.side-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 20px;
    padding: 16px;
    margin-bottom: 14px;
}

.side-head {
    font-weight: 700;
    font-size: 15px;
    margin-bottom: 10px;
    color: white;
}

.side-line {
    color: #dbe4ee;
    font-size: 14px;
    margin-bottom: 8px;
}

.creator {
    margin-top: 18px;
    padding: 14px;
    border-radius: 16px;
    background: linear-gradient(135deg, rgba(34,197,94,0.18), rgba(14,165,233,0.16));
    border: 1px solid rgba(255,255,255,0.08);
    color: white;
    font-weight: 700;
}

.chat-tip {
    text-align: center;
    color: #94a3b8;
    font-size: 13px;
    margin-top: 6px;
}
</style>
""", unsafe_allow_html=True)

total_orders, total_payments, total_reviews, total_states = get_kpis()

with st.sidebar:
    st.markdown('<div class="side-top">⚡ Smart AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="side-sub">Analytics-first chatbot experience</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="side-card">
        <div class="side-head">Quick Prompts</div>
        <div class="side-line">• hello</div>
        <div class="side-line">• how are you</div>
        <div class="side-line">• what is sql</div>
        <div class="side-line">• explain this project</div>
        <div class="side-line">• how many orders do we have?</div>
        <div class="side-line">• which city has highest orders?</div>
        <div class="side-line">• total orders and total revenue</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="side-card">
        <div class="side-head">Core Stack</div>
        <div class="side-line">• Python + Streamlit</div>
        <div class="side-line">• SQLite + SQL</div>
        <div class="side-line">• Multi-question support</div>
        <div class="side-line">• Charts + insights</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="creator">🚀 Built by Ujjawal Kumar</div>', unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <div class="tag">AI-Style Business Intelligence</div>
    <div class="hero-title">Ask your data.<br><span class="hero-gradient">Get decisions.</span></div>
    <div class="hero-text">
        Smart Data Assistant supports related answers for general chat, project questions, business analytics, and even multiple questions in one input.
    </div>
    <div class="hero-mini">
        <div class="mini-pill">🤖 General Chat</div>
        <div class="mini-pill">📊 SQL Analytics</div>
        <div class="mini-pill">📈 Charts</div>
        <div class="mini-pill">🧠 Multi-Question Support</div>
    </div>
</div>
""", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="kpi">
        <div class="kpi-icon">📦</div>
        <div class="kpi-value">{format_number(total_orders)}</div>
        <div class="kpi-label">Orders</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="kpi">
        <div class="kpi-icon">💳</div>
        <div class="kpi-value">{format_number(total_payments)}</div>
        <div class="kpi-label">Payments</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="kpi">
        <div class="kpi-icon">⭐</div>
        <div class="kpi-value">{format_number(total_reviews)}</div>
        <div class="kpi-label">Reviews</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="kpi">
        <div class="kpi-icon">🌍</div>
        <div class="kpi-value">{format_number(total_states)}</div>
        <div class="kpi-label">States</div>
    </div>
    """, unsafe_allow_html=True)

left, right = st.columns([1.25, 1])

with left:
    st.markdown("""
    <div class="panel">
        <div class="panel-title">Supported Now</div>
        <span class="prompt-btn">General questions</span>
        <span class="prompt-btn">Project explanation</span>
        <span class="prompt-btn">Business data queries</span>
        <span class="prompt-btn">Charts</span>
        <span class="prompt-btn">Multi-question input</span>
        <div class="note">This version can answer multiple related questions written in one input.</div>
    </div>
    """, unsafe_allow_html=True)

with right:
    st.markdown("""
    <div class="panel">
        <div class="panel-title">How it works</div>
        <div class="side-line">• Splits multiple questions from one input</div>
        <div class="side-line">• Detects general and data intents separately</div>
        <div class="side-line">• Runs safe SQL for data questions</div>
        <div class="side-line">• Returns related output only</div>
    </div>
    """, unsafe_allow_html=True)

user_input = st.chat_input("Ask anything...")

if user_input:
    with st.chat_message("user"):
        st.write(user_input)

    parts = split_multi_input(user_input)

    with st.chat_message("assistant"):
        if len(parts) > 1:
            st.write(f"I found {len(parts)} questions in your input. Here are the answers:")
        elif len(parts) == 1:
            st.write("Here is the answer to your question:")
        else:
            st.write("Please enter a question.")

        for i, part in enumerate(parts, start=1):
            result = get_single_response(part)

            st.markdown(f"### Answer {i}")
            st.write(result["text"])

            if result["df"] is not None:
                st.dataframe(result["df"], use_container_width=True)

                if result["chart"] is not None:
                    st.subheader("Chart View")
                    show_chart(result["df"], result["chart"])

                st.subheader("Quick Insight")
                st.info(result["summary"])

                with st.expander(f"Show SQL Query for Answer {i}"):
                    st.code(result["sql"], language="sql")
            elif result["summary"]:
                st.info(result["summary"])

            if i < len(parts):
                st.markdown("---")

st.markdown(
    '<div class="chat-tip">Try: hello and how are you, or total orders and total revenue, or explain this project and what is sql.</div>',
    unsafe_allow_html=True
)