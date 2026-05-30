"""
PRACTICAL EXAMPLES: Using the "Explain this Function" Feature

This file shows various usage patterns and advanced scenarios.
"""

# ============================================================================
# EXAMPLE 1: Basic CLI Usage (Non-Streamlit)
# ============================================================================

def example_basic_usage():
    """
    Use the explainer as a command-line tool or in scripts.
    """
    from core.function_explainer import get_function_code, explain_function_llm
    import os
    
    # Path to your Python file
    file_path = "core/doc_steward.py"
    function_name = "analyze_file"
    
    # Get the function code
    try:
        code = get_function_code(file_path, function_name)
        print(f"Found function:\n{code}\n")
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return
    
    # Explain it
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        print("Set GROQ_API_KEY environment variable first")
        return
    
    explanation = explain_function_llm(code, api_key=api_key)
    
    # Print each section
    print(f"PURPOSE:\n{explanation['purpose']}\n")
    print(f"INPUTS:\n{explanation['inputs']}\n")
    print(f"OUTPUT:\n{explanation['output']}\n")
    print(f"LOGIC:\n{explanation['logic']}\n")


# ============================================================================
# EXAMPLE 2: Batch Explain Multiple Functions
# ============================================================================

def example_batch_explain_functions():
    """
    Explain all functions in a file.
    """
    from core.function_explainer import (
        extract_functions_from_file,
        get_function_code,
        explain_function_llm
    )
    import os
    
    file_path = "core/doc_steward.py"
    api_key = os.environ.get('GROQ_API_KEY')
    
    # Get all functions
    functions = extract_functions_from_file(file_path)
    
    explanations = {}
    for func_info in functions[:3]:  # First 3 functions
        name = func_info['name']
        print(f"\n{'='*60}")
        print(f"Explaining: {name}")
        print('='*60)
        
        code = get_function_code(file_path, name)
        if code:
            explanation = explain_function_llm(code, api_key=api_key)
            explanations[name] = explanation
            print(f"Purpose: {explanation['purpose']}")


# ============================================================================
# EXAMPLE 3: Custom Prompt for Specific Analysis
# ============================================================================

def example_custom_analysis():
    """
    Modify the explanation prompt for specific needs.
    """
    from core.function_explainer import get_function_code
    from langchain_groq import ChatGroq
    from langchain_core.messages import HumanMessage
    import os
    
    file_path = "core/doc_steward.py"
    function_name = "analyze_file"
    api_key = os.environ.get('GROQ_API_KEY')
    
    code = get_function_code(file_path, function_name)
    
    # Custom analysis: Security focus
    custom_prompt = f"""
    You are a security expert. Analyze this Python function for:
    1. Potential security vulnerabilities
    2. Input validation issues
    3. Safe file handling practices
    4. Recommendations for hardening
    
    Function code:
    ```python
    {code}
    ```
    """
    
    llm = ChatGroq(
        temperature=0.2,
        model_name="mixtral-8x7b-32768",
        api_key=api_key
    )
    
    response = llm.invoke([HumanMessage(content=custom_prompt)])
    print(response.content)


# ============================================================================
# EXAMPLE 4: Generate Documentation from Explanations
# ============================================================================

def example_generate_documentation():
    """
    Use explanations to generate markdown documentation.
    """
    from core.function_explainer import (
        extract_functions_from_file,
        get_function_code,
        explain_function_llm
    )
    import os
    from pathlib import Path
    
    file_path = "core/doc_steward.py"
    api_key = os.environ.get('GROQ_API_KEY')
    
    functions = extract_functions_from_file(file_path)
    
    # Create documentation file
    doc_lines = [
        f"# API Documentation for {Path(file_path).stem}",
        "",
        "Auto-generated from function explanations",
        "",
    ]
    
    for func_info in functions[:5]:  # Document first 5
        name = func_info['display_name']
        code = get_function_code(file_path, func_info['name'])
        
        if code:
            explanation = explain_function_llm(code, api_key=api_key)
            
            doc_lines.extend([
                f"## {name}",
                "",
                explanation.get('purpose', 'Purpose not available'),
                "",
                f"**Parameters:**\n{explanation.get('inputs', 'No parameters')}",
                "",
                f"**Returns:**\n{explanation.get('output', 'No return value')}",
                "",
                f"**Example:**\n{explanation.get('example', 'No example')}",
                "",
                "---",
                "",
            ])
    
    # Write to file
    with open('AUTO_DOCUMENTATION.md', 'w') as f:
        f.write('\n'.join(doc_lines))
    
    print("Documentation generated: AUTO_DOCUMENTATION.md")


# ============================================================================
# EXAMPLE 5: Streamlit Custom Component
# ============================================================================

def example_streamlit_component():
    """
    Custom Streamlit component for explaining with caching.
    """
    import streamlit as st
    from core.function_explainer import get_function_code, explain_function_llm
    import os
    
    @st.cache_data
    def get_cached_explanation(file_path, function_name, api_key):
        """Cache explanations to avoid re-running expensive LLM calls."""
        code = get_function_code(file_path, function_name)
        return explain_function_llm(code, api_key=api_key)
    
    # In your Streamlit app:
    file_path = st.text_input("File path:")
    function_name = st.text_input("Function name:")
    api_key = st.secrets.get("GROQ_API_KEY", "")
    
    if st.button("Explain"):
        try:
            explanation = get_cached_explanation(file_path, function_name, api_key)
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Purpose")
                st.write(explanation['purpose'])
            with col2:
                st.subheader("Inputs")
                st.write(explanation['inputs'])
            
            with st.expander("Full Explanation"):
                st.markdown(explanation['full_text'])
        
        except Exception as e:
            st.error(f"Error: {str(e)}")


# ============================================================================
# EXAMPLE 6: Error Handling & Edge Cases
# ============================================================================

def example_error_handling():
    """
    Proper error handling in production code.
    """
    from core.function_explainer import get_function_code, explain_function_llm
    import os
    
    file_path = "core/doc_steward.py"
    function_name = "nonexistent_function"
    api_key = os.environ.get('GROQ_API_KEY')
    
    try:
        code = get_function_code(file_path, function_name)
        if not code:
            print(f"Function '{function_name}' not found in file")
            return
        
        explanation = explain_function_llm(code, api_key=api_key)
    
    except FileNotFoundError as e:
        print(f"File error: {e}")
    except ValueError as e:
        print(f"Invalid input: {e}")
    except RuntimeError as e:
        print(f"LLM error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


# ============================================================================
# EXAMPLE 7: Explain Functions in Python Classes
# ============================================================================

def example_explain_methods():
    """
    Extract and explain methods from classes.
    """
    from core.function_explainer import (
        extract_functions_from_file,
        get_function_code,
        explain_function_llm
    )
    import os
    
    file_path = "core/doc_steward.py"
    api_key = os.environ.get('GROQ_API_KEY')
    
    # Get all functions and methods
    all_items = extract_functions_from_file(file_path)
    
    # Filter for methods only
    methods = [f for f in all_items if f['type'] == 'method']
    
    for method in methods[:3]:
        print(f"\nExplaining method: {method['display_name']}")
        code = get_function_code(file_path, method['name'])
        explanation = explain_function_llm(code, api_key=api_key)
        print(f"Summary: {explanation['purpose'][:100]}...")


# ============================================================================
# EXAMPLE 8: Async Functions
# ============================================================================

def example_async_functions():
    """
    The explainer handles async functions too!
    """
    from core.function_explainer import extract_functions_from_file
    
    file_path = "core/doc_steward.py"
    
    all_items = extract_functions_from_file(file_path)
    
    # Find async functions
    async_functions = [f for f in all_items if f['is_async']]
    
    print(f"Found {len(async_functions)} async functions:")
    for func in async_functions:
        print(f"  - {func['display_name']} (async)")


# ============================================================================
# EXAMPLE 9: Integration with Test Generation
# ============================================================================

def example_generate_tests_from_explanation():
    """
    Use explanations to generate test cases.
    """
    from core.function_explainer import get_function_code, explain_function_llm
    from langchain_groq import ChatGroq
    from langchain_core.messages import HumanMessage
    import os
    
    file_path = "core/doc_steward.py"
    function_name = "analyze_file"
    api_key = os.environ.get('GROQ_API_KEY')
    
    code = get_function_code(file_path, function_name)
    explanation = explain_function_llm(code, api_key=api_key)
    
    # Generate test cases from explanation
    test_prompt = f"""
    Based on this function explanation, generate 3 pytest test cases:
    
    Function Purpose: {explanation['purpose']}
    Inputs: {explanation['inputs']}
    Output: {explanation['output']}
    Example: {explanation['example']}
    
    Generate realistic test cases with assertions.
    """
    
    llm = ChatGroq(
        temperature=0.3,
        model_name="mixtral-8x7b-32768",
        api_key=api_key
    )
    
    response = llm.invoke([HumanMessage(content=test_prompt)])
    print("Generated test cases:\n")
    print(response.content)


# ============================================================================
# RUNNING THESE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    # Uncomment the example you want to run:
    
    # example_basic_usage()
    # example_batch_explain_functions()
    # example_custom_analysis()
    # example_generate_documentation()
    # example_error_handling()
    # example_explain_methods()
    # example_async_functions()
    # example_generate_tests_from_explanation()
    
    print("Uncomment an example function to run it!")
