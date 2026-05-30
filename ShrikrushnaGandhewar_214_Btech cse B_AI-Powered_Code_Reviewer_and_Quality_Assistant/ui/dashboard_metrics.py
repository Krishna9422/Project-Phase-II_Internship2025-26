import os
import streamlit as st
from core.doc_steward import get_entity_list, get_function_complexity, get_maintainability_index
from core import java_support as core_java_support

def calculate_aggregate_metrics(file_list):
    """Calculate aggregate metrics across all files.
    
    Args:
        file_list: List of file paths to analyze
        
    Returns:
        Dictionary with aggregated metrics
    """
    total_functions = 0
    total_documented = 0
    total_undocumented = 0
    total_mi = 0.0
    file_count = 0
    raw_details = []
    syntax_errors = []

    workspace_root = os.path.abspath(os.getcwd())

    selected_language = st.session_state.get("selected_language", "Python")
    for file_path in file_list:
        if not os.path.exists(file_path):
            continue

        try:
            if selected_language == "Python":
                try:
                    entities = get_entity_list(file_path)
                except SyntaxError as e:
                    syntax_errors.append({
                        "file_path": file_path,
                        "file_name": os.path.basename(file_path),
                        "lineno": getattr(e, 'lineno', 'unknown'),
                        "text": getattr(e, 'text', None)
                    })
                    continue
                func_entities = [e for e in entities if e.get("Type") in ("Function", "Method")]

                file_funcs = len(func_entities)
                file_documented = sum(1 for e in func_entities if e.get("Has Docstring"))
                file_undocumented = file_funcs - file_documented
                file_coverage = (file_documented / file_funcs * 100) if file_funcs > 0 else 0.0

                mi = get_maintainability_index(file_path)

                total_functions += file_funcs
                total_documented += file_documented
                total_undocumented += file_undocumented
                total_mi += mi
                file_count += 1

                abs_path = os.path.abspath(file_path)
                rel_path = os.path.relpath(abs_path, workspace_root).replace("\\", "/")
                raw_details.append({
                    "file_path": abs_path,
                    "file_name": os.path.basename(file_path),
                    "file_rel": rel_path,
                    "functions": file_funcs,
                    "documented": file_documented,
                    "coverage": file_coverage,
                    "mi": mi
                })
            else:
                # Java files: use java_support summary
                report = core_java_support.get_java_file_report(file_path)
                for diagnostic in report.get("syntax_errors", []):
                    syntax_errors.append({
                        "file_path": file_path,
                        "file_name": os.path.basename(file_path),
                        "lineno": diagnostic.get("line", "unknown"),
                        "column": diagnostic.get("column"),
                        "message": diagnostic.get("message"),
                        "text": diagnostic.get("source"),
                    })

                file_funcs = int(report.get("methods", 0)) + int(report.get("classes", 0))
                file_documented = int(report.get("documented_count", 0))
                file_undocumented = file_funcs - file_documented
                file_coverage = (file_documented / file_funcs * 100) if file_funcs > 0 else 0.0

                mi = 0.0

                total_functions += file_funcs
                total_documented += file_documented
                total_undocumented += file_undocumented
                total_mi += mi
                file_count += 1

                abs_path = os.path.abspath(file_path)
                rel_path = os.path.relpath(abs_path, workspace_root).replace("\\", "/")
                raw_details.append({
                    "file_path": abs_path,
                    "file_name": os.path.basename(file_path),
                    "file_rel": rel_path,
                    "functions": file_funcs,
                    "documented": file_documented,
                    "coverage": file_coverage,
                    "mi": mi
                })
        except Exception:
            continue

    basename_counts = {}
    for detail in raw_details:
        name = detail["file_name"]
        basename_counts[name] = basename_counts.get(name, 0) + 1

    file_details = []
    for detail in raw_details:
        display_label = detail["file_rel"] if basename_counts.get(detail["file_name"], 0) > 1 else detail["file_name"]
        file_details.append({
            "file": display_label,
            "file_path": detail["file_path"],
            "file_name": detail["file_name"],
            "file_rel": detail["file_rel"],
            "functions": detail["functions"],
            "documented": detail["documented"],
            "coverage": detail["coverage"],
            "mi": detail["mi"],
        })
    
    avg_coverage = (total_documented / total_functions * 100) if total_functions > 0 else 0.0
    avg_mi = total_mi / file_count if file_count > 0 else 0.0
    
    return {
        "total_functions": total_functions,
        "total_documented": total_documented,
        "total_undocumented": total_undocumented,
        "avg_coverage": avg_coverage,
        "avg_mi": avg_mi,
        "file_count": file_count,
        "file_details": file_details,
        "syntax_errors": syntax_errors
    }
