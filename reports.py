import pandas as pd
import matplotlib.pyplot as plt
import psycopg2
import os

def monthly_report():

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))

    category_df = pd.read_sql("""
    SELECT category, SUM(amount) AS total
    FROM transactions
    WHERE date_trunc('month', date) = date_trunc('month', CURRENT_DATE)
    GROUP BY category
    ORDER BY total DESC
    """, conn)

    daily_df = pd.read_sql("""
    SELECT DATE(date) as day, SUM(amount) as total
    FROM transactions
    WHERE date_trunc('month', date) = date_trunc('month', CURRENT_DATE)
    GROUP BY day
    ORDER BY day
    """, conn)

    conn.close()

    if category_df.empty:
        raise Exception("No transactions this month")

    plt.figure(figsize=(14,8))

    # --- Category Bar Chart ---
    plt.subplot(2,2,1)
    bars = plt.bar(category_df["category"], category_df["total"])
    plt.title("Spending by Category")
    plt.xticks(rotation=30)
    plt.ylabel("RM")

    for bar in bars:
        h = bar.get_height()
        plt.text(
            bar.get_x()+bar.get_width()/2,
            h,
            f"{h:.2f}",
            ha="center"
        )

    # --- Pie Chart ---
    plt.subplot(2,2,2)
    plt.pie(
        category_df["total"],
        labels=category_df["category"],
        autopct="%1.1f%%",
        startangle=140
    )
    plt.title("Spending Distribution")

    # --- Daily Spending ---
    plt.subplot(2,1,2)
    plt.plot(daily_df["day"], daily_df["total"], marker="o")
    plt.title("Daily Spending Trend")
    plt.xlabel("Date")
    plt.ylabel("RM")
    plt.grid(True)

    plt.tight_layout()

    path = "report.png"
    plt.savefig(path)
    plt.close()

    return path
