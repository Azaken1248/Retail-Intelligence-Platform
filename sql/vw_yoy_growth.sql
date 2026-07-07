CREATE OR REPLACE VIEW raw_data.gold.vw_yoy_growth AS
WITH yearly_sales AS (
    SELECT 
        d.calendar_year,
        SUM(f.sales_amount) AS total_revenue
    FROM raw_data.gold.fact_sales f
    JOIN raw_data.gold.dim_date d 
        ON f.order_date_sk = d.date_sk
    GROUP BY 
        d.calendar_year
)
SELECT 
    calendar_year,
    ROUND(total_revenue, 2) AS current_revenue,
    ROUND(LAG(total_revenue) OVER (ORDER BY calendar_year), 2) AS previous_year_revenue,
    ROUND(
        (total_revenue - LAG(total_revenue) OVER (ORDER BY calendar_year)) 
        / NULLIF(LAG(total_revenue) OVER (ORDER BY calendar_year), 0) * 100, 
    2) AS yoy_growth_percentage
FROM yearly_sales
ORDER BY 
    calendar_year DESC;