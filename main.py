import os
import logging
import tempfile
import requests
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# .env файлни ўқиш
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("VOICE_ID")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN topilmadi. .env faylni tekshiring.")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY topilmadi. .env faylni tekshiring.")
if not ELEVENLABS_API_KEY or not VOICE_ID:
    raise ValueError("ELEVENLABS_API_KEY ёки VOICE_ID топилмади. .env файлини текширинг.")

# Логларни созлаш
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

client = OpenAI(api_key=OPENAI_API_KEY)

# ==========================================
# МУКАММАЛ НАЗОРАТЧИ ПРОМПТИ (CONTROLLER)
# ==========================================
SYSTEM_PROMPT = """
Сен дунё даражасидаги юқори малакали операцион директор (COO), компания "прокурори" ва бош назоратчи менежерсан.

Сен компаниядаги энг муҳим роллардан бирисан. Сен шунчаки воситачи эмассан, сен — компаниянинг ижро машинаси, қонун-қоидалар ҳимоячиси ва таъсисчининг (раҳбарнинг) ишончли вакилисан.

━━━━━━━━━━━━━━━━━━━━━━━
🏢 СЕНИНГ ВАЗИФА ВА ВАКОЛАТЛАРИНГ
━━━━━━━━━━━━━━━━━━━━━━━

1. КОММУНИКАЦИЯ ВА ИЕРАРХИЯ:
- Раҳбар ва жамоа ўртасидаги ягона кўприксан. Раҳбар ходимлар билан тўғридан-тўғри ишламайди, барчаси сен орқали ўтади.
- Мутахассисларнинг ишини режалаштирасан, мувофиқлаштирасан ва қаттиқ назорат қиласан.

2. ВАЗИФАЛАРНИ БОШҚАРИШ:
- Раҳбардан келган топшириқни чуқур таҳлил қил, мақсадини англа ва уни қадамларга бўл.
- Вазифани айнан керакли мутахассисга (Маркетолог, Молиячи, Юрист ва ҳ.к.) йўналтир.
- Ҳар бир вазифа учун қатъий дедлайн белгила ва унинг бажарилишини кузатиб бор.

3. СИФАТ ВА ИНТИЗОМ НАЗОРАТИ:
- Сен "яхши" ёки "тайёр" деган сўзларга текширмасдан ишонмайсан.
- Мутахассис тайёрлаган жавобни Раҳбарга кўрсатишдан олдин қаттиқ сифат фильтридан ўтказ. 
- Агар жавоб юзаки, нотўғри ёки компания манфаатига зид бўлса, Раҳбар кўришидан аввал мутахассисга қайтар ва қайта ишлаттир.
- Низоли ёки мавҳум вазиятларда тезда оқилона қарор қабул қил ва муаммони ҳал эт.

━━━━━━━━━━━━━━━━━━━━━━━
🧠 СЕНИНГ ХАРАКТЕРИНГ ВА ФИКРЛАШИНГ
━━━━━━━━━━━━━━━━━━━━━━━

- Қаттиққўл, лекин адолатли ва ростгўй.
- Рақамларга ва фактларга асосланган (Ҳисоб-китоб ва аналитикани яхши тушунасан).
- Деталларга ўта эътиборли. Вазифанинг бирор қисми эсдан чиқишига йўл қўймайсан.
- Эмоцияга берилмайсан, фақат компания манфаати ва натижа учун ишлайсан.
- Сен салбий вазиятларни ҳам компания манфаати томонга ўзгартира оладиган дипломат ва стратегсан.

━━━━━━━━━━━━━━━━━━━━━━━
📤 ЖАВОБ ФОРМАТИ ВА ҚОИДАЛАР
━━━━━━━━━━━━━━━━━━━━━━━

1. Жавоблар аниқ, лўнда ва структурали бўлсин. Кераксиз назария ёзма.
2. Қабул қилинган вазифани кимга йўналтирганинг ва қачонга (дедлайн) сўраганингни аниқ айт.
3. Мутахассисдан келган ишни текшираётганда: хатони очиқ кўрсат, эътироз билдир ва тўғирлашни талаб қил.
4. Жавоблар фақат ўзбек тилида (кирилл алифбосида) бўлсин. Лотин алифбосидан фойдаланма.

Сен оддий кузатувчи эмассан. Сен вазифа 100% тўлиқ ва мукаммал бажарилмагунча тўхтамайдиган НАЗОРАТЧИСАН.
"""

# ==========================================
# ФУНКЦИЯЛАР
# ==========================================

def wants_text_reply(user_message: str) -> bool:
    text = user_message.lower()
    triggers = [
        "матнда жавоб бер", "матнли жавоб бер", "матнда ёз", 
        "матнда ёзиб бер", "ёзма жавоб бер", "текст қилиб бер", 
        "text qilib ber", "matnda javob ber", "matnli javob ber", "yozma javob ber"
    ]
    return any(trigger in text for trigger in triggers)

def speech_to_text(audio_file_path: str) -> str:
    with open(audio_file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file,
        )
    return (transcription.text or "").strip()

def generate_ai_reply(user_message: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    
    reply = response.choices[0].message.content.strip() if response.choices else ""
    if not reply:
        reply = "Жавоб тайёр бўлмади. Илтимос, саволни қайта юборинг."
    return reply

async def send_voice_reply(update: Update, text: str):
    temp_audio_path = None
    try:
        # ElevenLabs лимитини тежаш учун матн узунлигини чеклаймиз
        safe_text = text[:1500] if text else "Жавоб тайёр бўлмади."

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            temp_audio_path = temp_audio.name

        # ==========================================
        # ELEVENLABS API ОРҚАЛИ ОВОЗ ГЕНЕРАЦИЯСИ
        # ==========================================
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        
        data = {
            "text": safe_text,
            "model_id": "eleven_multilingual_v2", 
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            with open(temp_audio_path, 'wb') as f:
                f.write(response.content)
        else:
            raise Exception(f"ElevenLabs API хатолиги: {response.text}")

        # Тайёр аудио файлни Телеграмга юбориш
        with open(temp_audio_path, "rb") as audio_file:
            await update.message.reply_voice(voice=audio_file)

    except Exception as e:
        logging.exception("Ovozli javob yuborishda xatolik")
        await update.message.reply_text(f"Хатолик юз берди: {str(e)}")
    finally:
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "Ассалому алайкум! Мен компаниянинг Бош Назоратчисиман.\n\n"
        "Барча вазифалар ва топшириқларни мен орқали беришингиз мумкин. Мен уларни тегишли мутахассисларга тақсимлайман ва бажарилишини қатъий назорат қиламан.\n\n"
        "Мен одатда фақат овозли жавоб бераман.\n"
        "Агар матнли жавоб керак бўлса, хабарингизда: \"матнда жавоб бер\" деб ёзинг."
    )
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Фойдаланиш қоидалари:\n\n"
        "1. Менга топшириқ ёки вазифани овозли ёки матн кўринишида юборинг.\n"
        "2. Мен уни таҳлил қилиб, қайси мутахассисга йўналтириш ва қандай дедлайн қўйишни белгилайман.\n"
        "3. Мен одатда овозли жавоб қайтараман.\n"
        "4. Агар матнли жавоб керак бўлса, \"матнда жавоб бер\" деб қўшиб ёзинг.\n\n"
        "Мисол:\n"
        "Матнда жавоб бер. Янги филиал очиш бўйича маркетинг ва молия бўлимига вазифа бер. Смета ва реклама режасини эртагача тайёрлашсин."
    )
    await update.message.reply_text(help_text)

async def respond_based_on_mode(update: Update, user_message: str):
    reply = generate_ai_reply(user_message)

    if wants_text_reply(user_message):
        await update.message.reply_text(reply)
    else:
        await send_voice_reply(update, reply)

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_message = update.message.text.strip()

    try:
        await respond_based_on_mode(update, user_message)
    except Exception as e:
        logging.exception("Matnli xabarda xatolik")
        await update.message.reply_text(f"Хатолик юз берди: {str(e)}")

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.voice:
        return

    temp_ogg_path = None

    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
            temp_ogg_path = temp_audio.name

        await voice_file.download_to_drive(temp_ogg_path)

        user_text = speech_to_text(temp_ogg_path)

        if not user_text:
            await update.message.reply_text("Овозли хабар тушунилмади. Илтимос, қайта юборинг.")
            return

        await respond_based_on_mode(update, user_text)

    except Exception as e:
        logging.exception("Ovozli xabarda xatolik")
        await update.message.reply_text(f"Хатолик юз берди: {str(e)}")
    finally:
        if temp_ogg_path and os.path.exists(temp_ogg_path):
            os.remove(temp_ogg_path)

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    print("Controller (Назоратчи) bot ишга тушди...")
    app.run_polling()

if __name__ == "__main__":
    main()