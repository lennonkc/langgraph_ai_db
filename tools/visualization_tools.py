"""
Visualization Tools
可视化工具

Comprehensive chart generation system with support for multiple visualization libraries
including Vega-Lite, Plotly, and HTML table generation.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()


class ChartGenerator:
    """图表生成器 - 主要的图表生成协调器"""

    def __init__(self):
        """初始化图表生成器"""
        self.supported_libraries = {
            "vega": VegaLiteGenerator(),
            "plotly": PlotlyGenerator(),
            "native_html": NativeHTMLGenerator()
        }

    def generate_chart(self,
                      chart_type: str,
                      data: List[Dict],
                      preferences: Dict[str, Any],
                      user_question: str) -> Dict[str, Any]:
        """生成图表规格和代码"""

        try:
            logger.info(f"Generating {chart_type} chart for {len(data)} data points")

            # Determine best library for chart type
            library = self._select_optimal_library(chart_type, data, preferences)

            # Generate chart specification
            generator = self.supported_libraries[library]
            chart_spec = generator.create_chart_spec(
                chart_type, data, preferences, user_question
            )

            # Generate HTML and JavaScript code
            html_code = generator.generate_html_code(chart_spec)
            js_code = generator.generate_js_code(chart_spec)

            # Generate chart title
            chart_title = self._generate_chart_title(user_question, preferences)

            result = {
                "library": library,
                "chart_spec": chart_spec,
                "html_code": html_code,
                "javascript_code": js_code,
                "chart_title": chart_title,
                "chart_type": chart_type
            }

            logger.info(f"Chart generated successfully using {library} library")

            return result

        except Exception as e:
            logger.error(f"Chart generation error: {e}")
            # Fallback to simple table
            return self._generate_fallback_chart(data, preferences, user_question)

    def _select_optimal_library(self,
                               chart_type: str,
                               data: List[Dict],
                               preferences: Dict) -> str:
        """选择最优的可视化库"""

        # Library preferences based on chart type
        library_preferences = {
            "bar_chart": "vega",
            "line_chart": "vega",
            "pie_chart": "plotly",
            "scatter_plot": "vega",
            "heatmap": "plotly",
            "treemap": "plotly",
            "area_chart": "vega",
            "table": "native_html"
        }

        # Consider data size
        if len(data) > 1000:
            # For large datasets, prefer Plotly for better performance
            if chart_type in ["bar_chart", "line_chart", "scatter_plot"]:
                return "plotly"

        # Check user preferences
        if preferences.get("library_preference") in self.supported_libraries:
            return preferences["library_preference"]

        return library_preferences.get(chart_type, "vega")

    def _generate_chart_title(self, user_question: str, preferences: Dict) -> str:
        """生成图表标题"""
        if preferences.get("title"):
            return preferences["title"]

        # Generate title based on question
        title_templates = {
            "top": "Top Performing Analysis",
            "trend": "Trend Analysis",
            "compare": "Comparison Analysis",
            "revenue": "Revenue Analysis",
            "profit": "Profitability Analysis",
            "sales": "Sales Analysis",
            "brands": "Brand Performance",
            "orders": "Order Analysis"
        }

        question_lower = user_question.lower()
        for keyword, template in title_templates.items():
            if keyword in question_lower:
                return template

        return "Business Data Analysis"

    def _generate_fallback_chart(self, data: List[Dict], preferences: Dict, user_question: str) -> Dict[str, Any]:
        """生成备用图表 (简单表格)"""
        generator = self.supported_libraries["native_html"]

        chart_spec = generator.create_chart_spec("table", data, preferences, user_question)
        html_code = generator.generate_html_code(chart_spec)

        return {
            "library": "native_html",
            "chart_spec": chart_spec,
            "html_code": html_code,
            "javascript_code": "",
            "chart_title": "Data Table",
            "chart_type": "table"
        }


class VegaLiteGenerator:
    """Vega-Lite图表生成器"""

    def create_chart_spec(self,
                         chart_type: str,
                         data: List[Dict],
                         preferences: Dict,
                         user_question: str) -> Dict:
        """创建Vega-Lite图表规格"""

        base_spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "description": f"Chart for: {user_question}",
            "data": {"values": data},
            "width": preferences.get("width", 600),
            "height": preferences.get("height", 400),
            "background": "#ffffff",
            "config": {
                "axis": {"labelFontSize": 12, "titleFontSize": 14},
                "legend": {"labelFontSize": 12, "titleFontSize": 14}
            }
        }

        if chart_type == "bar_chart":
            return self._create_bar_chart_spec(base_spec, data, preferences)
        elif chart_type == "line_chart":
            return self._create_line_chart_spec(base_spec, data, preferences)
        elif chart_type == "scatter_plot":
            return self._create_scatter_plot_spec(base_spec, data, preferences)
        elif chart_type == "area_chart":
            return self._create_area_chart_spec(base_spec, data, preferences)
        else:
            return self._create_default_chart_spec(base_spec, data, preferences)

    def _create_bar_chart_spec(self, base_spec: Dict, data: List[Dict], prefs: Dict) -> Dict:
        """创建条形图规格"""
        if not data:
            return base_spec

        # Identify categorical and numeric columns
        sample_row = data[0]
        categorical_col = None
        numeric_col = None

        for col, value in sample_row.items():
            if isinstance(value, str) and categorical_col is None:
                categorical_col = col
            elif isinstance(value, (int, float)) and numeric_col is None:
                numeric_col = col

        if not categorical_col or not numeric_col:
            return base_spec

        orientation = prefs.get("orientation", "vertical")
        color_scheme = prefs.get("color_scheme", "category10")

        if orientation == "horizontal":
            spec = {
                **base_spec,
                "mark": {"type": "bar", "tooltip": True, "cornerRadiusEnd": 2},
                "encoding": {
                    "y": {
                        "field": categorical_col,
                        "type": "nominal",
                        "sort": "-x",
                        "title": categorical_col.replace('_', ' ').title()
                    },
                    "x": {
                        "field": numeric_col,
                        "type": "quantitative",
                        "title": numeric_col.replace('_', ' ').title()
                    },
                    "color": {
                        "field": categorical_col,
                        "type": "nominal",
                        "scale": {"scheme": color_scheme},
                        "legend": {"title": categorical_col.replace('_', ' ').title()}
                    }
                }
            }
        else:
            spec = {
                **base_spec,
                "mark": {"type": "bar", "tooltip": True, "cornerRadiusEnd": 2},
                "encoding": {
                    "x": {
                        "field": categorical_col,
                        "type": "nominal",
                        "title": categorical_col.replace('_', ' ').title()
                    },
                    "y": {
                        "field": numeric_col,
                        "type": "quantitative",
                        "title": numeric_col.replace('_', ' ').title()
                    },
                    "color": {
                        "field": categorical_col,
                        "type": "nominal",
                        "scale": {"scheme": color_scheme},
                        "legend": {"title": categorical_col.replace('_', ' ').title()}
                    }
                }
            }

        return spec

    def _create_line_chart_spec(self, base_spec: Dict, data: List[Dict], prefs: Dict) -> Dict:
        """创建线图规格"""
        if not data:
            return base_spec

        sample_row = data[0]
        x_field = None
        y_field = None

        # Try to identify time/date field for x-axis
        for col, value in sample_row.items():
            if 'date' in col.lower() or 'time' in col.lower() or 'month' in col.lower() or 'year' in col.lower():
                x_field = col
                break

        # Find numeric field for y-axis
        for col, value in sample_row.items():
            if isinstance(value, (int, float)) and col != x_field:
                y_field = col
                break

        if not x_field or not y_field:
            # Fallback to first string and first numeric columns
            for col, value in sample_row.items():
                if isinstance(value, str) and x_field is None:
                    x_field = col
                elif isinstance(value, (int, float)) and y_field is None:
                    y_field = col

        if not x_field or not y_field:
            return base_spec

        spec = {
            **base_spec,
            "mark": {
                "type": "line",
                "point": prefs.get("show_markers", True),
                "interpolate": "linear" if not prefs.get("smooth_lines", False) else "monotone",
                "tooltip": True,
                "strokeWidth": 3
            },
            "encoding": {
                "x": {
                    "field": x_field,
                    "type": "temporal" if 'date' in x_field.lower() else "ordinal",
                    "title": x_field.replace('_', ' ').title()
                },
                "y": {
                    "field": y_field,
                    "type": "quantitative",
                    "title": y_field.replace('_', ' ').title()
                },
                "color": {"value": "#1f77b4"}
            }
        }

        return spec

    def _create_scatter_plot_spec(self, base_spec: Dict, data: List[Dict], prefs: Dict) -> Dict:
        """创建散点图规格"""
        if not data:
            return base_spec

        sample_row = data[0]
        numeric_fields = [col for col, value in sample_row.items() if isinstance(value, (int, float))]

        if len(numeric_fields) < 2:
            return base_spec

        x_field = numeric_fields[0]
        y_field = numeric_fields[1]

        spec = {
            **base_spec,
            "mark": {
                "type": "circle",
                "size": 100,
                "tooltip": True,
                "opacity": 0.7
            },
            "encoding": {
                "x": {
                    "field": x_field,
                    "type": "quantitative",
                    "title": x_field.replace('_', ' ').title()
                },
                "y": {
                    "field": y_field,
                    "type": "quantitative",
                    "title": y_field.replace('_', ' ').title()
                },
                "color": {"value": "#1f77b4"}
            }
        }

        # Add color by category if available
        categorical_fields = [col for col, value in sample_row.items() if isinstance(value, str)]
        if categorical_fields and prefs.get("color_by_category", False):
            spec["encoding"]["color"] = {
                "field": categorical_fields[0],
                "type": "nominal",
                "scale": {"scheme": "category10"}
            }

        return spec

    def _create_area_chart_spec(self, base_spec: Dict, data: List[Dict], prefs: Dict) -> Dict:
        """创建面积图规格"""
        # Similar to line chart but with area mark
        line_spec = self._create_line_chart_spec(base_spec, data, prefs)
        line_spec["mark"] = {
            "type": "area",
            "interpolate": "monotone",
            "tooltip": True,
            "opacity": 0.7
        }
        return line_spec

    def _create_default_chart_spec(self, base_spec: Dict, data: List[Dict], prefs: Dict) -> Dict:
        """创建默认图表规格"""
        return base_spec

    def generate_html_code(self, spec: Dict) -> str:
        """生成包含图表的HTML代码"""
        chart_id = f"vega-chart-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        return f"""
        <div id="{chart_id}" style="width: 100%; height: 500px;"></div>
        <script type="text/javascript">
            var spec = {json.dumps(spec, indent=2)};
            vegaEmbed('#{chart_id}', spec, {{
                "actions": true,
                "tooltip": true,
                "theme": "default"
            }}).catch(console.error);
        </script>
        """

    def generate_js_code(self, spec: Dict) -> str:
        """生成JavaScript代码"""
        return f"vegaEmbed('#vega-chart', {json.dumps(spec)});"


class PlotlyGenerator:
    """Plotly图表生成器"""

    def create_chart_spec(self,
                         chart_type: str,
                         data: List[Dict],
                         preferences: Dict,
                         user_question: str) -> Dict:
        """创建Plotly图表规格"""

        if chart_type == "pie_chart":
            return self._create_pie_chart_spec(data, preferences)
        elif chart_type == "heatmap":
            return self._create_heatmap_spec(data, preferences)
        elif chart_type == "treemap":
            return self._create_treemap_spec(data, preferences)
        elif chart_type == "bar_chart":
            return self._create_plotly_bar_chart_spec(data, preferences)
        elif chart_type == "line_chart":
            return self._create_plotly_line_chart_spec(data, preferences)
        else:
            return self._create_default_plotly_spec(data, preferences)

    def _create_pie_chart_spec(self, data: List[Dict], prefs: Dict) -> Dict:
        """创建饼图规格"""
        if not data:
            return {}

        sample_row = data[0]
        label_field = None
        value_field = None

        # Find categorical and numeric fields
        for col, value in sample_row.items():
            if isinstance(value, str) and label_field is None:
                label_field = col
            elif isinstance(value, (int, float)) and value_field is None:
                value_field = col

        if not label_field or not value_field:
            return {}

        labels = [row[label_field] for row in data]
        values = [row[value_field] for row in data]

        spec = {
            "data": [{
                "type": "pie",
                "labels": labels,
                "values": values,
                "textinfo": "label+percent" if prefs.get("show_percentages", True) else "label",
                "hovertemplate": "<b>%{label}</b><br>Value: %{value}<br>Percentage: %{percent}<extra></extra>",
                "marker": {
                    "colors": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FECA57", "#FF9FF3", "#54A0FF"],
                    "line": {"color": "#FFFFFF", "width": 2}
                }
            }],
            "layout": {
                "title": {
                    "text": prefs.get("title", "Distribution"),
                    "font": {"size": 18}
                },
                "showlegend": True,
                "font": {"size": 12},
                "margin": {"l": 50, "r": 50, "t": 50, "b": 50}
            }
        }

        # Handle explode largest slice
        if prefs.get("explode_largest", False):
            max_index = values.index(max(values))
            pull_values = [0.1 if i == max_index else 0 for i in range(len(values))]
            spec["data"][0]["pull"] = pull_values

        return spec

    def _create_plotly_bar_chart_spec(self, data: List[Dict], prefs: Dict) -> Dict:
        """创建Plotly条形图规格"""
        if not data:
            return {}

        sample_row = data[0]
        categorical_col = None
        numeric_col = None

        for col, value in sample_row.items():
            if isinstance(value, str) and categorical_col is None:
                categorical_col = col
            elif isinstance(value, (int, float)) and numeric_col is None:
                numeric_col = col

        if not categorical_col or not numeric_col:
            return {}

        x_values = [row[categorical_col] for row in data]
        y_values = [row[numeric_col] for row in data]

        orientation = prefs.get("orientation", "vertical")

        if orientation == "horizontal":
            spec = {
                "data": [{
                    "type": "bar",
                    "x": y_values,
                    "y": x_values,
                    "orientation": "h",
                    "marker": {"color": "#1f77b4"}
                }],
                "layout": {
                    "title": prefs.get("title", "Bar Chart"),
                    "xaxis": {"title": numeric_col.replace('_', ' ').title()},
                    "yaxis": {"title": categorical_col.replace('_', ' ').title()}
                }
            }
        else:
            spec = {
                "data": [{
                    "type": "bar",
                    "x": x_values,
                    "y": y_values,
                    "marker": {"color": "#1f77b4"}
                }],
                "layout": {
                    "title": prefs.get("title", "Bar Chart"),
                    "xaxis": {"title": categorical_col.replace('_', ' ').title()},
                    "yaxis": {"title": numeric_col.replace('_', ' ').title()}
                }
            }

        return spec

    def _create_plotly_line_chart_spec(self, data: List[Dict], prefs: Dict) -> Dict:
        """创建Plotly线图规格"""
        if not data:
            return {}

        sample_row = data[0]
        x_field = None
        y_field = None

        # Find x and y fields
        for col, value in sample_row.items():
            if 'date' in col.lower() or 'time' in col.lower() or 'month' in col.lower():
                x_field = col
                break

        for col, value in sample_row.items():
            if isinstance(value, (int, float)) and col != x_field:
                y_field = col
                break

        if not x_field or not y_field:
            for col, value in sample_row.items():
                if isinstance(value, str) and x_field is None:
                    x_field = col
                elif isinstance(value, (int, float)) and y_field is None:
                    y_field = col

        if not x_field or not y_field:
            return {}

        x_values = [row[x_field] for row in data]
        y_values = [row[y_field] for row in data]

        spec = {
            "data": [{
                "type": "scatter",
                "x": x_values,
                "y": y_values,
                "mode": "lines+markers" if prefs.get("show_markers", True) else "lines",
                "line": {"shape": "spline" if prefs.get("smooth_lines", False) else "linear"},
                "marker": {"color": "#1f77b4"}
            }],
            "layout": {
                "title": prefs.get("title", "Line Chart"),
                "xaxis": {"title": x_field.replace('_', ' ').title()},
                "yaxis": {"title": y_field.replace('_', ' ').title()}
            }
        }

        return spec

    def _create_heatmap_spec(self, data: List[Dict], prefs: Dict) -> Dict:
        """创建热力图规格"""
        # Simplified heatmap implementation
        return {"data": [], "layout": {"title": "Heatmap"}}

    def _create_treemap_spec(self, data: List[Dict], prefs: Dict) -> Dict:
        """创建树状图规格"""
        # Simplified treemap implementation
        return {"data": [], "layout": {"title": "Treemap"}}

    def _create_default_plotly_spec(self, data: List[Dict], prefs: Dict) -> Dict:
        """创建默认Plotly规格"""
        return {"data": [], "layout": {"title": "Chart"}}

    def generate_html_code(self, spec: Dict) -> str:
        """生成Plotly HTML代码"""
        chart_id = f"plotly-chart-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        return f"""
        <div id="{chart_id}" style="width:100%;height:500px;"></div>
        <script>
            var data = {json.dumps(spec.get('data', []))};
            var layout = {json.dumps(spec.get('layout', {}))};
            var config = {{responsive: true, displayModeBar: true}};
            Plotly.newPlot('{chart_id}', data, layout, config);
        </script>
        """

    def generate_js_code(self, spec: Dict) -> str:
        """生成Plotly JavaScript代码"""
        return f"""
        var data = {json.dumps(spec.get('data', []))};
        var layout = {json.dumps(spec.get('layout', {}))};
        Plotly.newPlot('plotly-chart', data, layout);
        """


class NativeHTMLGenerator:
    """原生HTML表格生成器"""

    def create_chart_spec(self,
                         chart_type: str,
                         data: List[Dict],
                         preferences: Dict,
                         user_question: str) -> Dict:
        """创建HTML表格规格"""
        return {
            "type": "table",
            "data": data,
            "preferences": preferences,
            "title": preferences.get("title", "Data Table")
        }

    def generate_html_code(self, spec: Dict) -> str:
        """生成HTML表格代码"""
        data = spec.get("data", [])
        preferences = spec.get("preferences", {})

        if not data:
            return "<p>No data available</p>"

        headers = list(data[0].keys())

        # Limit data for performance
        display_data = data[:200] if len(data) > 200 else data

        html = f"""
        <div class="table-container">
            <h3>{spec.get('title', 'Data Table')}</h3>
        """

        if len(data) > 200:
            html += f"<p><em>Showing first 200 rows of {len(data)} total records</em></p>"

        html += """
            <table class="data-table" style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                <thead>
                    <tr style="background-color: #f5f5f5;">
        """

        for header in headers:
            html += f'<th style="padding: 12px; text-align: left; border: 1px solid #ddd; font-weight: bold;">{header.replace("_", " ").title()}</th>'

        html += """
                    </tr>
                </thead>
                <tbody>
        """

        for i, row in enumerate(display_data):
            row_style = "background-color: #f9f9f9;" if i % 2 == 1 else ""
            html += f'<tr style="{row_style}">'

            for header in headers:
                value = row.get(header, "")
                if isinstance(value, float):
                    value = f"{value:,.2f}"
                elif isinstance(value, int):
                    value = f"{value:,}"
                html += f'<td style="padding: 8px; border: 1px solid #ddd;">{value}</td>'

            html += "</tr>"

        html += """
                </tbody>
            </table>
        </div>
        """

        return html

    def generate_js_code(self, spec: Dict) -> str:
        """生成JavaScript代码 (表格不需要)"""
        return ""


class HTMLReportGenerator:
    """HTML报告生成器"""

    def __init__(self):
        """初始化报告生成器"""
        pass

    def generate_full_report(self,
                           user_question: str,
                           chart_spec: Dict,
                           data: List[Dict],
                           preferences: Dict,
                           metadata: Dict,
                           explanation_markdown: str = "",
                           generated_script_content: str = "",
                           ai_summary_markdown: str = "") -> str:
        """生成完整的HTML报告"""

        try:
            logger.info("Generating full HTML report")

            report_html = self._build_report_structure(
                user_question, chart_spec, data, preferences, metadata,
                explanation_markdown, generated_script_content, ai_summary_markdown
            )

            logger.info("HTML report generated successfully")

            return report_html

        except Exception as e:
            logger.error(f"HTML report generation error: {e}")
            return self._generate_error_report(str(e))

    def _build_report_structure(self,
                               question: str,
                               chart_spec: Dict,
                               data: List[Dict],
                               preferences: Dict,
                               metadata: Dict,
                               explanation_markdown: str = "",
                               generated_script_content: str = "",
                               ai_summary_markdown: str = "") -> str:
        """构建报告结构"""

        # Load base template
        template = self._load_template()

        # Generate report sections
        header_section = self._generate_header_section(question, metadata)
        summary_section = self._generate_summary_section(data, metadata)
        visualization_section = self._generate_visualization_section(chart_spec)
        ai_summary_section = self._generate_ai_summary_section(ai_summary_markdown)
        data_section = self._generate_data_section(data, preferences)
        explanation_section = self._generate_explanation_section(explanation_markdown)
        script_section = self._generate_script_section(generated_script_content)
        footer_section = self._generate_footer_section(metadata)

        # Get library includes
        library_includes = self._get_library_includes(chart_spec.get("library", ""))

        # Combine all sections
        full_report = template.format(
            header=header_section,
            summary=summary_section,
            visualization=visualization_section,
            ai_summary=ai_summary_section,
            data_table=data_section,
            explanation=explanation_section,
            generated_script=script_section,
            footer=footer_section,
            chart_library_includes=library_includes
        )

        return full_report

    def _load_template(self) -> str:
        """加载HTML模板"""
        template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Business Analysis Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2.5em;
        }}
        .section {{
            padding: 30px;
            border-bottom: 1px solid #eee;
        }}
        .section:last-child {{
            border-bottom: none;
        }}
        .section h2 {{
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        .chart-container {{
            margin: 20px 0;
            padding: 20px;
            background-color: #fafafa;
            border-radius: 5px;
            border: 1px solid #e0e0e0;
        }}
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 25px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #dee2e6;
        }}
        .stat-value {{
            font-size: 2.2em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .footer {{
            background-color: #f8f9fa;
            color: #666;
            text-align: center;
            padding: 25px;
            font-size: 0.9em;
            border-top: 1px solid #e0e0e0;
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            font-size: 0.9em;
        }}
        .data-table th {{
            background-color: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        .data-table td {{
            padding: 10px 12px;
            border-bottom: 1px solid #eee;
        }}
        .data-table tr:hover {{
            background-color: #f8f9fa;
        }}
        .data-table tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        @media (max-width: 768px) {{
            .container {{
                margin: 10px;
                border-radius: 0;
            }}
            .section {{
                padding: 20px;
            }}
            .header {{
                padding: 30px 20px;
            }}
            .header h1 {{
                font-size: 2em;
            }}
            .summary-stats {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
    {chart_library_includes}
</head>
<body>
    <div class="container">
        {header}
        {summary}
        {visualization}
        {ai_summary}
        {data_table}
        {explanation}
        {generated_script}
        {footer}
    </div>
</body>
</html>
        """
        return template

    def _generate_header_section(self, question: str, metadata: Dict) -> str:
        """生成报告头部"""
        timestamp = metadata.get("generated_at", datetime.now().isoformat())
        formatted_time = timestamp.split('T')[0] if 'T' in timestamp else timestamp

        return f"""
        <div class="header">
            <h1>📊 Business Analysis Report</h1>
            <p style="font-size: 1.2em; margin: 10px 0;"><strong>Question:</strong> {question}</p>
            <p style="font-size: 0.9em; opacity: 0.9;"><small>Generated on {formatted_time}</small></p>
        </div>
        """

    def _generate_summary_section(self, data: List[Dict], metadata: Dict) -> str:
        """生成汇总统计部分"""
        if not data:
            return ""

        total_rows = len(data)
        execution_time = metadata.get("execution_time_seconds", 0)
        cost = metadata.get("cost_estimate_usd", 0)
        data_points = metadata.get("data_points", total_rows)

        summary_html = f"""
        <div class="section">
            <h2>📈 Summary Statistics</h2>
            <div class="summary-stats">
                <div class="stat-card">
                    <div class="stat-value">{data_points:,}</div>
                    <div class="stat-label">Total Records</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{execution_time:.2f}s</div>
                    <div class="stat-label">Query Time</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${cost:.4f}</div>
                    <div class="stat-label">Processing Cost</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{len(data[0].keys()) if data else 0}</div>
                    <div class="stat-label">Data Columns</div>
                </div>
            </div>
        </div>
        """

        return summary_html

    def _generate_visualization_section(self, chart_spec: Dict) -> str:
        """生成可视化部分"""
        chart_html = chart_spec.get("html_code", "")
        chart_title = chart_spec.get("chart_title", "Data Visualization")

        return f"""
        <div class="section">
            <h2>📊 {chart_title}</h2>
            <div class="chart-container">
                {chart_html}
            </div>
        </div>
        """

    def _generate_data_section(self, data: List[Dict], preferences: Dict) -> str:
        """生成数据表格部分"""
        if not preferences.get("include_data_table", True) or not data:
            return ""

        # Use NativeHTMLGenerator for consistent table styling
        table_generator = NativeHTMLGenerator()
        table_spec = {
            "data": data,
            "preferences": preferences,
            "title": "Detailed Data"
        }

        table_html = table_generator.generate_html_code(table_spec)

        return f"""
        <div class="section">
            <h2>📋 Detailed Data</h2>
            {table_html}
        </div>
        """

    def _generate_ai_summary_section(self, ai_summary_markdown: str) -> str:
        """生成AI摘要部分 - 在数据表格上方显示"""
        if not ai_summary_markdown or not ai_summary_markdown.strip():
            return ""

        try:
            import markdown2

            # Convert markdown to HTML
            html_content = markdown2.markdown(ai_summary_markdown.strip())

            return f"""
            <div class="section">
                <h2>🤖 AI-Powered Analysis Summary</h2>
                <div class="ai-summary-content" style="
                    background: linear-gradient(135deg, #f8f9ff 0%, #e8f4fd 100%);
                    border-left: 4px solid #667eea;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 15px 0;
                    font-size: 16px;
                    line-height: 1.7;
                    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.1);
                ">
                    {html_content}
                </div>
            </div>
            """
        except Exception as e:
            logger.error(f"Failed to render AI summary markdown: {e}")
            # Fallback to plain text
            return f"""
            <div class="section">
                <h2>🤖 AI-Powered Analysis Summary</h2>
                <div class="ai-summary-content" style="
                    background: linear-gradient(135deg, #f8f9ff 0%, #e8f4fd 100%);
                    border-left: 4px solid #667eea;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 15px 0;
                    font-size: 16px;
                    line-height: 1.7;
                    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.1);
                ">
                    <pre style="white-space: pre-wrap; font-family: inherit; margin: 0;">{ai_summary_markdown}</pre>
                </div>
            </div>
            """

    def _generate_explanation_section(self, explanation_markdown: str) -> str:
        """生成解释说明部分 - 渲染Markdown为HTML"""
        if not explanation_markdown or not explanation_markdown.strip():
            return ""

        try:
            import markdown2

            # Convert markdown to HTML
            html_content = markdown2.markdown(explanation_markdown.strip())

            return f"""
            <div class="section">
                <h2>📝 Analysis Explanation</h2>
                <div class="explanation-content">
                    {html_content}
                </div>
            </div>
            """
        except Exception as e:
            logger.error(f"Failed to render markdown: {e}")
            # Fallback to plain text
            return f"""
            <div class="section">
                <h2>📝 Analysis Explanation</h2>
                <div class="explanation-content">
                    <pre style="white-space: pre-wrap; font-family: inherit;">{explanation_markdown}</pre>
                </div>
            </div>
            """

    def _generate_script_section(self, generated_script_content: str) -> str:
        """生成生成的脚本代码部分 - 带语法高亮"""
        if not generated_script_content or not generated_script_content.strip():
            return ""

        try:
            from pygments import highlight
            from pygments.lexers import SqlLexer, PythonLexer
            from pygments.formatters import HtmlFormatter

            # Determine lexer based on content (simple heuristic)
            if any(keyword in generated_script_content.lower()
                   for keyword in ['select', 'from', 'where', 'join', 'group by']):
                lexer = SqlLexer()
                language_name = "SQL"
            else:
                lexer = PythonLexer()
                language_name = "Python"

            # Generate highlighted HTML
            formatter = HtmlFormatter(style='colorful', cssclass='highlight')
            highlighted_code = highlight(generated_script_content.strip(), lexer, formatter)

            # Get CSS for syntax highlighting
            css_styles = formatter.get_style_defs('.highlight')

            return f"""
            <div class="section">
                <h2>💻 Generated {language_name} Script</h2>
                <style>
                    {css_styles}
                    .highlight {{
                        border-radius: 5px;
                        padding: 15px;
                        overflow-x: auto;
                        font-size: 14px;
                        line-height: 1.4;
                    }}
                </style>
                <div class="script-content">
                    {highlighted_code}
                </div>
            </div>
            """
        except Exception as e:
            logger.error(f"Failed to highlight code: {e}")
            # Fallback to plain code block
            return f"""
            <div class="section">
                <h2>💻 Generated Script</h2>
                <div class="script-content">
                    <pre style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; font-size: 14px; line-height: 1.4;"><code>{generated_script_content}</code></pre>
                </div>
            </div>
            """

    def _generate_footer_section(self, metadata: Dict) -> str:
        """生成页脚部分"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return f"""
        <div class="footer">
            <p>Report generated by Business Intelligence System</p>
            <p>Chart Type: {metadata.get('chart_type', 'Unknown')} | Generated at: {timestamp}</p>
            <p style="margin-top: 15px; font-size: 0.8em;">
                🔧 Powered by LangGraph • 📊 Interactive Visualizations • 🚀 AI-Driven Analytics
            </p>
        </div>
        """

    def _get_library_includes(self, library: str) -> str:
        """获取图表库的CSS/JS引用"""
        includes = {
            "vega": """
            <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
            <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
            <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
            """,
            "plotly": """
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            """,
            "mermaid": """
            <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
            <script>mermaid.initialize({startOnLoad:true});</script>
            """
        }

        return includes.get(library, "")

    def _generate_error_report(self, error_message: str) -> str:
        """生成错误报告"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Report Generation Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; }}
                .error {{ background-color: #f8d7da; color: #721c24; padding: 20px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="error">
                <h2>❌ Report Generation Failed</h2>
                <p>An error occurred while generating the report:</p>
                <pre>{error_message}</pre>
            </div>
        </body>
        </html>
        """