# -*- coding: utf-8 -*-
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import json
import re
import logging
import asyncio
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
    if context.args:  # Vérifie qu'un numéro a été passé
        num = context.args[0]
        if num in questions_data:
            formatted_response = format_question(num, questions_data[num])
            await update.message.reply_text(formatted_response, parse_mode='HTML')
        else:
            await update.message.reply_text("Question non trouvée.")
    else:
        response = "Veuillez fournir un numéro de question."
        await update.message.reply_text(response)

# Commande /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
        "Bonjour ! Demande-moi une question avec /get <num> ou mentionne-moi dans un groupe avec @heidelbot <num>."
    )

# Fonction pour corriger la ponctuation française
def fix_french_punctuation(text):
    """Corrige la ponctuation selon les règles typographiques françaises"""
    import re
    
    # Pour les signes : ; ? ! (doivent avoir un espace avant ET après)
    # Enlève les espaces existants puis ajoute l'espacement correct
    text = re.sub(r'\s*([?:;!])\s*', r' \1 ', text)
    
    # Pour les virgules et points (espace seulement après, pas avant)
    # Enlève les espaces avant, assure l'espace après
    text = re.sub(r'\s*([,.])\s*', r'\1 ', text)
    
    # Corrections spéciales pour éviter les espaces en double
    text = re.sub(r'\s+', ' ', text)  # Réduit les espaces multiples
    text = re.sub(r'^\s+|\s+$', '', text)  # Supprime espaces début/fin
    
    # Correction pour les guillemets français (si présents)
    text = re.sub(r'\s*"\s*', ' " ', text)
    
    return text

# Fonction pour formater une question avec numéro et mise en forme
def format_question(num, content):
    """Formate une question avec son numéro, question en gras et réponse normale"""
    if '\n\n' in content:
        parts = content.split('\n\n', 1)
        question = fix_french_punctuation(parts[0].strip())
        answer = fix_french_punctuation(parts[1].strip())
        return f"<b>{num}. {question}</b>\n\n{answer}"
    else:
        # Fallback si le format n'est pas celui attendu
        fixed_content = fix_french_punctuation(content.strip())
        return f"<b>{num}.</b> {fixed_content}"

# Gestion des mentions et messages
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    # Log détaillé pour diagnostic
    chat_type = update.message.chat.type
    text = update.message.text
    user = update.message.from_user
    chat_id = update.message.chat.id
    
    print(f"[DEBUG] Message de {user.first_name} dans {chat_type} (ID: {chat_id}): '{text}'")
    logger.info(f"Message de {user.first_name} dans {chat_type}: {text}")
    
    # Vérifier si le bot est mentionné
    bot_mentioned = "@heidelbot" in text.lower()
    is_private = chat_type == "private"
    
    print(f"[DEBUG] Bot mentionné: {bot_mentioned}, Chat privé: {is_private}")
    
    # Si c'est un message privé ou le bot est mentionné
    if is_private or bot_mentioned:
        print("[DEBUG] Traitement du message...")
        
        # Recherche du numéro - patterns multiples
        patterns = [
            r"@heidelbot\s+(\d+)",      # @heidelbot 1
            r"heidelbot\s+(\d+)",       # heidelbot 1  
            r"@heidelbot\s*(\d+)",      # @heidelbot1
            r"(\d+)"                    # Juste un numéro
        ]
        
        num = None
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                num = match.group(1)
                print(f"[DEBUG] Numéro trouvé avec pattern '{pattern}': {num}")
                break
        
        if num and num in questions_data:
            print(f"[DEBUG] Envoi de la question {num}")
            formatted_response = format_question(num, questions_data[num])
            try:
                await update.message.reply_text(formatted_response, parse_mode='HTML')
                print(f"[DEBUG] Question {num} envoyée avec succès")
                logger.info(f"Question {num} envoyée avec succès")
            except Exception as e:
                print(f"[DEBUG] Erreur envoi: {e}")
                logger.error(f"Erreur envoi message: {e}")
        elif num:
            await update.message.reply_text(f"Question {num} non trouvée (questions 1-129 disponibles)")
        elif bot_mentioned:
            await update.message.reply_text("Utilise: @heidelbot <numéro> pour avoir une question (ex: @heidelbot 1)")
        else:
            print("[DEBUG] Aucun numéro trouvé dans le message")

# Gestionnaire d'erreurs
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

# Fonction pour maintenir l'activité
async def keep_alive():
    """Fonction pour maintenir l'activité du bot"""
    while True:
        await asyncio.sleep(600)  # Attendre 10 minutes
        logger.info("Bot still alive")

def main():
    """Fonction principale avec gestion des erreurs et reconnexion automatique"""
    # Initialise l'application avec ton token
    app = ApplicationBuilder().token("7595543004:AAGb4V3Q7e4Uc6_WzLzdpnw8yBQICnJjIXA").build()

    # Ajout des handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("get", get_question))
    # Handler pour tous les messages texte (avec filtre dans la fonction)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Ajout du gestionnaire d'erreurs
    app.add_error_handler(error_handler)

    logger.info("Bot démarré avec succès!")
    
    # Note: keep_alive sera géré automatiquement par le polling
    
    # Démarre le bot avec gestion des erreurs
    try:
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False
        )
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du bot: {e}")
        # Redémarrage automatique après 5 secondes
        import time
        time.sleep(5)
        main()

if __name__ == '__main__':
    while True:
        try:
            main()
        except Exception as e:
            logger.error(f"Erreur critique: {e}")
            logger.info("Redémarrage du bot dans 10 secondes...")
            import time
            time.sleep(10)