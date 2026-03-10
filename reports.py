import pandas as pd
import matplotlib.pyplot as plt
import psycopg2
import os

def monthly_report():

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))

    df = pd.read_sql("""
    SELECT category, SUM(amount) AS total
    FROM transactions
    WHERE date_trunc('month', date) = date_trunc('month', CURRENT_DATE)
    GROUP BY category
    ORDER BY total DESC
    """, conn)

    conn.close()

    if df.empty:
        raise Exception("No transactions this month")

    plt.figure(figsize=(10,6))

    bars = plt.bar(df["category"], df["total"])

    plt.title("Monthly Spending by Category", fontsize=16)
    plt.xlabel("Category")
    plt.ylabel("Amount (RM)")

    plt.xticks(rotation=30)

    # add value labels
    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width()/2,
            height,
            f"{height:.2f}",
            ha='center',
            va='bottom'
        )

    plt.tight_layout()

    path = "report.png"
    plt.savefig(path)
    plt.close()

    return path
