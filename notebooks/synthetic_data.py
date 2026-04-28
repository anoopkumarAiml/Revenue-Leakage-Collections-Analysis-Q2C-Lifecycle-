import pandas as pd
import numpy as np

np.random.seed(42)  # for reproducibility


n = 40000

pricing_master = pd.DataFrame({
    "plan_id": ["BM", "PM", "BY", "PY"],
    "plan_name": ["Base", "Pro", "Base", "Pro"],
    "billing_type": ["Monthly", "Monthly", "Yearly", "Yearly"],
    "list_price": [400, 1000, 4000, 10000],
    "currency": ["USD", "USD", "USD", "USD"],
    "is_active": [1, 1, 1, 1],
    "max_discount_percent": [10, 25, 10, 15]
})

# -----------------------------
# Step 2: Create quotes
# -----------------------------
quotes = pd.DataFrame({
    "quote_id": [f"Q{i+1}" for i in range(n)],
    "customer_id": [f"C{i+1}" for i in range(n)],
    "plan_id": np.random.choice(pricing_master["plan_id"], n)
})

# -----------------------------
# Step 3: Add dates (important)
# -----------------------------
quotes["quote_date"] = pd.to_datetime("2024-01-01") + pd.to_timedelta(
    np.random.randint(0, 60, n), unit="D"
)

# Month-end flag
quotes["is_month_end"] = quotes["quote_date"].dt.is_month_end

# -----------------------------
# Step 4: Merge pricing
# -----------------------------
quotes = quotes.merge(pricing_master, on="plan_id", how="left")

# -----------------------------
# Step 5: Assign discount (behavior-based)
# -----------------------------
quotes["discount_percent"] = np.where(
    quotes["is_month_end"],
    np.random.randint(15, 30, n),   # high discount
    np.random.randint(0, 15, n)     # normal discount
)

# Cap discount to max allowed (normal cases)
quotes["discount_percent"] = np.minimum(
    quotes["discount_percent"],
    quotes["max_discount_percent"]
)

# -----------------------------
# Step 6: Discount duration (1 month)
# -----------------------------
quotes["discount_duration_months"] = np.where(
    quotes["discount_percent"] > 0, 1, 0
)

quotes["discount_start_date"] = quotes["quote_date"]

quotes["expected_end_date"] = quotes["discount_start_date"] + pd.to_timedelta(30, unit="D")

# -----------------------------
# Step 7: Create leakage (THIS IS KEY)
# -----------------------------
leak_mask = np.where(
    quotes["is_month_end"],
    np.random.rand(n) < 0.5,   # high error at month-end
    np.random.rand(n) < 0.1    # low error normally
)

quotes["discount_end_date"] = quotes["expected_end_date"]
quotes.loc[leak_mask, "discount_end_date"] = None

# -----------------------------
# Step 8: Final price
# -----------------------------
quotes["final_price"] = quotes["list_price"] * (
    1 - quotes["discount_percent"] / 100
)

# -----------------------------
# Status
# -----------------------------
quotes["status"] = np.random.choice(
    ["Draft", "Approved", "Rejected", "Converted"],
    size=len(quotes),
    p=[0.2, 0.3, 0.2, 0.3]
)

# -----------------------------
# Output
# -----------------------------
#print(quotes)
#pricing_master.to_csv("pricing_master.csv", index=False)
#quotes.to_csv("quotes_with_leakage.csv", index=False)



final_quotes = quotes[[
    "quote_id",
    "customer_id",
    "plan_id",
    "list_price",
    "discount_percent",
    "discount_start_date",
    "discount_end_date",
    "final_price",
    "quote_date",
    "status"
]]

final_quotes["quote_end_date"] = None

#print(final_quotes)



converted_quotes = final_quotes[final_quotes["status"] == "Converted"].copy()

converted_quotes = converted_quotes.merge(
    pricing_master[["plan_id", "billing_type"]],
    on="plan_id",
    how="left"
)

converted_quotes["contract_id"] = ["CT" + str(i+1) for i in range(len(converted_quotes))]

converted_quotes["contract_start_date"] = converted_quotes["quote_date"] + pd.to_timedelta(
    np.random.randint(1, 5, len(converted_quotes)), unit="D"
)
converted_quotes["contract_status"] = "Active"
converted_quotes["version"] = 1

contracts = converted_quotes[[
    "contract_id",
    "quote_id",
    "customer_id",
    "plan_id",
    "billing_type",
    "contract_start_date",
    "final_price",
    "discount_percent",
    "discount_end_date",
    "contract_status",
    "version"
]]

#print(contracts)



subscriptions = contracts.copy()
subscriptions["subscription_id"] = ["S" + str(i+1) for i in range(len(subscriptions))]
subscriptions["subscription_start_date"] = subscriptions["contract_start_date"]
subscriptions["subscription_status"] = "Active"

subscriptions = subscriptions[[
    "subscription_id",
    "contract_id",
    "customer_id",
    "plan_id",
    "billing_type",
    "subscription_start_date",
    "subscription_status"
]]

#print(subscriptions.head())

upgrades = []

for _, row in subscriptions.iterrows():

    if row["billing_type"] == "Monthly" and np.random.rand() < 0.3:

        upgrade_month = np.random.randint(2, 10)

        upgrades.append({
            "subscription_id": row["subscription_id"],
            "upgrade_month": upgrade_month,
            "new_plan_id": "PM" if row["plan_id"] == "BM" else "PY"
        })

upgrades_df = pd.DataFrame(upgrades)

events = []

for _, row in subscriptions.iterrows():

    sub_id = row["subscription_id"]

    # downgrade
    if np.random.rand() < 0.2:
        events.append({
            "subscription_id": sub_id,
            "event_type": "downgrade",
            "month": np.random.randint(3, 10),
            "plan_id": "BM"
        })

    # pause
    if np.random.rand() < 0.2:
        start = np.random.randint(3, 8)
        end = start + np.random.randint(1, 3)
        events.append({
            "subscription_id": sub_id,
            "event_type": "pause",
            "start_month": start,
            "end_month": end
        })

    # cancel
    if np.random.rand() < 0.1:
        events.append({
            "subscription_id": sub_id,
            "event_type": "cancel",
            "month": np.random.randint(5, 12)
        })

events_df = pd.DataFrame(events)

contracts["version"] = 1

contracts["contract_end_date"] = None

new_contracts = []
new_subscriptions = []
amendment_quotes = []

for _, row in upgrades_df.iterrows():

    sub_id = row["subscription_id"]
    new_plan = row["new_plan_id"]

    sub_row = subscriptions[
        subscriptions["subscription_id"] == sub_id
    ].iloc[0]

    idx = sub_row.name

    upgrade_date = sub_row["subscription_start_date"] + pd.DateOffset(
        months=row["upgrade_month"]
    )

    old_contract = contracts.loc[idx]

    # -----------------------------
    # 1. TERMINATE OLD CONTRACT
    # -----------------------------
    contracts.loc[idx, "contract_status"] = "Terminated"
    contracts.loc[idx, "contract_end_date"] = upgrade_date

    # INTENTIONAL BUG: old subscription not terminated
    subscriptions.loc[idx, "subscription_status"] = "Active"

    # -----------------------------
    # 2. CLOSE OLD QUOTE
    # -----------------------------
    final_quotes.loc[
    final_quotes["quote_id"] == old_contract["quote_id"],
    ["status", "quote_end_date"]
    ] = ["Amended", upgrade_date]

    # -----------------------------
    # 3. CREATE AMENDMENT QUOTE
    # -----------------------------
    new_quote_id = "AQ_" + sub_id

    amendment_quotes.append({
        "quote_id": new_quote_id,
        "customer_id": sub_row["customer_id"],
        "plan_id": new_plan,
        "list_price": pricing_master[
            pricing_master["plan_id"] == new_plan
        ]["list_price"].values[0],
        "discount_percent": 0,
        "discount_start_date": upgrade_date,
        "discount_end_date": None,
        "final_price": pricing_master[
            pricing_master["plan_id"] == new_plan
        ]["list_price"].values[0],
        "quote_date": upgrade_date,
        "status": "Converted"
    })

    # -----------------------------
    # 4. CREATE NEW CONTRACT
    # -----------------------------
    new_contract_id = "CT_NEW_" + sub_id

    new_contracts.append({
        "contract_id": new_contract_id,
        "quote_id": new_quote_id,
        "customer_id": sub_row["customer_id"],
        "plan_id": new_plan,
        "billing_type": sub_row["billing_type"],
        "contract_start_date": upgrade_date,
        "final_price": pricing_master[
            pricing_master["plan_id"] == new_plan
        ]["list_price"].values[0],
        "discount_percent": 0,
        "discount_end_date": None,
        "contract_status": "Active",
        "version": 2,
        "parent_contract_id": old_contract["contract_id"],
        "contract_end_date": None
    })

    # -----------------------------
    # 5. CREATE NEW SUBSCRIPTION
    # -----------------------------
    new_subscriptions.append({
        "subscription_id": "S_NEW_" + sub_id,
        "contract_id": new_contract_id,
        "customer_id": sub_row["customer_id"],
        "plan_id": new_plan,
        "billing_type": sub_row["billing_type"],
        "subscription_start_date": upgrade_date,
        "subscription_status": "Active"
    })

# append all
contracts = pd.concat([contracts, pd.DataFrame(new_contracts)], ignore_index=True)
#contracts.to_csv("contracts.csv", index=False)
subscriptions = pd.concat([subscriptions, pd.DataFrame(new_subscriptions)], ignore_index=True)
#subscriptions.to_csv("subscriptions.csv", index=False)
final_quotes = pd.concat([final_quotes, pd.DataFrame(amendment_quotes)], ignore_index=True)
#final_quotes.to_csv("cpq_quote.csv", index=False)

invoices = []
invoice_counter = 1

contract_map = contracts.set_index("contract_id").to_dict("index")
for _, row in subscriptions.iterrows():

    start_date = pd.to_datetime(row["subscription_start_date"])
    billing_type = row["billing_type"]

    contract_row = contract_map[row["contract_id"]]

    discount_percent = contract_row["discount_percent"]
    discount_end = contract_row["discount_end_date"]

    current_plan = row["plan_id"]

    # upgrade lookup
    upgrade_row = upgrades_df[
        upgrades_df["subscription_id"] == row["subscription_id"]
    ]

    upgrade_month = None
    new_plan = None

    # FIX: skip upgrade for new subscription
    if not row["subscription_id"].startswith("S_NEW_"):
        if not upgrade_row.empty:
            upgrade_month = int(upgrade_row.iloc[0]["upgrade_month"])
            new_plan = upgrade_row.iloc[0]["new_plan_id"]

    # =========================
    # MONTHLY
    # =========================
    if billing_type == "Monthly":

        for m in range(12):

            # EVENT CONTROL
            if row["subscription_id"].startswith("S_NEW_"):
                sub_events = pd.DataFrame(columns=["subscription_id", "event_type", "month", "plan_id", "start_month", "end_month"])
            else:
                sub_events = events_df[
                events_df["subscription_id"] == row["subscription_id"]
                ]

            # CANCEL
            cancel_event = sub_events[sub_events["event_type"] == "cancel"]
            if not cancel_event.empty:
                cancel_month = int(cancel_event.iloc[0]["month"])
                if m >= cancel_month:
                    break

            # PAUSE
            pause_event = sub_events[sub_events["event_type"] == "pause"]
            if not pause_event.empty:
                pause_start = int(pause_event.iloc[0]["start_month"])
                pause_end = int(pause_event.iloc[0]["end_month"])

                if pause_start <= m <= pause_end:
                    continue

            # DOWNGRADE
            downgrade_event = sub_events[sub_events["event_type"] == "downgrade"]
            if not downgrade_event.empty:
                downgrade_month = int(downgrade_event.iloc[0]["month"])

                if m == downgrade_month and (upgrade_month is None or m != upgrade_month):
                    current_plan = downgrade_event.iloc[0]["plan_id"]

            # BILLING
            base_date = start_date + pd.DateOffset(months=m)

            invoice_date = base_date + pd.to_timedelta(
                np.random.randint(0, 5), unit="D"
            )

            contract_end = contract_row.get("contract_end_date")

            if pd.notna(contract_end):
                if invoice_date >= contract_end:
                    break

            old_price = pricing_master[
                pricing_master["plan_id"] == current_plan
            ]["list_price"].values[0]

            # UPGRADE
            if upgrade_month is not None and m == upgrade_month:
                new_price = pricing_master[
                pricing_master["plan_id"] == new_plan
                ]["list_price"].values[0]

                # REAL PRORATION
                days_in_month = 30
                upgrade_day = np.random.randint(10, 20)

                old_days = upgrade_day
                new_days = days_in_month - upgrade_day

                amount = (old_price * old_days / days_in_month) + (new_price * new_days / days_in_month)

                current_plan = new_plan

                

            elif upgrade_month is not None and m > upgrade_month:

                new_price = pricing_master[
                    pricing_master["plan_id"] == new_plan
                ]["list_price"].values[0]

                amount = new_price

            else:
                amount = old_price

           
            # DISCOUNT (ONLY BEFORE UPGRADE)
            if not (upgrade_month is not None and m >= upgrade_month):

                if pd.isna(discount_end):
                    amount = amount * (1 - discount_percent / 100)
                elif invoice_date <= pd.to_datetime(discount_end):
                    amount = amount * (1 - discount_percent / 100)

            invoices.append({
                "invoice_id": "INV" + str(invoice_counter),
                "subscription_id": row["subscription_id"],
                "customer_id": row["customer_id"],
                "plan_id": current_plan,
                "invoice_date": invoice_date,
                "amount": round(amount, 2)
            })

            invoice_counter += 1

    # =========================
    # YEARLY
    # =========================
    else:

        list_price = pricing_master[
            pricing_master["plan_id"] == current_plan
        ]["list_price"].values[0]

        invoice_date = start_date + pd.to_timedelta(
            np.random.randint(0, 5), unit="D"
        )

        amount = list_price * (1 - discount_percent / 100)

        invoices.append({
            "invoice_id": "INV" + str(invoice_counter),
            "subscription_id": row["subscription_id"],
            "customer_id": row["customer_id"],
            "plan_id": current_plan,
            "invoice_date": invoice_date,
            "amount": round(amount, 2)
        })

        invoice_counter += 1


invoices_df = pd.DataFrame(invoices)

invoices_df = invoices_df.sort_values(by=["invoice_date", "customer_id"])

#invoices_df.to_csv("invoices.csv", index=False)

print(invoices_df.head(20))



customer_summary = invoices_df.groupby("customer_id").agg({
    "amount": "sum"
}).reset_index()

#ustomer_summary.to_csv("customer_summary.csv", index=False)



payments = []
payment_counter = 1

for _, row in invoices_df.iterrows():

    invoice_date = pd.to_datetime(row["invoice_date"])
    amount = row["amount"]

    rand = np.random.rand()

    if rand < 0.7:
        status = "Paid"
        delay_days = np.random.randint(0, 10)
        amount_paid = amount

    elif rand < 0.85:
        status = "Late"
        delay_days = np.random.randint(10, 30)
        amount_paid = amount

    elif rand < 0.95:
        status = "Partial"
        delay_days = np.random.randint(5, 20)
        amount_paid = amount * np.random.uniform(0.3, 0.8)

    else:
        status = "Failed"
        delay_days = None
        amount_paid = 0

    payment_date = (
        invoice_date + pd.to_timedelta(delay_days, unit="D")
        if delay_days is not None else None
    )

    payments.append({
        "payment_id": "PAY" + str(payment_counter),
        "invoice_id": row["invoice_id"],
        "customer_id": row["customer_id"],
        "payment_date": payment_date,
        "amount_paid": round(amount_paid, 2),
        "payment_status": status
    })

    payment_counter += 1

payments_df = pd.DataFrame(payments)

#payments_df.to_csv("payments.csv", index=False)

print(payments_df.head(20))



collections = []
collection_counter = 1

for _, row in payments_df.iterrows():

    invoice_id = row["invoice_id"]
    customer_id = row["customer_id"]
    payment_status = row["payment_status"]
    payment_date = row["payment_date"]

    # get invoice info
    invoice_row = invoices_df[invoices_df["invoice_id"] == invoice_id].iloc[0]
    invoice_amount = invoice_row["amount"]
    invoice_date = invoice_row["invoice_date"]

    amount_paid = row["amount_paid"]
    remaining = invoice_amount - amount_paid

    # only if something is unpaid
    if remaining > 0:

        rand = np.random.rand()

        if rand < 0.6:
            collected_amount = remaining * np.random.uniform(0.5, 1.0)
            status = "Recovered"
        else:
            collected_amount = 0
            status = "Unrecovered"

        # correct date logic
        base_date = pd.to_datetime(payment_date) if pd.notna(payment_date) else pd.to_datetime(invoice_date)

        collection_date = base_date + pd.to_timedelta(
            np.random.randint(5, 20), unit="D"
        )

        collections.append({
            "collection_id": "COL" + str(collection_counter),
            "invoice_id": invoice_id,
            "customer_id": customer_id,
            "collection_date": collection_date,
            "amount_collected": round(collected_amount, 2),
            "collection_status": status
        })

        collection_counter += 1


collections_df = pd.DataFrame(collections)

#collections_df.to_csv("collections.csv", index=False)

print(collections_df.head(20))

events_df.to_csv("events.csv", index=False)