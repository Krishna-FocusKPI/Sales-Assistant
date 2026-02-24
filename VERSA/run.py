import warnings

from src.common.provider import SUPPORTED_PROVIDERS
from src.utils.initialization import initialization
from src.workflows.workflows import routing
from src.workflows import WorkFlows
import streamlit as st


warnings.filterwarnings("ignore")

PROVIDER_LABELS = {"openai": "OpenAI", "anthropic": "Anthropic"}

# Optional: set to a full image URL for "frosted glass over image" look. Leave "" for solid container.
# Image search ideas: "starry night sky wallpaper", "galaxy nebula background", "fantasy night landscape",
#   "abstract atmospheric background", "dreamy gradient wallpaper", "blurred aesthetic background"
# Starry sky / space image URLs (Unsplash, free to use):
#   https://images.unsplash.com/photo-1462331940025-496dfbfc7564          (galaxy)
#   https://images.unsplash.com/photo-1506318137071-a8e063b4bec0          (starry night)
#   https://images.unsplash.com/photo-1419242902214-272b3f66ee7a          (milky way)
#   https://images.unsplash.com/photo-1534796636912-3b95b3ab5986          (aurora / night sky)
#   https://images.unsplash.com/photo-1446776811953-b23d57bd21af          (stars over mountains)
#   https://images.unsplash.com/photo-1519681393784-d120267933ba          (starry night landscape)
#   https://images.unsplash.com/photo-1543722530-d2c3201371e7            (nebula / space)
#   https://images.unsplash.com/photo-1579546929518-9e396f3cc809          (gradient night sky)
#   https://images.unsplash.com/photo-1518709268805-4e9042af9f23          (milky way 2)
#   https://images.unsplash.com/photo-1507400492013-162706c8c05e          (starry sky)
BACKGROUND_IMAGE_URL = "https://images.unsplash.com/photo-1519681393784-d120267933ba"

# Chat UI: frosted glass container; bubbles/input/dropdown = more opaque so they stand out from background
CHAT_CONTAINER_CSS = """
<style>
/* 0. Hide top toolbar/header bar (Deploy, menu, decoration) */
header[data-testid="stHeader"],
[data-testid="stHeader"],
#MainMenu,
button[title="View fullscreen"],
.stDeployButton,
#stDecoration,
footer[data-testid="stFooter"],
footer {
    visibility: hidden !important;
    display: none !important;
}
/* 0b. Sidebar: balanced glass – see-through + strong blur, text still readable */
section[data-testid="stSidebar"],
section.stSidebar,
[data-testid="stSidebar"] {
    background: rgba(22, 28, 40, 0.72) !important;
    background-color: rgba(22, 28, 40, 0.72) !important;
    backdrop-filter: blur(8px) saturate(140%) !important;
    -webkit-backdrop-filter: blur(8px) saturate(140%) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.15) !important;
}
[data-testid="stSidebar"] > div,
section.stSidebar > div {
    background: transparent !important;
}
/* Left sidebar: keep “End current workflow” button text on one line */
[data-testid="stSidebar"] button,
section[data-testid="stSidebar"] button {
    white-space: nowrap !important;
    min-width: fit-content !important;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
section.stSidebar label,
section.stSidebar p,
section.stSidebar span {
    color: rgba(255, 255, 255, 0.95) !important;
}
/* 1. Disable main scroll: only the chat area should scroll */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > div,
main {
    overflow: hidden !important;
    height: 100vh !important;
    max-height: 100vh !important;
}
/* 1b. Ensure all wrappers are transparent so background image shows through to the glass panel. */
[data-testid="stAppViewContainer"] > div,
main > div,
main > div > div,
section.main,
[data-testid="stAppViewContainer"] section,
section[data-testid="stAppViewContainer"],
div:has(> [data-testid="stMainBlockContainer"]),
div:has(> .block-container) {
    background: transparent !important;
    background-color: transparent !important;
}
/* 2. Main block container: transparent, no overflow so main scroll stays disabled */
[data-testid="stMainBlockContainer"],
[data-testid="stAppViewContainer"] .block-container,
main .block-container,
[data-testid="stAppViewContainer"] [class*="block-container"],
main [class*="block-container"] {
    background: transparent !important;
    background-color: transparent !important;
    padding: 0 !important;
    min-height: auto !important;
    max-height: 100vh !important;
    overflow: hidden !important;
    border: none !important;
    box-shadow: none !important;
}
/* When right sidebar is present: full width and no right padding so sidebar sits at far right */
[data-testid="stAppViewContainer"] .block-container:has([class*="st-key-right_sidebar_panel"]),
main .block-container:has([class*="st-key-right_sidebar_panel"]) {
    max-width: 100% !important;
    padding-left: 1rem !important;
    padding-right: 0 !important;
}
/* 2b. Chat panel only: light frosted glass; fixed height so only chat area scrolls */
[data-testid="stAppViewContainer"] [class*="st-key-chat_glass_panel"],
main [class*="st-key-chat_glass_panel"] {
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.08) 0%, rgba(250, 252, 255, 0.04) 100%) !important;
    background-color: rgba(255, 255, 255, 0.06) !important;
    backdrop-filter: blur(24px) saturate(160%) !important;
    -webkit-backdrop-filter: blur(24px) saturate(160%) !important;
    border-radius: 12px;
    padding: 1.25rem 1.5rem !important;
    margin-top: 0.5rem;
    height: calc(100vh - 2rem) !important;
    max-height: calc(100vh - 2rem) !important;
    min-height: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    overflow: hidden !important;
    width: 100%;
    border: 1px solid rgba(255, 255, 255, 0.28) !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.06) !important;
}
/* 2c. Right sidebar panel: same height as chat panel; top aligned */
[data-testid="stAppViewContainer"] [class*="st-key-right_sidebar_panel"],
main [class*="st-key-right_sidebar_panel"] {
    background: rgba(42, 50, 66, 0.62) !important;
    background-color: rgba(42, 50, 66, 0.62) !important;
    backdrop-filter: blur(8px) saturate(140%) !important;
    -webkit-backdrop-filter: blur(8px) saturate(140%) !important;
    border-radius: 12px 0 0 12px !important;
    border-left: 1px solid rgba(255, 255, 255, 0.15) !important;
    padding: 1.25rem 0.75rem 0.5rem 0.75rem !important;
    margin-top: 0.5rem !important;
    height: calc(100vh - 1.5rem) !important;
    max-height: calc(100vh - 1.5rem) !important;
    min-height: 0 !important;
    box-shadow: -4px 0 24px rgba(0, 0, 0, 0.08) !important;
    margin-right: 0 !important;
}
[data-testid="stAppViewContainer"] [class*="st-key-right_sidebar_panel"] label,
[data-testid="stAppViewContainer"] [class*="st-key-right_sidebar_panel"] p,
[data-testid="stAppViewContainer"] [class*="st-key-right_sidebar_panel"] span,
main [class*="st-key-right_sidebar_panel"] label,
main [class*="st-key-right_sidebar_panel"] p,
main [class*="st-key-right_sidebar_panel"] span {
    color: #fff !important;
    font-weight: 500 !important;
}
[data-testid="stAppViewContainer"] [class*="st-key-right_sidebar_panel"] [data-testid="stMarkdown"] p,
main [class*="st-key-right_sidebar_panel"] [data-testid="stMarkdown"] p {
    color: #fff !important;
    font-weight: 500 !important;
}
[data-testid="stAppViewContainer"] [class*="st-key-right_sidebar_panel"] [data-testid="stAlert"] p,
[data-testid="stAppViewContainer"] [class*="st-key-right_sidebar_panel"] [data-testid="stAlert"] span,
main [class*="st-key-right_sidebar_panel"] [data-testid="stAlert"] p,
main [class*="st-key-right_sidebar_panel"] [data-testid="stAlert"] span {
    color: #fff !important;
    font-weight: 500 !important;
}
/* Right sidebar: minimal gap before Flowchart (after divider) */
[data-testid="stAppViewContainer"] [class*="st-key-right_sidebar_panel"] hr,
main [class*="st-key-right_sidebar_panel"] hr {
    margin: 0.4rem 0 0.35rem 0 !important;
    border-color: rgba(255,255,255,0.2) !important;
}
/* Compact right sidebar: less spacing so content fits without scroll */
[data-testid="stAppViewContainer"] [class*="st-key-right_sidebar_panel"] [data-testid="stVerticalBlock"] > div,
main [class*="st-key-right_sidebar_panel"] [data-testid="stVerticalBlock"] > div {
    margin-top: 0.15rem !important;
    margin-bottom: 0.15rem !important;
}
[data-testid="stAppViewContainer"] [class*="st-key-right_sidebar_panel"] [data-testid="stVerticalBlock"],
main [class*="st-key-right_sidebar_panel"] [data-testid="stVerticalBlock"] {
    gap: 0.2rem !important;
}
[data-testid="stAppViewContainer"] [class*="st-key-right_sidebar_panel"] [data-testid="stMarkdown"] h3,
[data-testid="stAppViewContainer"] [class*="st-key-right_sidebar_panel"] [data-testid="stMarkdown"] h4,
main [class*="st-key-right_sidebar_panel"] [data-testid="stMarkdown"] h3,
main [class*="st-key-right_sidebar_panel"] [data-testid="stMarkdown"] h4 {
    margin-top: 0.35rem !important;
    margin-bottom: 0.25rem !important;
    font-size: 0.95rem !important;
    color: #fff !important;
    font-weight: 600 !important;
}
[data-testid="stAppViewContainer"] [class*="st-key-right_sidebar_panel"] [data-testid="stProgress"] span,
main [class*="st-key-right_sidebar_panel"] [data-testid="stProgress"] span {
    color: #fff !important;
    font-weight: 500 !important;
}
[data-testid="stAppViewContainer"] [class*="st-key-right_sidebar_panel"] [data-testid="stProgress"],
main [class*="st-key-right_sidebar_panel"] [data-testid="stProgress"] {
    margin-top: 0.2rem !important;
    margin-bottom: 0.2rem !important;
}
[data-testid="stAppViewContainer"] [class*="st-key-right_sidebar_panel"] [data-testid="stAlert"],
main [class*="st-key-right_sidebar_panel"] [data-testid="stAlert"] {
    padding: 0.35rem 0.5rem !important;
    margin-top: 0.15rem !important;
    margin-bottom: 0.15rem !important;
}
/* View products buttons: left-aligned */
[data-testid="stAppViewContainer"] [class*="st-key-view_products_buttons"],
main [class*="st-key-view_products_buttons"] {
    display: flex !important;
    flex-direction: column !important;
    align-items: flex-start !important;
}
/* 3. Chat area: scrollable; flex so we can align user right; same height cap as chat panel */
[data-testid="stAppViewContainer"] [class*="st-key-chat_area"],
main [class*="st-key-chat_area"] {
    display: flex !important;
    flex-direction: column !important;
    width: 100% !important;
    flex: 1 1 auto !important;
    min-height: 0 !important;
    max-height: calc(100vh - 2rem) !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    -webkit-overflow-scrolling: touch !important;
}
/* Glass panel inner wrapper: allow flex child to shrink for scroll */
[data-testid="stAppViewContainer"] [class*="st-key-chat_glass_panel"] > div,
main [class*="st-key-chat_glass_panel"] > div {
    min-height: 0 !important;
    flex: 1 1 auto !important;
    display: flex !important;
    flex-direction: column !important;
}
[data-testid="stAppViewContainer"] div:has(> [data-testid="stChatMessage"]),
main div:has(> [data-testid="stChatMessage"]) {
    display: flex !important;
    flex-direction: column !important;
    width: 100%;
}
[data-testid="stAppViewContainer"] [class*="st-key-chat_area"] > div:nth-child(odd),
main [class*="st-key-chat_area"] > div:nth-child(odd) {
    align-self: flex-start !important;
    margin-right: auto !important;
}
[data-testid="stAppViewContainer"] [class*="st-key-chat_area"] > div:nth-child(even),
main [class*="st-key-chat_area"] > div:nth-child(even) {
    align-self: flex-end !important;
    margin-left: auto !important;
}
/* 3. Message bubbles: theme-matching translucent blue-purple (fits chat panel) */
[data-testid="stChatMessage"] {
    border-radius: 1rem;
    padding: 0.6rem 1rem;
    max-width: 82%;
    width: fit-content !important;
    margin-bottom: 0.5rem;
    background: rgba(235, 238, 255, 0.45) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
}
/* 4. AI/assistant: left, pink text, theme-matching bubble */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    background: rgba(232, 230, 255, 0.5) !important;
    color: #c71585 !important;
    align-self: flex-start !important;
    margin-right: auto !important;
    margin-left: 0 !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(255, 255, 255, 0.22) !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) p,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) [data-testid="stMarkdownContainer"],
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) div,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) li {
    color: #c71585 !important;
}
/* 5. User: right, blue text, theme-matching bubble */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: rgba(225, 235, 255, 0.5) !important;
    color: #1a5fb4 !important;
    align-self: flex-end !important;
    margin-left: auto !important;
    margin-right: 0 !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(255, 255, 255, 0.22) !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) p,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stMarkdownContainer"],
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) div {
    color: #1a5fb4 !important;
}
/* 6. Caption and spans/links */
[data-testid="stChatMessage"] [data-testid="stCaptionContainer"],
[data-testid="stChatMessage"] [data-testid="stCaptionContainer"] p {
    color: inherit !important;
    opacity: 0.9;
}
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] a {
    color: inherit !important;
}
/* 6b. Tools used: inside AI bubble, small bold white text */
.tools-used-line,
[data-testid="stAppViewContainer"] .tools-used-line,
main .tools-used-line {
    font-size: 0.65rem !important;
    margin: 0.35rem 0 0.5rem 0 !important;
    padding-left: 0 !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) .tools-used-line,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) .tools-used-line strong {
    color: #fff !important;
}
.tools-used-line strong,
main .tools-used-line strong {
    font-weight: 700 !important;
}
/* 6b2. Fixed-height slot for "Thinking..." so it doesn't push the input down */
[data-testid="stAppViewContainer"] [class*="st-key-thinking_slot"],
main [class*="st-key-thinking_slot"] {
    min-height: 3.5rem !important;
    max-height: 3.5rem !important;
    overflow: hidden !important;
    flex-shrink: 0 !important;
}
/* 6c. Thinking / typing indicator (three bouncing dots) */
.typing-dots span {
    display: inline-block;
    width: 4px;
    height: 4px;
    margin: 0 1px;
    background: currentColor;
    border-radius: 50%;
    animation: typing-bounce 1.4s ease-in-out infinite;
}
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing-bounce {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-4px); }
}
/* 7. Message box (chat input): clearly visible – more opaque gray + gloss, multiple selectors */
[data-testid="stAppViewContainer"] [data-testid="stChatInput"],
main [data-testid="stChatInput"],
[data-testid="stAppViewContainer"] .stChatInputContainer,
main .stChatInputContainer,
[data-testid="stAppViewContainer"] .stChatInputContainer > div,
main .stChatInputContainer > div,
[data-testid="stAppViewContainer"] div[class*="stChatInput"],
main div[class*="stChatInput"] {
    background: rgba(200, 200, 212, 0.85) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.4) !important;
    border-radius: 1rem !important;
    border: 1px solid rgba(180,180,190,0.6) !important;
}
[data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] input,
[data-testid="stChatInput"] [contenteditable],
div[class*="stChatInput"] textarea,
div[class*="stChatInput"] input {
    background: transparent !important;
    color: inherit !important;
}
/* 8. Model provider (selectbox): same visible style – more opaque gray + gloss */
[data-testid="stAppViewContainer"] .block-container [data-testid="stSelectbox"],
main .block-container [data-testid="stSelectbox"],
[data-testid="stAppViewContainer"] .block-container [data-testid="stSelectbox"] > div,
main .block-container [data-testid="stSelectbox"] > div,
[data-testid="stAppViewContainer"] .block-container div[class*="stSelectbox"],
main .block-container div[class*="stSelectbox"] {
    background: rgba(200, 200, 212, 0.85) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.4) !important;
    border-radius: 1rem !important;
    border: 1px solid rgba(180,180,190,0.6) !important;
}
main .block-container [data-testid="stSelectbox"] [class*="control"],
main .block-container div[class*="stSelectbox"] [class*="control"] {
    background: transparent !important;
    border: none !important;
}
/* Chat header row: align title and model provider dropdown on same baseline */
[data-testid="stAppViewContainer"] [class*="st-key-chat_glass_panel"] [data-testid="stHorizontalBlock"]:first-of-type,
main [class*="st-key-chat_glass_panel"] [data-testid="stHorizontalBlock"]:first-of-type {
    display: flex !important;
    align-items: center !important;
    flex-wrap: nowrap !important;
}
/* Header provider: no gray container – only the dropdown visible; pushed far right */
[data-testid="stAppViewContainer"] [class*="st-key-chat_glass_panel"] [data-testid="stHorizontalBlock"]:first-of-type > div:last-child,
main [class*="st-key-chat_glass_panel"] [data-testid="stHorizontalBlock"]:first-of-type > div:last-child,
[data-testid="stAppViewContainer"] [class*="st-key-chat_glass_panel"] [data-testid="stHorizontalBlock"]:first-of-type > div:last-child > div,
main [class*="st-key-chat_glass_panel"] [data-testid="stHorizontalBlock"]:first-of-type > div:last-child > div,
[data-testid="stAppViewContainer"] [class*="st-key-header_provider"],
main [class*="st-key-header_provider"] {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
[data-testid="stAppViewContainer"] [class*="st-key-chat_glass_panel"] [data-testid="stHorizontalBlock"]:first-of-type > div:last-child,
main [class*="st-key-chat_glass_panel"] [data-testid="stHorizontalBlock"]:first-of-type > div:last-child {
    display: flex !important;
    justify-content: flex-end !important;
    padding-right: 0 !important;
    margin-left: auto !important;
    margin-right: -2.5rem !important;
}
[data-testid="stAppViewContainer"] [class*="st-key-header_provider"] [data-testid="stSelectbox"],
main [class*="st-key-header_provider"] [data-testid="stSelectbox"],
[data-testid="stAppViewContainer"] [class*="st-key-chat_glass_panel"] [data-testid="stHorizontalBlock"]:first-of-type > div:last-child [data-testid="stSelectbox"],
main [class*="st-key-chat_glass_panel"] [data-testid="stHorizontalBlock"]:first-of-type > div:last-child [data-testid="stSelectbox"] {
    width: auto !important;
    min-width: 7.5rem !important;
    max-width: 8.5rem !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
[data-testid="stAppViewContainer"] [class*="st-key-header_provider"] [data-testid="stSelectbox"] > div,
main [class*="st-key-header_provider"] [data-testid="stSelectbox"] > div,
[data-testid="stAppViewContainer"] [class*="st-key-chat_glass_panel"] [data-testid="stHorizontalBlock"]:first-of-type > div:last-child [data-testid="stSelectbox"] > div,
main [class*="st-key-chat_glass_panel"] [data-testid="stHorizontalBlock"]:first-of-type > div:last-child [data-testid="stSelectbox"] > div {
    min-width: 7.5rem !important;
    max-width: 8.5rem !important;
    min-height: 1.6rem !important;
    padding: 0.25rem 0.5rem !important;
    font-size: 0.8rem !important;
    border-radius: 0.5rem !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    white-space: nowrap !important;
    overflow: visible !important;
}
[data-testid="stAppViewContainer"] [class*="st-key-header_provider"] [data-testid="stSelectbox"] [class*="control"],
main [class*="st-key-header_provider"] [data-testid="stSelectbox"] [class*="control"],
[data-testid="stAppViewContainer"] [class*="st-key-chat_glass_panel"] [data-testid="stHorizontalBlock"]:first-of-type > div:last-child [data-testid="stSelectbox"] [class*="control"],
main [class*="st-key-chat_glass_panel"] [data-testid="stHorizontalBlock"]:first-of-type > div:last-child [data-testid="stSelectbox"] [class*="control"] {
    font-size: 0.8rem !important;
    padding: 0.15rem 0.4rem !important;
    white-space: nowrap !important;
}
[data-testid="stAppViewContainer"] [class*="st-key-chat_glass_panel"] [data-testid="stHorizontalBlock"]:first-of-type [data-testid="stSelectbox"] [role="listbox"],
main [class*="st-key-chat_glass_panel"] [data-testid="stHorizontalBlock"]:first-of-type [data-testid="stSelectbox"] [role="listbox"],
[data-testid="stAppViewContainer"] [class*="st-key-chat_glass_panel"] [data-testid="stHorizontalBlock"]:first-of-type [data-testid="stSelectbox"] div[role="option"],
main [class*="st-key-chat_glass_panel"] [data-testid="stHorizontalBlock"]:first-of-type [data-testid="stSelectbox"] div[role="option"] {
    font-size: 0.8rem !important;
    white-space: nowrap !important;
}
/* End workflow modal (opens from sidebar): Cancel left, End workflow right; button text on one line. Global selector so it applies when modal is portaled outside main. */
[class*="st-key-end_wf_modal_actions"] button,
[data-testid="stAppViewContainer"] [class*="st-key-end_wf_modal_actions"] button,
main [class*="st-key-end_wf_modal_actions"] button {
    white-space: nowrap !important;
    min-width: fit-content !important;
}
</style>
"""


def page_chatting():
    # Optional full-page background image (must be first so it applies to .stApp as main background)
    if BACKGROUND_IMAGE_URL:
        bg_css = f"""
        <style>
        html, body {{
            margin: 0;
            padding: 0;
            min-height: 100vh;
        }}
        .stApp {{
            background-image: url("{BACKGROUND_IMAGE_URL}") !important;
            background-size: cover !important;
            background-position: center !important;
            background-attachment: fixed !important;
            background-repeat: no-repeat !important;
        }}
        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] > div,
        main,
        main > div,
        main > div > div,
        div:has(> [data-testid="stMainBlockContainer"]) {{
            background: transparent !important;
            background-color: transparent !important;
        }}
        </style>
        """
        st.markdown(bg_css, unsafe_allow_html=True)
    # Chat container + bubble styles (frosted panel on top of background)
    st.markdown(CHAT_CONTAINER_CSS, unsafe_allow_html=True)

    # When a workflow is active, use main column + right sidebar (flowchart, progress, current/next step)
    use_right_sidebar = bool(st.session_state.get("workflow"))
    if use_right_sidebar:
        col_main, col_right = st.columns([2.8, 1])
        ctx_main = col_main
    else:
        ctx_main = st.container()
        col_right = None

    with ctx_main:
        with st.container(key="chat_glass_panel"):
            # Step 1. Header: title left, model provider dropdown top right
            st.session_state.setdefault("ppr_provider", st.session_state.get("ppr_provider_sidebar", "openai"))
            col_title, col_provider = st.columns([3, 1])  # provider column narrow; CSS pins dropdown right
            with col_title:
                st.title(st.secrets.message.title)
            with col_provider:
                with st.container(key="header_provider"):
                    st.selectbox(
                        "Model provider",
                        options=list(SUPPORTED_PROVIDERS),
                        format_func=lambda p: PROVIDER_LABELS.get(p, p.title()),
                        key="ppr_provider",
                        label_visibility="collapsed",
                    )

            # Step 2. Chat area container (messages + buttons + input) so message box is inside
            with st.container(key="chat_area"):
                # Chat history (assistant/user for bubble styling)
                for message in st.session_state.messages:
                    role = message.get("role") or "assistant"
                    streamlit_role = "user" if (role.strip().lower() == "human") else "assistant"
                    with st.chat_message(streamlit_role):
                        st.write(message.get("content") or "")
                        activity = message.get("activity")
                        if activity:
                            st.markdown(
                                '<p class="tools-used-line"><strong>Tools used:</strong> '
                                + " → ".join(activity)
                                + "</p>",
                                unsafe_allow_html=True,
                            )

                # Step 2b. "View products" / "View selected products" buttons (open modals via workflow ui); stacked vertically, left-aligned
                workflow = st.session_state.get("workflow")
                if workflow and workflow.get("name") == WorkFlows.WORKFLOW_PPR.value:
                    from src.workflows.workflow_ppr.ui.support import (
                        _has_product_data,
                        _has_selected_products,
                    )
                    has_rec = _has_product_data()
                    has_sel = _has_selected_products()
                    if has_rec or has_sel:
                        with st.container(key="view_products_buttons"):
                            if has_rec and has_sel:
                                if st.button("View selected products", type="secondary", key="view_selected_products_btn"):
                                    st.session_state.show_selected_products_modal = True
                                    st.rerun()
                                if st.button("View recommended products", type="secondary", key="view_products_btn"):
                                    st.session_state.show_products_modal = True
                                    st.rerun()
                            elif has_sel:
                                if st.button("View selected products", type="secondary", key="view_selected_products_btn"):
                                    st.session_state.show_selected_products_modal = True
                                    st.rerun()
                            elif has_rec:
                                if st.button("View recommended products", type="secondary", key="view_products_btn"):
                                    st.session_state.show_products_modal = True
                                    st.rerun()
                elif workflow and workflow.get("name") == WorkFlows.WORKFLOW_IPR.value:
                    from src.workflows.workflow_ipr.ui.support import (
                        _has_product_data,
                        _has_selected_products,
                    )
                    has_rec = _has_product_data()
                    has_sel = _has_selected_products()
                    if has_rec or has_sel:
                        with st.container(key="view_products_buttons"):
                            if has_rec and has_sel:
                                if st.button("View selected products", type="secondary", key="view_selected_products_btn_ipr"):
                                    st.session_state.show_selected_products_modal = True
                                    st.rerun()
                                if st.button("View recommended products", type="secondary", key="view_products_btn_ipr"):
                                    st.session_state.show_products_modal = True
                                    st.rerun()
                            elif has_sel:
                                if st.button("View selected products", type="secondary", key="view_selected_products_btn_ipr"):
                                    st.session_state.show_selected_products_modal = True
                                    st.rerun()
                            elif has_rec:
                                if st.button("View recommended products", type="secondary", key="view_products_btn_ipr"):
                                    st.session_state.show_products_modal = True
                                    st.rerun()

                # Step 3. While AI is generating: show "Thinking..." in a fixed-height slot so layout doesn't shift.
                generation_in_progress = st.session_state.get("generation_in_progress", False)
                messages = st.session_state.get("messages") or []
                last_is_human = bool(messages and (messages[-1].get("role") or "").strip().lower() == "human")

                if generation_in_progress and last_is_human:
                    with st.container(key="thinking_slot"):
                        with st.chat_message("assistant"):
                            st.markdown(
                                'Thinking <span class="typing-dots"><span></span><span></span><span></span></span>',
                                unsafe_allow_html=True,
                            )
                    provider = st.session_state.get("ppr_provider", "openai")
                    routing(messages[-1]["content"], provider=provider)
                    return

                # Step 4. Chat input inside container (message box appears inside the gray area)
                human_message = st.chat_input()
                if human_message:
                    st.chat_message("user").write(human_message)
                    st.session_state.messages.append({"role": "Human", "content": human_message})
                    st.session_state.generation_in_progress = True
                    st.rerun()
                    return

    if col_right is not None:
        with col_right:
            with st.container(key="right_sidebar_panel"):
                from src.common.right_sidebar import render_right_sidebar
                render_right_sidebar()
            
    
def main():    
    # if ui exist, then run the workflow ui
    if st.session_state.workflow and st.session_state.workflow['ui']:
        st.session_state.workflow['ui'](page_chatting)
    else:
        page_chatting()


if __name__ == '__main__':
    initialization()
    main()
