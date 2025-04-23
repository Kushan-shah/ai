import shutil
import streamlit as st
from PIL import Image
import pytesseract
import time
import google.generativeai as genai

# ========== ENSURE TESSERACT BINARY ==========
# Fail fast if Tesseract isn’t installed on the host
if not shutil.which("tesseract"):
    st.error("⛔ Tesseract OCR binary not found. Make sure your Aptfile includes:\n\n"
             "  tesseract-ocr\n"
             "  libtesseract-dev")
    st.stop()

# Point pytesseract at the system binary
pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract")

# ========== SETUP AI MODEL ==========
genai.configure(api_key="AIzaSyBUrWiT4phbZT9JKXAG5B8lap6KdHCs1sI")  # Replace with your Gemini key
model = genai.GenerativeModel("models/gemini-1.5-pro-latest")

st.set_page_config("🍳 AI Cooking Assistant", layout="centered")
st.title("🍽️ AI Cooking Dashboard")

# ========== INIT SESSION ==========
if "timers" not in st.session_state:
    st.session_state.timers = {}
if "steps_output" not in st.session_state:
    st.session_state.steps_output = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "trigger_prompt" not in st.session_state:
    st.session_state.trigger_prompt = None

# ========== UTILS ==========
def extract_text_from_image(uploaded_file):
    img = Image.open(uploaded_file)
    return pytesseract.image_to_string(img)

def get_cooking_time(recipe_text):
    try:
        response = model.generate_content(
            f"Estimate total cooking time (in minutes only). Recipe: {recipe_text}"
        )
        return int(''.join(filter(str.isdigit, response.text)))
    except:
        return 10  # fallback

def get_steps(recipe_text):
    response = model.generate_content(
        f"Break this recipe into clear step-by-step instructions with estimated time for each step:\n{recipe_text}"
    )
    return response.text.strip()

def format_time(secs):
    mins = int(secs // 60)
    sec = int(secs % 60)
    return f"{mins:02d}:{sec:02d}"

# ========== RECIPE INPUT ==========
st.markdown("Upload an image or paste a recipe to get started:")
upload = st.file_uploader("📸 Upload Recipe Image", type=["png", "jpg", "jpeg"])
text_input = st.text_area("✍️ Or Paste Recipe")

if upload:
    text_input = extract_text_from_image(upload)
    st.success("✅ Text extracted from image!")

if st.button("🧠 Analyze with AI"):
    if text_input.strip() == "":
        st.warning("Please enter or upload a recipe.")
    else:
        with st.spinner("Analyzing..."):
            time_est = get_cooking_time(text_input)
            steps = get_steps(text_input)
            label = f"🍳 {text_input.split()[0][:15]}..."
            st.session_state.timers[label] = {
                "duration": time_est * 60,
                "remaining": time_est * 60,
                "running": False,
                "paused": False,
                "steps": steps,
                "start_time": None
            }
            st.session_state.steps_output = steps
            st.success(f"✅ Timer for '{label}' added! Duration: {time_est} min")

# ========== MANUAL TIMER ==========
st.subheader("⏲️ Set a Manual Cooking Timer")
manual_label = st.text_input("Label for your dish", "My Dish")
col1, col2 = st.columns(2)
with col1:
    minutes = st.number_input("Minutes", 0, 120, 0)
with col2:
    seconds = st.number_input("Seconds", 0, 59, 0)

if st.button("➕ Add Timer"):
    total_sec = int(minutes * 60 + seconds)
    if manual_label not in st.session_state.timers:
        st.session_state.timers[manual_label] = {
            "duration": total_sec,
            "remaining": total_sec,
            "running": False,
            "paused": False,
            "steps": "",
            "start_time": None
        }
        st.success(f"✅ Timer '{manual_label}' added for {minutes} min {seconds} sec")
    else:
        st.warning("⚠️ A timer with that label already exists!")

# ========== LIVE TIMERS ==========
st.subheader("⏱️ Your Cooking Timers")
remove_keys = []

for label, timer in st.session_state.timers.items():
    with st.container():
        c1, c2, c3 = st.columns([4,1,1])
        with c1:
            if timer["running"] and not timer["paused"]:
                elapsed = time.time() - timer["start_time"]
                timer["remaining"] = max(0, timer["duration"] - elapsed)
                if timer["remaining"] == 0:
                    st.error(f"⏰ '{label}' is DONE!")
                    remove_keys.append(label)
            st.markdown(f"**{label}** — `{format_time(timer['remaining'])}`")
        with c2:
            if not timer["running"]:
                if st.button("▶️ Start", key=f"start_{label}"):
                    timer["start_time"] = time.time()
                    timer["running"] = True
                    timer["paused"] = False
            elif not timer["paused"]:
                if st.button("⏸ Pause", key=f"pause_{label}"):
                    timer["paused"] = True
                    timer["duration"] = timer["remaining"]
                    timer["running"] = False
            else:
                if st.button("▶️ Resume", key=f"resume_{label}"):
                    timer["start_time"] = time.time()
                    timer["running"] = True
                    timer["paused"] = False
        with c3:
            if st.button("🗑 Stop", key=f"stop_{label}"):
                remove_keys.append(label)

for key in remove_keys:
    del st.session_state.timers[key]

# ========== STEP-BY-STEP INSTRUCTIONS ==========
if st.session_state.steps_output:
    st.markdown("---")
    st.subheader("🔪 Step-by-Step Instructions")
    for i, step in enumerate(st.session_state.steps_output.split("\n"), 1):
        if step.strip():
            with st.expander(f"Step {i}"):
                st.write(step.strip())

# ========== INTERACTIVE CHATBOT ==========
st.markdown("---")
st.subheader("💬 Cooking Chat Assistant")
mode = st.radio(
    "Select Chat Mode:",
    ["🍳 Recipe Ideas", "🧠 Cooking Tips", "🧂 Ingredient Substitutes"],
    horizontal=True
)

user_input = st.chat_input("Ask your assistant...")
final_input = user_input or st.session_state.trigger_prompt

if final_input:
    st.chat_message("user").write(final_input)
    prompts = {
        "🍳 Recipe Ideas": "Suggest a recipe idea based on:",
        "🧠 Cooking Tips": "Give a cooking technique or safety tip about:",
        "🧂 Ingredient Substitutes": "Suggest a substitute for:"
    }
    with st.spinner("AI is thinking..."):
        resp = model.generate_content(f"{prompts[mode]} {final_input}")
        reply = resp.text.strip()

    st.chat_message("assistant").markdown(reply)
    st.session_state.chat_history.extend([
        {"role":"user","content":final_input},
        {"role":"assistant","content":reply}
    ])
    st.session_state.trigger_prompt = None

# ========== QUICK CHAT BUTTONS ==========
st.markdown("### ⚡ Quick Chat Prompts")
b1, b2, b3 = st.columns(3)
with b1:
    if st.button("👨‍🍳 Suggest Dinner"):
        st.session_state.trigger_prompt = "What can I make for dinner with rice and tomatoes?"
with b2:
    if st.button("🧂 Replace Garlic"):
        st.session_state.trigger_prompt = "What can I use instead of garlic?"
with b3:
    if st.button("🥗 Healthy Snack"):
        st.session_state.trigger_prompt = "Give me a healthy snack idea under 10 minutes."

# ========== SHOW CHAT HISTORY ==========
with st.expander("📜 Show Full Chat History"):
    for msg in st.session_state.chat_history:
        st.markdown(f"**{msg['role'].capitalize()}**: {msg['content']}")

# ========== CUSTOM STYLING ==========
st.markdown("""
<style>
body, html, [class*="css"] {
    font-family: 'Segoe UI', sans-serif;
    background-color: #fffaf0;
}
h1, h2, h3 {
    color: #ff7043;
}
.stButton>button {
    background-color: #ff7043;
    color: white;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: bold;
}
.stButton>button:hover {
    background-color: #f4511e;
}
</style>
""", unsafe_allow_html=True)
