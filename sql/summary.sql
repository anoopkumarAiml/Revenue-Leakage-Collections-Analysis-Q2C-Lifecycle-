# Final Summary Table

WITH contract_base AS (
    SELECT 
        c.contract_id,
        s.customer_id,
        s.subscription_id,
        c.plan_id,
        c.billing_type,
        c.final_price,
        c.discount_percent,
        c.discount_end_date,

        CASE 
            WHEN c.billing_type = 'Yearly' THEN c.final_price / 12
            ELSE c.final_price
        END AS expected_monthly_revenue

    FROM q2c.contracts c
    JOIN q2c.subscriptions s 
        ON c.contract_id = s.contract_id
),

invoice_agg AS (
    SELECT 
        subscription_id,
        SUM(amount) AS invoiced_revenue
    FROM q2c.invoices
    GROUP BY subscription_id
),

payment_agg AS (
    SELECT 
        i.subscription_id,
        SUM(c.amount) AS collected_revenue
    FROM q2c.invoices i
    LEFT JOIN q2c.collections c 
        ON i.invoice_id = c.invoice_id
    GROUP BY i.subscription_id
),

event_flags AS (
    SELECT 
        subscription_id,
        MAX(CASE WHEN event_type = 'pause' THEN 1 ELSE 0 END) AS has_pause,
        MAX(CASE WHEN event_type = 'upgrade' THEN 1 ELSE 0 END) AS has_upgrade,
        MAX(CASE WHEN event_type = 'downgrade' THEN 1 ELSE 0 END) AS has_downgrade,
        MAX(CASE WHEN event_type = 'cancel' THEN 1 ELSE 0 END) AS has_cancel
    FROM q2c.events
    GROUP BY subscription_id
)

SELECT 
    cb.contract_id,
    cb.customer_id,

    cb.expected_monthly_revenue,
    COALESCE(i.invoiced_revenue, 0) AS invoiced_revenue,
    COALESCE(p.collected_revenue, 0) AS collected_revenue,

    (cb.expected_monthly_revenue - COALESCE(i.invoiced_revenue, 0)) AS leakage

FROM contract_base cb
LEFT JOIN invoice_agg i 
    ON cb.subscription_id = i.subscription_id
LEFT JOIN payment_agg p 
    ON cb.subscription_id = p.subscription_id
LEFT JOIN event_flags e 
    ON cb.subscription_id = e.subscription_id;