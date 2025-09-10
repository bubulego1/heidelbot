# -*- coding: utf-8 -*-
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import json
import re
import logging
import os

# Configuration du logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Charge ton JSON avec les questions/réponses
with open("questions.json", "r", encoding="utf-8") as f:
    questions_data = json.load(f)

# Commande /get <num>
async def get_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if context.args:
        num = context.args[0]
        if num in questions_data:
            formatted_response = format_question(num, questions_data[num])
            await update.message.reply_text(formatted_response, parse_mode='HTML')
        else:
            await update.message.reply_text("Question non trouvée.")
    else:
        await update.message.reply_text("Veuillez fournir un numéro de question.")

# Commande /recherche <mot>
async def search_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not context.args:
        await update.message.reply_text("Veuillez fournir un mot à rechercher. Ex: /recherche salut")
        return

    query = " ".join(context.args).lower()
    results = []
    for num, content in questions_data.items():
        if query in content.lower():
            results.append(format_question(num, content))
    
    if results:
        # Telegram a une limite de 4096 caractères par message, on coupe si nécessaire
        chunk_size = 4000
        message = ""
        for res in results:
            if len(message) + len(res) + 2 > chunk_size:
                await update.message.reply_text(message, parse_mode='HTML')
                message = res + "\n\n"
            else:
                message += res + "\n\n"
        if message:
            await update.message.reply_text(message, parse_mode='HTML')
    else:
        await update.message.reply_text(f"Aucune question trouvée contenant '{query}'.")

# Commande /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
        "Bonjour !\n- Demande une question avec /get <num>\n- Recherche avec /recherche <mot>\n- Ou mentionne-moi dans un groupe avec @heidelbot <num>."
    )

# Fonction pour corriger la ponctuation française
def fix_french_punctuation(text):
    text = re.sub(r'\s*([?:;!])\s*', r' \1 ', text)
    text = re.sub(r'\s*([,.])\s*', r'\1 ', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'^\s+|\s+$', '', text)
    text = re.sub(r'\s*"\s*', ' " ', text)
    return text

# Fonction pour formater une question
def format_question(num, content):
    if '\n\n' in content:
        parts = content.split('\n\n', 1)
        question = fix_french_punctuation(parts[0].strip())
        answer = fix_french_punctuation(parts[1].strip())
        return f"<b>{num}. {question}</b>\n\n{answer}"
    else:
        fixed_content = fix_french_punctuation(content.strip())
        return f"<b>{num}.</b> {fixed_content}"

# Gestion des mentions et messages
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    chat_type = update.message.chat.type
    text = update.message.text
    user = update.message.from_user
    
    bot_mentioned = "@heidelbot" in text.lower()
    is_private = chat_type == "private"
    
    if is_private or bot_mentioned:
        patterns = [
            r"@heidelbot\s+(\d+)",
            r"heidelbot\s+(\d+)",
            r"@heidelbot\s*(\d+)",
            r"(\d+)"
        ]
        num = None
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                num = match.group(1)
                break
        
        if num and num in questions_data:
            formatted_response = format_question(num, questions_data[num])
            try:
                await update.message.reply_text(formatted_response, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Erreur envoi message: {e}")
        elif num:
            await update.message.reply_text(f"Question {num} non trouvée (questions 1-129 disponibles)")
        elif bot_mentioned:
            await update.message.reply_text("Utilise: @heidelbot <numéro> pour avoir une question (ex: @heidelbot 1)")

# Gestionnaire d'erreurs
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

# Fonction principale
def main():
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
    PORT = int(os.environ.get("PORT", 8443))
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Ajout des handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("get", get_question))
    app.add_handler(CommandHandler("recherche", search_question))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_error_handler(error_handler)
    
    # Lancement du webhook
   import os
port = int(os.environ.get("PORT", 10000))

app.run_webhook(
    listen="0.0.0.0",
    port=port,
    webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
    )

if __name__ == "__main__":
    main()
