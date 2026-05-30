"""
INTEGRATION GUIDE: Adding "Explain this Function" Feature

This file shows you exactly how to integrate the new "Explain this Function"
feature into your existing main_app.py

STEP 1: Add the import at the top of main_app.py
STEP 2: Add the new page to the navigation
STEP 3: Call the function in your main() function
"""

# ============================================================================
# STEP 1: Add this import near the top of main_app.py
# ============================================================================

from ui.section_explain_function import show_explain_function_tab


# ============================================================================
# STEP 2: Add to your pages list (find this in your main_app.py)
# ============================================================================

# Current code looks like:
# pages = ["Home"] + sorted(other_pages, key=lambda page_name: page_name.lower())

# MODIFY to:
other_pages = [
    "Dashboard",
    "AI Optimizer",
    "Docstring",
    "Function Details",
    "Explain Function",  # ← ADD THIS NEW PAGE
    "JSON Output",
    "Validation",
]


# ============================================================================
# STEP 3: Add icon for the new page (in your page_icons dict)
# ============================================================================

page_icons = {
    "Home": "🏠",
    "Dashboard": "📊",
    "AI Optimizer": "⚡",
    "Docstring": "📝",
    "Function Details": "🔍",
    "Explain Function": "🧠",  # ← ADD THIS ICON
    "JSON Output": "🧾",
    "Validation": "✅",
}


# ============================================================================
# STEP 4: Add the page handler in your main() function
# ============================================================================

# Find your existing page handlers that look like:
# if view == "Home":
#     run_home_section(...)
# elif view == "Dashboard":
#     ...

# ADD THIS BLOCK:
elif view == "Explain Function":
    st.markdown(
        "<h1 style='text-align: center; margin-bottom: 2rem;'>🧠 Explain Function</h1>",
        unsafe_allow_html=True
    )
    show_explain_function_tab()


# ============================================================================
# COMPLETE EXAMPLE: What the main() function modification looks like
# ============================================================================

def main():
    """Main function for AI Code Reviewer."""
    # ... existing code ...
    
    if view == "Home":
        st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>🚀 Home</h1>", unsafe_allow_html=True)
        run_home_section()
    
    elif view == "Dashboard":
        st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>📊 Dashboard</h1>", unsafe_allow_html=True)
        dashboard.show_analytics_dashboard()
    
    elif view == "AI Optimizer":
        st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>⚡ AI Optimizer</h1>", unsafe_allow_html=True)
        run_ai_optimizer_section()
    
    elif view == "Docstring":
        st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>📝 Docstring</h1>", unsafe_allow_html=True)
        run_docstring_section()
    
    elif view == "Explain Function":  # ← NEW PAGE
        st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>🧠 Explain Function</h1>", unsafe_allow_html=True)
        show_explain_function_tab()
    
    elif view == "Function Details":
        st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>🔍 Function Details</h1>", unsafe_allow_html=True)
        # ... existing function details code ...
    
    # ... rest of your views ...


# ============================================================================
# DEPENDENCIES
# ============================================================================

# The new feature uses:
# - streamlit (already in requirements.txt)
# - langchain-groq (already in requirements.txt)
# - groq (already in requirements.txt)
# - python-dotenv (already in requirements.txt)

# No new packages need to be installed!


# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

# The feature uses the GROQ_API_KEY environment variable.
# Users can provide it:
# 1. Via the UI text input (recommended for Streamlit)
# 2. Via .env file:
#    Create a .env file in your project root with:
#    GROQ_API_KEY=gsk_your_api_key_here

# Get your free API key from: https://console.groq.com


# ============================================================================
# FEATURES INCLUDED
# ============================================================================

# ✅ Select Python file from uploaded files
# ✅ Choose function/method from that file
# ✅ Display function code with syntax highlighting
# ✅ Generate AI explanation covering:
#    - Purpose
#    - Inputs (parameters)
#    - Output (return value)
#    - Step-by-step logic
#    - Usage example
#    - Key insights
# ✅ Organized UI with tabs for easy reading
# ✅ Error handling for:
#    - Missing API key
#    - Syntax errors in Python files
#    - Missing functions
#    - LLM API failures
# ✅ Reusable functions for integration elsewhere


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

# From Python code (not Streamlit):
"""
from core.function_explainer import get_function_code, explain_function_llm

# Get function code
code = get_function_code("path/to/file.py", "my_function")
print(code)

# Explain the function
explanation = explain_function_llm(
    code,
    api_key="gsk_your_key_here"
)

print(explanation['purpose'])
print(explanation['inputs'])
print(explanation['full_text'])
"""


# ============================================================================
# TROUBLESHOOTING
# ============================================================================

# Q: "No functions found in this file"
# A: Make sure the Python file has valid syntax. Check the file manually.

# Q: "LLM call failed"
# A: Check your API key is valid. Visit https://console.groq.com to verify.

# Q: "GROQ_API_KEY environment variable not set"
# A: Either:
#    1. Provide the key via the UI text input
#    2. Create a .env file with GROQ_API_KEY=your_key
#    3. Set it as a system environment variable

# Q: API rate limit exceeded
# A: Groq has free tier limits. Wait a minute before trying again.
