import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

def monthly_report():

    conn=sqlite3.connect("expenses.db")

    df=pd.read_sql("""
    SELECT category,SUM(amount) as total
    FROM transactions
    WHERE strftime('%Y-%m',date)=strftime('%Y-%m','now')
    GROUP BY category
    """,conn)

    plt.figure()
    df.plot(kind="bar",x="category",y="total")

    path="report.png"
    plt.savefig(path)

    return path