"""
Prompt Templates for the AI Database Analyst Workflow

This module centralizes all prompt templates used across the application,
making them easier to manage, version, and update.
"""
# -----------------------------------------------------------------
# -----------------------------------------------------------------

DATABASE_SCHEMA_INFO = """
## BigQuery Database Schema Information

### Core Fact Table: rpt_fct_order
| Field Name | Type | Description |
|---|---|---|
| sales_channel_id | INTEGER | Sales Channel ID |
| sales_channel_type_id | INTEGER | Sales Channel Type ID |
| market_region_id | INTEGER | Market Region ID |
| order_date | DATE | Order Date |
| channel_id | STRING | Channel ID |
| item_id | INTEGER | Item ID |
| units | INTEGER | Units Sold |
| item_promotion_discount_usd | FLOAT | Item Promotion Discount (USD) |
| ship_promotion_discount_usd | FLOAT | Shipping Promotion Discount (USD) |
| tax_usd | FLOAT | Tax (USD) |
| gross_sales_usd | FLOAT | Gross Sales (USD) |
| gross_revenue_usd | FLOAT | Gross Revenue (USD) |
| cogs_usd | FLOAT | Cost of Goods Sold (USD) |
| refund_usd | FLOAT | Refund (USD) |
| referral_fee_refund_usd | FLOAT | Referral Fee Refund (USD) |
| refund_administration_fee_usd | FLOAT | Refund Administration Fee (USD) |
| warehousing_cost_usd | FLOAT | Warehousing Cost (USD) |
| transportation_cost_usd | FLOAT | Transportation Cost (USD) |
| fba_inbound_placement_fee_usd | FLOAT | FBA Inbound Placement Fee (USD) |
| amz_fba_fee_usd | FLOAT | Amazon FBA Fee (USD) |
| referral_fee_order_usd | FLOAT | Order Referral Fee (USD) |
| net_revenue_usd | FLOAT | Net Revenue (USD) |
| gross_profit_usd | FLOAT | Gross Profit (USD) |

### Core Dimension Table: rpt_dim_item
| Field Name | Type | Description |
|---|---|---|
| channel_id | STRING | Channel ID |
| item_id | INTEGER | Item ID |
| sub_brand | STRING | Sub-brand Name |
| parent_asin | STRING | Parent ASIN |
| is_current | BOOLEAN | Is Current |
| is_item_inactive | STRING | Is Item Inactive (T/F) |
| item_sku | STRING | Item SKU |
| listing_status | STRING | Listing Status (Active/Discontinued/Divested) |

### Table Join Relationship
- Primary JOIN: rpt_fct_order.item_id = rpt_dim_item.item_id
- It is recommended to always join using item_id.
"""

SAMPLE_DATA_INFO = """
## Sample Data

### rpt_dim_item Sample Data
| channel_id | item_id | sub_brand | parent_asin | listing_status |
|---|---|---|---|---|
| B09JPHT1XH | 130987 | B-Six | B09JPK9WHZ | Discontinued |
| B091BBKX9G | 45435 | B-Six | None | Discontinued |
| B07XQ52GY3 | 59966 | BARTSTR | B07XQ52GY3 | Divested |
| B075X2XKBZ | 20517 | BEARD KING | B075X2XKBZ | Divested |
| B09DGVCQ7R | 125919 | DMD | B0BSGB4ZKG | Active |

### Common Field Value Ranges
- sub_brand: B-Six, BARTSTR, BEARD KING, Becky Cameron, Checkered Chef, DMD, DRIVE AUTO PRODUCTS, etc.
- listing_status: Active, Discontinued, Divested
- is_item_inactive: 'T' (True), 'F' (False)
"""








# -----------------------------------------------------------------
# -----------------------------------------------------------------
CHIEF_ARCHITECT_PROMPT = """
You are a top-tier BigQuery data analyst and query architect. Based on the user's question, reference queries, and database information, write an optimal BigQuery query script to answer the user's question.

## User Question
{user_question}

{reference_section}

{database_schema}

{sample_data}

{correction_section}

## Core Instructions and Constraints

### Multi-step Query Authorization
If you are unsure about the possible values of a field (e.g., `listing_status`), **you can first write a `SELECT DISTINCT listing_status FROM ...` query to explore**. You can output a plan with multiple steps. Note that your multi-step interactions are completed within a single Python script.

### Token Limit Warning
Note that your total input (including the question, schema, etc.) has been limited to under 100k tokens. Please use this information efficiently.

### Aggregation First Principle
When filtering is needed, prioritize using aggregation (e.g., `COUNT`, `SUM`) to show statistical counts. **Do not return a large number of raw data rows**.

### Column Relevance Principle
In the final `SELECT` statement, **only include columns that are directly relevant to the user's question**, avoiding unnecessary information.

### Performance Optimization Requirements
- Use appropriate WHERE clauses to filter data.
- Limit the result set to a reasonable size.
- Avoid `SELECT *` unless specifically necessary.
- Use aggregation instead of raw data.
- Include necessary `LIMIT` clauses.

## Output Format Requirements

Please return the result in strict JSON format:

{{
    "explanation": "This script first queries... then...",
    "query_plan": [
        {{
            "step": 1,
            "description": "Explore available values for 'sub_brand'",
            "sql": "SELECT DISTINCT sub_brand FROM `YOUR_TABLE` LIMIT 100;"
        }},
        {{
            "step": 2,
            "description": "Based on the user question and exploration results, calculate the final brand sales ranking",
            "sql": "SELECT d.sub_brand, SUM(f.gross_sales_usd) as total_revenue FROM ... WHERE ... GROUP BY ... ORDER BY ...;"
        }}
    ],
    "final_sql_python": "The complete Python script code, including BigQuery execution logic"
}}

## Python Script Template Requirements

`final_sql_python` should contain the complete Python script, formatted as follows:

```python
import os
from google.cloud import bigquery
from datetime import datetime, timedelta

def execute_analysis():
    \"\"\"执行数据分析查询\"\"\"

    # 初始化BigQuery客户端
    client = bigquery.Client(project="YOUR_TABLE")

    try:
        # 如果有多步查询，在这里执行
        # 步骤1: 探索性查询
        if len(query_plan) > 1:
            for i, step in enumerate(query_plan[:-1], 1):
                print(f"执行步骤 {{i}}: {{step['description']}}")
                result = client.query(step['sql']).result()
                # 处理中间结果...

        # 最终查询
        final_query = \"\"\"
        这里是最终的SQL查询
        \"\"\"

        print("执行最终查询...")
        query_job = client.query(final_query)
        results = query_job.result()

        # 转换结果为字典列表
        data = []
        for row in results:
            data.append(dict(row))

        return {{
            "success": True,
            "results": data,
            "row_count": len(data),
            "query_metadata": {{
                "execution_time": query_job.ended - query_job.started if query_job.ended and query_job.started else None,
                "bytes_processed": query_job.total_bytes_processed,
                "cost_estimate_usd": None
            }}
        }}

    except Exception as e:
        return {{
            "success": False,
            "error": str(e),
            "results": []
        }}

if __name__ == "__main__":
    result = execute_analysis()
    print(f"查询结果: {{result}}")
```

Please ensure:
1. The returned format is valid JSON.
2. The Python script syntax is correct.
3. Appropriate error handling is included.
4. The query is optimized to avoid exceeding the 200GB processing limit.
"""









# -----------------------------------------------------------------
# -----------------------------------------------------------------

SEMANTIC_MATCHING_PROMPT = """
You are a semantic matching expert. Please compare the user's question with the list of questions below and find the most semantically similar one.

**User Question**: {user_question}

**Question List**:
{questions_list}

**Matching Criteria**:
- Confidence Threshold: 0.75 (must be met to be considered a successful match)
- Semantic Similarity: Consider the core intent of the question, not just the surface text.
- Example: "Which brand sold the best last month?" and "What was the top-selling brand by revenue in the past 30 days?" are highly similar.

**Output Requirements**:
Please return the result in strict JSON format:

{{
    "match_found": true/false,
    "matched_ids": [1, 2],
    "confidence": 0.85,
    "reasoning": "Detailed explanation of the matching logic and confidence calculation",
    "alternatives": [3, 4]
}}

**Explanation**:
- match_found: Whether a match with confidence ≥ 0.75 was found.
- matched_ids: A list of the best-matched question IDs (sorted by similarity).
- confidence: The confidence score of the best match (0-1).
- reasoning: A detailed explanation of the matching decision.
- alternatives: Other potentially relevant but lower-confidence question IDs.

Please ensure the output is valid JSON without any markdown code block markers.
"""














# -----------------------------------------------------------------
# -----------------------------------------------------------------
VISUALIZATION_AI_SUMMARY_PROMPT = """
You are a senior data analyst. Based on the user's question and the provided data analysis results, generate a concise yet insightful analysis summary in English.

Requirements:
1. Use Markdown format.
2. Focus on key trends, patterns, and insights in the data.
3. Answer the user's core question.
4. Provide specific numbers to support your points.
5. Offer actionable business recommendations.
6. Keep the length under 1000 words.

Please output the Markdown content directly, without any introductory or concluding remarks.
"""











# -----------------------------------------------------------------
# -----------------------------------------------------------------
SCRIPT_VALIDATION_PROMPT = """
You are an expert data analyst responsible for validating BigQuery execution results.

## Original User Question:
{user_question}

## Generated SQL Query:
```sql
{sql_query}
```

## Execution Results:
- Success: {execution_success}
- Row Count: {row_count}
- Execution Time: {execution_time} seconds
- Data Size Processed: {bytes_processed} bytes
- Cost Estimate: ${cost_estimate}
- Error Message: {error_message}

## Sample Data (first 5 rows):
{sample_data}

## Data Summary:
{data_summary}

## Validation Criteria:

### 1. Execution Status (Weight: 20%)
- Did the query execute successfully?
- Are there any technical errors?

### 2. Data Relevance (Weight: 25%)
- Does the returned data directly answer the user's question?
- Are the columns and metrics appropriate for the question?
- Is the data scope (time range, filters) appropriate?

### 3. Data Completeness (Weight: 20%)
- Is there sufficient data to provide meaningful insights?
- Are there obvious gaps or missing data points?
- Is the sample size adequate for analysis?

### 4. Data Quality (Weight: 15%)
- Are there any data anomalies or inconsistencies?
- Do the values make business sense?
- Are there excessive null values or outliers?

### 5. Token Compliance (Weight: 10%)
- Does the result size stay within the 100k token limit?
- Is the data volume manageable for LLM processing?

### 6. Result Interpretability (Weight: 10%)
- Can the results be easily understood and explained to users?
- Is the data structure clear and logical?

## Required Response Format:

Provide your assessment in the following JSON format:

{{
    "execution_assessment": {{
        "technical_success": true/false,
        "error_analysis": "description of any technical issues"
    }},
    "quality_scores": {{
        "data_relevance": 0.85,
        "data_completeness": 0.90,
        "data_quality": 0.75,
        "token_compliance": 1.0,
        "result_interpretability": 0.80,
        "overall_weighted_score": 0.82
    }},
    "data_quality_metrics": {{
        "has_meaningful_data": true,
        "appropriate_time_range": true,
        "relevant_metrics": true,
        "reasonable_data_volume": true,
        "null_value_ratio": 0.05,
        "outlier_detection": "within normal range"
    }},
    "validation_decision": "approved|needs_revision|rejected",
    "improvement_suggestions": [
        "Consider adding time-based filtering for more recent data",
        "Include additional metrics like profit margins for completeness"
    ],
    "reasoning": "Detailed explanation of validation decision and key factors",
    "confidence": 0.90
}}

## Decision Guidelines:
- **approved**: Overall score ≥ 0.7 and all critical criteria met
- **needs_revision**: 0.5 ≤ Overall score < 0.7 or specific issues identified
- **rejected**: Overall score < 0.5 or fundamental execution failures
"""




# -----------------------------------------------------------------
# -----------------------------------------------------------------

EXPLAIN_RESULTS_PROMPT = """
You are a friendly data analyst. Please explain in the simplest, non-technical language what the following data query does and how it answers the question for your boss.

**User Question:** {user_question}

**SQL Query:**
```sql
{generated_sql}
```

**Query Result Overview:**
- Total rows returned: {total_rows}
- Execution successful: {execution_success_text}

**Validation Explanation:** {validation_reasoning}

Please provide:
1. **Simple Explanation**: Explain in non-technical language what this query does and how it answers the user's question.
2. **Key Findings**: Briefly summarize the main findings from the data (if any).
3. **Data Description**: Explain the meaning of the returned data fields.

Please respond in markdown format, maintaining a concise and friendly tone.
"""

