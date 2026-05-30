"""Home page section renderer."""

import pandas as pd
import plotly.express as px
import streamlit as st

from core.auto_fixer import fix_syntax_error
from ui.dashboard_metrics import calculate_aggregate_metrics
from ui.section_reports import render_coverage_report

def run_home_section(view, btn_container, file_list, docstring_style, show_empty_state):
	if view != "Home":
		return

	with btn_container:
		col1, col2, col3, col4 = st.columns(4)

		def go_to_page(page_name):
			st.session_state.current_page = page_name

		st.markdown(
			"""
			<style>
			div[data-testid="stButton"] button {
				height: 80px;
				font-size: 1.2rem !important;
				margin-bottom: 1rem;
			}
			</style>
			""",
			unsafe_allow_html=True,
		)

		lang = st.session_state.get("selected_language", "Python")

		if lang == "Python":
			with col1:
				st.button("⚙️ Function Details", on_click=go_to_page, args=("Function Details",), use_container_width=True)
				st.button("📝 Docstring", on_click=go_to_page, args=("Docstring",), use_container_width=True)
			with col2:
				st.button("📈 Dashboard", on_click=go_to_page, args=("Dashboard",), use_container_width=True)
				st.button("✅ Validation", on_click=go_to_page, args=("Validation",), use_container_width=True)
			with col3:
				st.button("📋 JSON Output", on_click=go_to_page, args=("JSON Output",), use_container_width=True)
				st.button("🧠 Explain Function", on_click=go_to_page, args=("Explain Function",), use_container_width=True)
			with col4:
				st.button("⚡ AI Optimizer", on_click=go_to_page, args=("AI Optimizer",), use_container_width=True)
				st.button("🤖 AI Assistant", on_click=go_to_page, args=("AI Assistant",), use_container_width=True)
		else:
			with col1:
				st.button("⚙️ Function Details", on_click=go_to_page, args=("Function Details",), use_container_width=True)
				st.button("📝 Docstring", on_click=go_to_page, args=("Docstring",), use_container_width=True)
			with col2:
				st.button("📈 Dashboard", on_click=go_to_page, args=("Dashboard",), use_container_width=True)
				st.button("🧪 Java Validation", on_click=go_to_page, args=("Java Validation",), use_container_width=True)
			with col3:
				st.button("📋 JSON Output", on_click=go_to_page, args=("JSON Output",), use_container_width=True)
				st.button("🧠 Explain Function", on_click=go_to_page, args=("Explain Function",), use_container_width=True)
			with col4:
				st.button("⚡ AI Optimizer", on_click=go_to_page, args=("AI Optimizer",), use_container_width=True)
				st.button("🤖 AI Assistant", on_click=go_to_page, args=("AI Assistant",), use_container_width=True)

	st.markdown("<div class='ui-section-title'>📊 3. Visual Report</div>", unsafe_allow_html=True)
	if not file_list:
		show_empty_state()
		return

	agg_metrics = calculate_aggregate_metrics(file_list)
	file_details = agg_metrics.get("file_details", [])
	syntax_errors = agg_metrics.get("syntax_errors", [])
	
	if syntax_errors:
		lang = st.session_state.get("selected_language", "Python")
		for err_idx, err in enumerate(syntax_errors):
			err_file = err["file_name"]
			err_line = err.get("lineno", "unknown")
			err_col = err.get("column")
			err_msg = err.get("message")
			location = f"line {err_line}" if err_col in (None, "", 0) else f"line {err_line}, column {err_col}"
			if err_msg:
				st.error(f"❌ Syntax Error in {err_file} at {location}: {err_msg}")
			else:
				st.error(f"❌ Syntax Error in {err_file} at {location}!")
			if err.get("text"):
				st.code(err["text"].rstrip(), language=("java" if lang == "Java" else "python"))
			button_key = f"fix_syntax_home_{err['file_path']}_{err.get('lineno', 'na')}_{err_idx}"
			if st.button(f"🪄 Auto-Fix Syntax Error in {err_file}", key=button_key):
				with st.spinner("Analyzing and fixing syntax error..."):
					if fix_syntax_error(err["file_path"], lang):
						st.success("✅ Syntax error corrected! Reloading...")
						st.rerun()
					else:
						st.error("❌ Failed to automatically fix syntax error. Check your GROQ API Key or code complexity.")
						
	if not file_details and not syntax_errors:
		st.warning("No valid files could be analyzed from your selection.")
		return
	elif not file_details:
		return

	st.info(f"📁 Visual report generated for {len(file_details)} selected file(s)")
	m1, m2, m3, m4 = st.columns(4)
	m1.metric("Files", agg_metrics["file_count"])
	m2.metric("Functions", agg_metrics["total_functions"])
	m3.metric("Documented", agg_metrics["total_documented"])
	m4.metric("Coverage", f"{agg_metrics['avg_coverage']:.1f}%")

	df_multi = pd.DataFrame(file_details)
	df_multi["undocumented"] = df_multi["functions"] - df_multi["documented"]
	total_missing = int(df_multi["undocumented"].sum())

	c1, c2 = st.columns(2)
	with c1:
		if agg_metrics["total_functions"] == 0:
			st.info("No classes or methods detected in the selected files to plot coverage.")
		else:
			pie_data = pd.DataFrame({
				"Status": ["Documented", "Undocumented"],
				"Count": [agg_metrics["total_documented"], agg_metrics["total_undocumented"]]
			})
			fig_pie = px.pie(
				pie_data,
				names="Status",
				values="Count",
				title="Overall Coverage",
				hole=0.45,
				color="Status",
				color_discrete_map={"Documented": "#10b981", "Undocumented": "#ef4444"},
			)
			fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#f8fafc"))
			st.plotly_chart(fig_pie, use_container_width=True)
	with c2:
		fig_cov = px.bar(
			df_multi,
			x="file",
			y="coverage",
			title="Coverage % by File",
			color="coverage",
			color_continuous_scale="RdYlGn",
			range_y=[0, 100],
		)
		fig_cov.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0.03)", font=dict(color="#f8fafc"))
		st.plotly_chart(fig_cov, use_container_width=True)

	with st.expander("📋 Per-file report table", expanded=True):
		report_df = df_multi[["file", "functions", "documented", "undocumented", "coverage", "mi"]].copy()
		report_df.columns = ["File", "Functions", "Documented", "Missing", "Coverage %", "MI"]
		report_df["Coverage %"] = report_df["Coverage %"].map(lambda value: round(value, 2))
		report_df["MI"] = report_df["MI"].map(lambda value: round(value, 2))
		st.dataframe(report_df, use_container_width=True)

	st.markdown("<div class='ui-section-title'>📄 4. Detailed Coverage Report</div>", unsafe_allow_html=True)
	render_coverage_report(
		file_list=file_list,
		files_to_display=file_list,
		show_all_files=True,
	)
