CREATE OR REPLACE VIEW raw_data.gold.vw_customer_ltv_ranking AS
WITH customer_metrics AS (
    SELECT 
        customer_sk,
        COUNT(DISTINCT order_id) AS total_orders,
        SUM(sales_amount) AS lifetime_value
    FROM raw_data.gold.fact_sales
    GROUP BY 
        customer_sk
)
SELECT 
    customer_sk,
    total_orders,
    ROUND(lifetime_value, 2) AS lifetime_value,
    NTILE(10) OVER (ORDER BY lifetime_value DESC) AS ltv_decile,
    DENSE_RANK() OVER (ORDER BY lifetime_value DESC) AS ltv_rank
FROM customer_metrics
WHERE lifetime_value > 0
ORDER BY 
    ltv_rank ASC;