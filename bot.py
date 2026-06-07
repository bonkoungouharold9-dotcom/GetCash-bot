import os
import sqlite3
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TOKEN")  # Sur Koyeb, on mettra la variable
CANAL_ID = "@Getcash209"
PRIX_PAR_FILLEUL = 500

conn = sqlite3.connect("getcash.db", check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS users (tg_id INTEGER PRIMARY KEY, custom_id TEXT UNIQUE, parrain_id INTEGER, solde INTEGER DEFAULT 0, date_inscription TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
c.execute("""CREATE TABLE IF NOT EXISTS validations (tg_id INTEGER PRIMARY KEY, a_rejoint_canal BOOLEAN DEFAULT 0)""")
conn.commit()

def generer_id_personnalise():
    while True:
        new_id = "1012" + "".join(str(random.randint(0,9)) for _ in range(6))
        c.execute("SELECT custom_id FROM users WHERE custom_id = ?", (new_id,))
        if not c.fetchone():
            return new_id

def ajouter_utilisateur(tg_id, parrain_id=None):
    c.execute("SELECT tg_id FROM users WHERE tg_id = ?", (tg_id,))
    if c.fetchone():
        return False
    custom_id = generer_id_personnalise()
    c.execute("INSERT INTO users (tg_id, custom_id, parrain_id) VALUES (?, ?, ?)", (tg_id, custom_id, parrain_id))
    c.execute("INSERT INTO validations (tg_id, a_rejoint_canal) VALUES (?, 0)", (tg_id,))
    conn.commit()
    return True

async def verifier_canal(context, user_id):
    try:
        membre = await context.bot.get_chat_member(CANAL_ID, user_id)
        return membre.status in ["member", "administrator", "creator"]
    except:
        return False

async def valider_filleul(context, tg_id):
    c.execute("SELECT a_rejoint_canal FROM validations WHERE tg_id = ?", (tg_id,))
    row = c.fetchone()
    if not row or row[0] == 1:
        return False
    c.execute("UPDATE validations SET a_rejoint_canal = 1 WHERE tg_id = ?", (tg_id,))
    c.execute("SELECT parrain_id FROM users WHERE tg_id = ?", (tg_id,))
    parrain = c.fetchone()
    if parrain and parrain[0]:
        c.execute("UPDATE users SET solde = solde + ? WHERE tg_id = ?", (PRIX_PAR_FILLEUL, parrain[0]))
        conn.commit()
        await context.bot.send_message(parrain[0], f"🎉 Nouveau filleul validé ! +{PRIX_PAR_FILLEUL} FCFA")
        return True
    conn.commit()
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    parrain_id = int(args[0]) if args and args[0].isdigit() else None
    nouveau = ajouter_utilisateur(user_id, parrain_id)
    if not nouveau:
        await update.message.reply_text("✅ Déjà inscrit. Utilise /mon_id, /solde, /mes_filleuls")
        return
    a_rejoint = await verifier_canal(context, user_id)
    if a_rejoint:
        await valider_filleul(context, user_id)
        msg = "🎉 Merci d'avoir rejoint le canal ! Ton parrain a reçu 500 FCFA."
    else:
        msg = f"⚠️ Rejoins {CANAL_ID} puis /check"
    c.execute("SELECT custom_id FROM users WHERE tg_id = ?", (user_id,))
    custom = c.fetchone()[0]
    msg += f"\n🆔 ID: `{custom}`\n🔗 Lien: https://t.me/{(await context.bot.get_me()).username}?start={user_id}"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await verifier_canal(context, user_id):
        await update.message.reply_text(f"❌ Rejoins {CANAL_ID} puis /check")
        return
    if await valider_filleul(context, user_id):
        await update.message.reply_text("✅ Validé ! +500 FCFA pour ton parrain.")
    else:
        await update.message.reply_text("Déjà validé ou pas de parrain.")

async def mon_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    c.execute("SELECT custom_id FROM users WHERE tg_id = ?", (user_id,))
    row = c.fetchone()
    if row:
        await update.message.reply_text(f"🆔 ID: `{row[0]}`\nLien: https://t.me/{(await context.bot.get_me()).username}?start={user_id}", parse_mode="Markdown")
    else:
        await update.message.reply_text("Utilise /start d'abord")

async def solde(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    c.execute("SELECT solde FROM users WHERE tg_id = ?", (user_id,))
    row = c.fetchone()
    await update.message.reply_text(f"💰 Solde: {row[0]} FCFA" if row else "Inscris-toi avec /start")

async def mes_filleuls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    c.execute("SELECT COUNT(*) FROM users WHERE parrain_id = ?", (user_id,))
    nb = c.fetchone()[0]
    await update.message.reply_text(f"👥 {nb} filleul(s) validé(s)")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start, /check, /mon_id, /solde, /mes_filleuls\nSupport: @tik_cashMentor")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("mon_id", mon_id))
    app.add_handler(CommandHandler("solde", solde))
    app.add_handler(CommandHandler("mes_filleuls", mes_filleuls))
    app.add_handler(CommandHandler("help", help_command))
    print("Bot GetCash en ligne")
    app.run_polling()

if __name__ == "__main__":
    main()
