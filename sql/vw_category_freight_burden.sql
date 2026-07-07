CREATE OR REPLACE VIEW raw_data.gold.vw_category_freight_burden AS
SELECT 
    p.product_category_name,
    COUNT(f.order_item_id) AS items_sold,
    ROUND(SUM(f.sales_amount), 2) AS total_revenue,
    ROUND(SUM(f.freight_value), 2) AS total_freight_cost,
    ROUND((SUM(f.freight_value) / NULLIF(SUM(f.sales_amount), 0)) * 100, 2) AS freight_to_revenue_ratio
FROM raw_data.gold.fact_sales f
JOIN raw_data.gold.dim_product p 
    ON f.product_sk = p.product_sk
WHERE p.product_category_name != 'unknown'
GROUP BY 
    p.product_category_name
HAVING SUM(f.sales_amount) > 1000
ORDER BY 
    freight_to_revenue_ratio DESC;