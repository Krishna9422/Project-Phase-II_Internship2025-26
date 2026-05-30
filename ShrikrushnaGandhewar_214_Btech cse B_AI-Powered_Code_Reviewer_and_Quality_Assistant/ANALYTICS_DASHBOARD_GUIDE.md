## 📊 Interactive Analytics Dashboard Guide

Your project now has a comprehensive **Interactive Analytics Dashboard** that provides real-time insights into your code quality and project metrics.

### 🎯 How to Access

1. **Run the Application:**
   ```bash
   streamlit run main_app.py
   ```

2. **Navigate to Dashboard:**
   - Look in the left sidebar under "Page"
   - Select **📊 Analytics Dashboard** from the dropdown
   - Or click on Home and find the dashboard button

### 📈 Dashboard Sections

#### 1. **Key Performance Indicators (KPIs)**
Shows at-a-glance metrics:
- **Test Accuracy**: Percentage of tests passing (target: 100%)
- **Documentation Coverage**: % of functions with docstrings (target: >80%)
- **Code Maintainability**: Average maintainability index score (higher is better)
- **Total Files Analyzed**: Count of source files being reviewed

#### 2. **Test Results Analysis**
Displays:
- **Test Summary**: Total tests, passed, and failed counts
- **Test Duration**: Total execution time for the test suite
- **Test Outcome Pie Chart**: Visual breakdown of test results
- Color-coded indicators (green for passing, red for failures)

#### 3. **Code Quality Metrics**
Includes two interactive charts:
- **Docstring Coverage by File**: Horizontal bar chart showing documentation % for each file
- **Maintainability Index by File**: Scatter plot with MI scores for easy comparison

#### 4. **Function Complexity Distribution**
Visualizes code complexity metrics:
- **Complexity Histogram**: Distribution of cyclomatic complexity across functions
- **Most Complex Functions**: Table of top 5 most complex functions
- Color indicators: Green (simple), Yellow (moderate), Red (complex)

#### 5. **Documentation Statistics**
Shows documentation progress:
- **Metrics Cards**: Total functions, documented, and undocumented counts
- **Progress Bar**: Visual representation of documentation completion
- **Stacked Bar Chart**: Documented vs undocumented comparison
- **Donut Chart**: Percentage breakdown

#### 6. **Project Summary & Recommendations**
Intelligent analysis section with:
- **Current Status**: Automatic assessment of project health
- **Recommendations**: Actionable suggestions for improvements

### 🎨 Features

✨ **Beautiful UI**
- Glassmorphism design with gradient backgrounds
- Responsive layouts that work on all screen sizes
- Dark theme optimized for reduced eye strain
- Interactive Plotly charts with hover tooltips

📊 **Interactive Charts**
- Hover over data points for detailed information
- Zoom, pan, and download chart features
- Color-coded visualizations for quick insights
- Real-time updates as you select files

🔍 **Comprehensive Metrics**
- Test execution results from pytest
- Function complexity analysis (cyclomatic complexity)
- Docstring coverage tracking
- Maintainability index calculations
- Code quality scoring

### 📝 How to Use

1. **Select Files**: Use the file uploader to select Python or Java files you want to analyze
2. **View Dashboard**: Click on "Analytics Dashboard" to see all metrics
3. **Analyze Results**: Review KPIs and charts to understand code quality
4. **Take Action**: Follow the recommendations to improve your code
5. **Track Progress**: Return to dashboard to see improvements over time

### 💡 Interpretation Guide

| Metric | Good | Acceptable | Needs Work |
|--------|------|-----------|-----------|
| Test Accuracy | 100% | 80-99% | <80% |
| Documentation Coverage | >80% | 50-80% | <50% |
| Maintainability Index | >70 | 50-70 | <50 |
| Cyclomatic Complexity | 1-5 | 6-10 | >10 |

### 🚀 Best Practices

1. **Run Tests Regularly**: Execute pytest to generate fresh test results
   ```bash
   pytest --json-report --json-report-file=storage/reports/pytest_results.json
   ```

2. **Review Dashboard Weekly**: Monitor metrics to track progress
3. **Address Complex Functions**: Refactor functions with high complexity
4. **Maintain Documentation**: Keep docstrings updated and comprehensive
5. **Monitor Test Coverage**: Ensure all critical paths are tested

### 📂 Required Files

The dashboard automatically looks for:
- `storage/reports/pytest_results.json` - Test results from pytest
- Source code files (.py and .java) - Analyzed for metrics
- `core/doc_steward.py` - For docstring and complexity analysis

### 🔧 Customization

You can modify the analytics dashboard by editing:
- `ui/section_analytics_dashboard.py` - Main dashboard component
- Add custom metrics by updating `calculate_aggregate_metrics()` in `ui/dashboard_metrics.py`
- Customize colors and styles in the CSS sections

### ❓ FAQ

**Q: Why is my test accuracy not showing?**
A: Run pytest to generate results:
```bash
pytest --json-report --json-report-file=storage/reports/pytest_results.json
```

**Q: Can I export dashboard data?**
A: Charts can be downloaded by clicking the camera icon in Plotly charts. For raw data, check the JSON output section.

**Q: How often is the dashboard updated?**
A: The dashboard updates whenever you refresh the page or rerun the Streamlit app.

**Q: What languages are supported?**
A: Python and Java files are fully supported. Toggle between them using the language selector in the sidebar.

---

### 📧 Support

For issues or feature requests, refer to the project documentation or contact the development team.

**Happy analyzing! 🎉**
