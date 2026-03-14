import discord
import os
from dotenv import load_dotenv
from parser import parse_message
from reports import monthly_report
import psycopg2
from discord.ui import View, Button

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

MERCHANT_CHOICES=[
"Transfer",
"Petrol",
"Top Up",
"TNG Reload",
"Cashback",
"Other"
]

intents=discord.Intents.default()
intents.message_content=True

bot=discord.Client(intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    
class CategoryView(discord.ui.View):
    def __init__(self, tx_id):
        super().__init__(timeout=None)

        self.tx_id = tx_id

        for category in CATEGORIES:

            button = discord.ui.Button(
                label=category,
                style=discord.ButtonStyle.primary
            )

            button.callback = self.make_callback(category)

            self.add_item(button)

    def make_callback(self, category):

        async def callback(interaction: discord.Interaction):

            conn = psycopg2.connect(os.getenv("DATABASE_URL"))
            c = conn.cursor()

            c.execute("""
            UPDATE transactions
            SET category=%s, processed=TRUE
            WHERE id=%s
            """, (category, self.tx_id))

            c.execute(
                "DELETE FROM pending WHERE transaction_id=%s",
                (self.tx_id,)
            )

            conn.commit()
            conn.close()

            await interaction.response.send_message(
                f"Saved category: {category}",
                ephemeral=True
            )

        return callback
        
def save_transaction(msg,source,text):

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    c=conn.cursor()

    try:
        c.execute("""
        INSERT INTO transactions(date,source,raw,discord_msg_id)
        VALUES(NOW(),%s,%s,%s)
        """,(source,text,msg.id))
        conn.commit()
        return True
    except:
        return False
        
class MerchantView(discord.ui.View):

    def __init__(self, tx_id, amount):
        super().__init__(timeout=None)

        self.tx_id = tx_id
        self.amount = amount

        for merchant in MERCHANT_CHOICES:

            button = discord.ui.Button(
                label=merchant,
                style=discord.ButtonStyle.secondary
            )

            button.callback = self.make_callback(merchant)

            self.add_item(button)

    def make_callback(self, merchant):

        async def callback(interaction: discord.Interaction):

            conn = psycopg2.connect(os.getenv("DATABASE_URL"))
            c = conn.cursor()

            c.execute("""
            UPDATE transactions
            SET merchant=%s
            WHERE id=%s
            """,(merchant,self.tx_id))

            conn.commit()
            conn.close()

            await interaction.response.send_message(
                f"Merchant set: {merchant}",
                ephemeral=True
            )

        return callback
        
async def check_unprocessed():

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    c = conn.cursor()

    c.execute("""
    SELECT id, amount, merchant, type
    FROM transactions
    WHERE processed IS NOT TRUE
    """)

    rows = c.fetchall()

    conn.close()

    return rows

async def scan_channels_for_missing():

    channels = [GX, CIMB, TNG]

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    c = conn.cursor()

    added = 0

    for ch_id in channels:

        channel = bot.get_channel(int(ch_id))

        async for msg in channel.history(limit=100):

            if msg.author.id == bot.user.id:
                continue

            # check if message already saved
            c.execute("""
            SELECT 1 FROM transactions
            WHERE discord_msg_id=%s
            """,(msg.id,))

            if c.fetchone():
                continue

            # detect source
            source=None
            if str(msg.channel.id)==GX:
                source="gxbank"
            if str(msg.channel.id)==CIMB:
                source="cimb"
            if str(msg.channel.id)==TNG:
                source="tng"

            if not source:
                continue

            amount,merchant,tx_type=parse_message(msg.content)

            if not amount:
                continue

            c.execute("""
            INSERT INTO transactions(date,source,raw,discord_msg_id,amount,merchant,type)
            VALUES(NOW(),%s,%s,%s,%s,%s,%s)
            """,(source,msg.content,msg.id,amount,merchant,tx_type))

            added+=1

    conn.commit()
    conn.close()

    return added
    
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
        SELECT id FROM transactions WHERE discord_msg_id=%s
        """,(msg.id,))
        
        row = c.fetchone()
        
        if not row:
            conn.close()
            return
        
        tx = row[0]
        
        # save amount + type first
        c.execute("""
        UPDATE transactions
        SET amount=%s,type=%s
        WHERE id=%s
        """,(amount,tx_type,tx))
        
        conn.commit()
        
        # now handle missing merchant
        if not merchant:
        
            ch=bot.get_channel(int(GENERAL))
        
            view = MerchantView(tx, amount)
        
            await ch.send(
                f"Merchant not detected\n\nAmount: RM{amount}\n\nSelect merchant:",
                view=view
            )
        
            conn.close()
            return
            
        c=conn.cursor()

        c.execute("""
        UPDATE transactions
        SET amount=%s,merchant=%s,type=%s
        WHERE discord_msg_id=%s
        """,(amount,merchant,tx_type,msg.id))

        conn.commit()

        if tx_type=="transfer":

            await msg.add_reaction("🔁")

            ch=bot.get_channel(int(GENERAL))

            c.execute("""
            SELECT id FROM transactions WHERE discord_msg_id=%s
            """,(msg.id,))
            tx = c.fetchone()[0]
            
            view = CategoryView(tx)
            
            prompt = await ch.send(
            f"""
            Transfer detected
            
            Merchant: {merchant}
            Amount: RM{amount}
            
            Choose category:
            """,
            view=view
            )

            c.execute("""
            INSERT INTO pending(transaction_id,discord_prompt_id)
            VALUES((SELECT id FROM transactions WHERE discord_msg_id=%s),%s)
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
        WHERE discord_prompt_id=%s
        """,(reply,))

        row=c.fetchone()

        if row:

            tx=row[0]

            category=msg.content.strip()

            c.execute("""
            UPDATE transactions
            SET category=%s,processed=TRUE
            WHERE id=%s
            """,(category,tx))

            c.execute("DELETE FROM pending WHERE transaction_id=%s",(tx,))
            conn.commit()

            await msg.add_reaction("✅")

        conn.close()

    if msg.content=="/report":

        path=monthly_report()

        await msg.channel.send(file=discord.File(path))

    if msg.content == "/check":

        await msg.channel.send("Scanning channels for missing transactions...")
    
        added = await scan_channels_for_missing()
    
        rows = await check_unprocessed()
    
        ch = bot.get_channel(int(GENERAL))
    
        reopened = 0
    
        for tx_id, amount, merchant, tx_type in rows:
    
            if not merchant:
    
                view = MerchantView(tx_id, amount)
    
                await ch.send(
                    f"""
    Unprocessed transaction
    
    Amount: RM{amount}
    
    Merchant missing — choose one:
    """,
                    view=view
                )
    
                reopened+=1
    
            else:
    
                view = CategoryView(tx_id)
    
                await ch.send(
                    f"""
    Unprocessed transaction
    
    Merchant: {merchant}
    Amount: RM{amount}
    
    Choose category:
    """,
                    view=view
                )
    
                reopened+=1
    
        await msg.channel.send(
            f"Scan complete\n"
            f"Transactions added: {added}\n"
            f"Unprocessed reopened: {reopened}"
        )
        
    if msg.content.startswith("/ai"):
    
        cmd = msg.content.replace("/ai","").strip()
    
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        c = conn.cursor()
    
        c.execute("""
        INSERT INTO ai_commands(command)
        VALUES(%s)
        """,(cmd,))
    
        conn.commit()
        conn.close()
    
        await msg.channel.send("AI task queued.")

bot.run(TOKEN)
