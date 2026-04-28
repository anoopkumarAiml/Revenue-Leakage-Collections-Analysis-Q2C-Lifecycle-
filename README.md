# Revenue Leakage & Collections Analysis (Q2C Lifecycle)

## 1. Problem Statement

In a subscription-based business, revenue leakage occurs when the **expected billing amount (based on contracts and pricing rules)** does not match the **actual invoiced amount**.

This project analyzes the **Quote-to-Cash (Q2C) lifecycle** to identify:

* Where revenue leakage is happening
* Why invoices are incorrect or missing
* How much revenue is not collected (Accounts Receivable risk)

---

## 2. Business Objective

* Quantify **Expected vs Invoiced vs Collected revenue**
* Identify **revenue leakage drivers**
* Detect **data integrity issues** in Q2C flow
* Provide a **Power BI dashboard** for decision-making

---

## 3. Data Overview

The dataset simulates a full Q2C pipeline:

* `cpq_quote` → Quote creation & discount rules
* `contracts` → Contract lifecycle & pricing terms
* `subscriptions` → Active billing entities
* `invoices` → Generated billing records
* `payments` → Actual cash collection
* `events` → Subscription lifecycle changes (pause, cancel, downgrade)
* `pricing_master` → Plan pricing & discount limits

---

## 4. Key Concepts

### Expected Revenue

Revenue that **should be billed** based on:

* Plan price
* Contract start date
* Discount rules
* Subscription lifecycle events

### Invoiced Revenue

Revenue that was **actually billed**:

* Taken directly from `invoices.amount`

### Collected Revenue

Revenue that was **actually received**:

* Derived from `payments.amount`

### Revenue Leakage

```text
Leakage = Expected Revenue − Invoiced Revenue
```

### Outstanding AR

```text
Outstanding = Invoiced Revenue − Collected Revenue
```

---

## 5. Approach

### Step 1: Data Integrity Checks

Validated Q2C lifecycle consistency:

* Quotes with invalid discount limits
* Contracts without valid quote linkage
* Missing or orphan records
* Duplicate detection

---

### Step 2: Revenue Modeling (Core Logic)

#### Expected Revenue

Simulated monthly billing using:

* Contract start date
* Plan pricing
* Discount logic (applied incorrectly due to missing end date)
* Subscription events:

  * Pause → revenue = 0
  * Cancel → revenue stops
  * Downgrade → lower pricing

---

#### Invoiced Revenue

```sql
SUM(invoices.amount)
```

Filtered by:

* Subscription linkage
* Time period

---

#### Collected Revenue

```sql
SUM(payments.amount)
```

Joined via invoice_id

---

### Step 3: Final Data Model

All metrics aligned at:

```text
subscription_id (granularity)
```

Final dataset includes:

* expected_revenue
* invoiced_revenue
* collected_revenue
* leakage
* outstanding

---

## 6. Key Findings

* Significant leakage caused by:

  * Missing `discount_end_date`
  * Continuous discount application beyond first billing cycle
* Contracts generating invoices without proper validation
* Revenue gaps increasing over time due to billing errors
* High AR aging indicating collection inefficiencies

---

## 7. Dashboard Overview (Power BI)

The dashboard provides:

### KPI Metrics

* Total Expected Revenue
* Total Invoiced Revenue
* Total Collected Revenue
* Revenue Leakage
* Outstanding AR
* Leakage %
* Collection Efficiency %

---

### Visual Insights

* Revenue Funnel (Expected → Invoiced → Collected)
* Leakage Contribution by Reason
* Plan-wise Revenue Comparison
* AR Aging Buckets (0–7, 30, 60, 90+ days)
* Top Customers by Leakage
* Expected vs Collected Scatter Analysis
* Monthly Revenue Trend

---

## 8. Business Impact

This analysis helps:

* Detect billing system issues
* Prevent revenue loss
* Improve cash collection efficiency
* Enable proactive risk identification

---

## 9. Tools & Technologies

* SQL (MySQL) → Data extraction & transformation
* Python (Pandas) → EDA & validation
* Power BI → Dashboard & visualization

---

## 10. Project Structure

```text
project/
│
├── data/
│   ├── contracts.csv
│   ├── subscriptions.csv
│   ├── invoices.csv
│   ├── payments.csv
│   ├── events.csv
│   ├── pricing_master.csv
│
├── notebooks/
│   └── EDA.ipynb
│
├── sql/
│   └── summary.sql
│
├── dashboard/
│   └── powerbi.pbix
│
└── README.md
```

---

## 11. Key Learning

* Expected revenue must be **simulated**, not derived from invoices
* Data modeling is more important than writing queries
* Granularity consistency (subscription level) is critical
* Visualization is only as good as underlying data

---

## 12. Future Improvements

* Incorporate upgrade events (currently limited)
* Improve event-driven revenue modeling
* Automate anomaly detection
* Deploy dashboard for real-time monitoring

---

## 13. Conclusion

This project demonstrates how structured data modeling across the Q2C lifecycle can uncover hidden revenue leakage and improve financial visibility.

The combination of **SQL, data modeling, and visualization** provides a scalable approach to solving real-world billing and revenue challenges.
