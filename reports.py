import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import psycopg2
import os

def monthly_report():

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))

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
