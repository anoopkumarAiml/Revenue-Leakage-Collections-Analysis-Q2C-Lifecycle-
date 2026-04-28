# for calculating the expected revenue 
SELECT 
    SUM(expected_revenue) AS total_expected_revenue
FROM (
    SELECT 
        s.subscription_id,
        
        SUM(
            CASE 
                WHEN i.invoice_date <= DATE_ADD(c.contract_start_date, INTERVAL 1 MONTH)
                THEN p.list_price * (1 - c.discount_percent/100)
                ELSE p.list_price
            END
        ) AS expected_revenue

    FROM subscriptions s
    JOIN contracts c ON s.contract_id = c.contract_id
    JOIN pricing_master p ON s.plan_id = p.plan_id
    JOIN invoices i ON s.subscription_id = i.subscription_id

    WHERE c.discount_end_date IS NULL

    GROUP BY s.subscription_id
) t;


#