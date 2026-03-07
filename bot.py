import discord
import sqlite3
import os
from dotenv import load_dotenv
from parser import parse_message
from reports import monthly_report
import psycopg2

load_dotenv()

TOKEN=os.getenv("TOKEN")

GX=os.getenv("GX_CHANNEL")
CIMB=os.getenv("CIMB_CHANNEL")
TNG=os.getenv("TNG_CHANNEL")

GENERAL=os.getenv("GENERAL_CHANNEL")

CATEGORIES=[
"Food","Transport","Shopping","Housing",
"Utilities","Tax","Parking","Entertainment",
"Drinks","Transfer","Other"
]

intents=discord.Intents.default()
intents.message_content=True

bot=discord.Client(intents=intents)


def save_transaction(msg,source,text):

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    c=conn.cursor()

    try:
        c.execute("""
        INSERT INTO transactions(date,source,raw,discord_msg_id)
        VALUES(datetime('now'),?,?,?)
        """,(source,text,msg.id))
        conn.commit()
        return True
    except:
        return False


@bot.event
async def on_message(msg):

    if msg.author.bot:
        return

    channel=str(msg.channel.id)

    source=None

    if channel==GX:
        source="gxbank"

    if channel==CIMB:
        source="cimb"

    if channel==TNG:
        source="tng"

    if source:

        inserted=save_transaction(msg,source,msg.content)

        if not inserted:
            return

        amount,merchant,tx_type=parse_message(msg.content)

        if not amount:
            return

        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        c=conn.cursor()

        c.execute("""
        UPDATE transactions
        SET amount=?,merchant=?,type=?
        WHERE discord_msg_id=?
        """,(amount,merchant,tx_type,msg.id))

        conn.commit()

        if tx_type=="transfer":

            await msg.add_reaction("🔁")

            ch=bot.get_channel(int(GENERAL))

            prompt=await ch.send(
            f"""
Transfer detected

Merchant: {merchant}
Amount: RM{amount}

Reply category:
food / family / personal / ignore
"""
            )

            c.execute("""
            INSERT INTO pending(transaction_id,discord_prompt_id)
            VALUES((SELECT id FROM transactions WHERE discord_msg_id=?),?)
            """,(msg.id,prompt.id))

            conn.commit()

        else:

            await msg.add_reaction("✅")

        conn.close()

    if msg.reference:

        reply=msg.reference.message_id

        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        c=conn.cursor()

        c.execute("""
        SELECT transaction_id
        FROM pending
        WHERE discord_prompt_id=?
        """,(reply,))

        row=c.fetchone()

        if row:

            tx=row[0]

            category=msg.content.strip()

            c.execute("""
            UPDATE transactions
            SET category=?,processed=1
            WHERE id=?
            """,(category,tx))

            c.execute("DELETE FROM pending WHERE transaction_id=?",(tx,))
            conn.commit()

            await msg.add_reaction("✅")

        conn.close()

    if msg.content=="/report":

        path=monthly_report()

        await msg.channel.send(file=discord.File(path))


bot.run(TOKEN)
