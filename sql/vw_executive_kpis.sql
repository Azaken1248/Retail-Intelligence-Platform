CREATE OR REPLACE VIEW raw_data.gold.vw_executive_kpis AS
SELECT 
    COUNT(DISTINCT f.order_id) AS total_lifetime_orders,
    COUNT(DISTINCT f.customer_sk) AS total_unique_customers,
    ROUND(SUM(f.sales_amount), 2) AS total_lifetime_revenue,
    ROUND(SUM(f.sales_amount) / COUNT(DISTINCT f.order_id), 2) AS average_order_value
FROM raw_data.gold.fact_sales f;