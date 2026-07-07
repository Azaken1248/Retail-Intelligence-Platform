CREATE OR REPLACE VIEW raw_data.gold.vw_monthly_sales AS
SELECT 
    d.calendar_year AS sales_year,
    d.calendar_month AS sales_month,
    COUNT(DISTINCT f.order_id) AS total_orders,
    COUNT(f.order_item_id) AS total_items_sold,
    ROUND(SUM(f.sales_amount), 2) AS total_revenue,
    ROUND(SUM(f.freight_value), 2) AS total_freight_cost
FROM raw_data.gold.fact_sales f
JOIN raw_data.gold.dim_date d 
    ON f.order_date_sk = d.date_sk
GROUP BY 
    d.calendar_year, 
    d.calendar_month
ORDER BY 
    d.calendar_year DESC, 
    d.calendar_month DESC;