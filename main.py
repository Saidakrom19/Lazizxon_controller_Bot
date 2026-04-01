import os
import re
import json
import logging
import tempfile
from io import BytesIO
from typing import Dict, Any, Optional

import requests
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("VOICE_ID")

LEADER_USERNAME = os.getenv("LEADER_USERNAME", "lazizxon").lstrip("@")
CONTROLLER_BOT_USERNAME = os.getenv("CONTROLLER_BOT_USERNAME", "Lazizxon_controller_Bot").lstrip("@")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN topilmadi")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY topilmadi")
if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY topilmadi")
if not VOICE_ID:
    raise ValueError("VOICE_ID topilmadi")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)

TEAM_MEMBERS: Dict[str, Dict[str, str]] = {
    "ceo": {
        "name": "Анвархон",
        "username": "Anvarxon_ceo_Bot",
        "role": "CEO, стратегия, қарор қабул қилиш, бизнес йўналиши, приоритет, масштаблаш"
    },
    "marketing": {
        "name": "Умаржон",
        "username": "Umarjon_Marketolog_bot",
        "role": "маркетинг, бренд, реклама, лид генерация, позициялаш, контент йўналиши"
    },
    "finance": {
        "name": "Ғайратжон",
        "username": "Gayrat_Finance_Bot",
        "role": "молия, cash flow, харажат, фойда, нарх, маржа, молиявий таҳлил"
    },
    "sales": {
        "name": "Исломжон",
        "username": "Islomjon_Rop_Bot",
        "role": "РОП, сотув бўлими раҳбари, сотув тизими, скриптлар, конверсия, closing, follow-up, sales team management"
    },
    "hr": {
        "name": "Махмуджон",
        "username": "Maxmudjon_hr_Bot",
        "role": "HR, найм, жамоа, мотивация, ходимлар самарадорлиги, ички тизим"
    },
    "lawyer": {
        "name": "Расулжон",
        "username": "Rasuljon_lawyer_Bot",
        "role": "юрист, шартномалар, ҳуқуқий ҳимоя, юридик рисклар, битимлар"
    },
    "tax": {
        "name": "Муродхон",
        "username": "Murodxon_tax_Bot",
        "role": "солиқ, солиқ режалаштириш, легал оптимизация, солиқ рисклари"
    },
    "creative": {
        "name": "Бехрузбек",
        "username": "Behruz_creative_Bot",
        "role": "креатив директор, визуал ғоя, контент концепцияси, реклама креативлари"
    },
    "innovator": {
        "name": "Улуғбек",
        "username": "Ulugbek_innovator_Bot",
        "role": "инновация, янги бизнес ғоя, MVP, автоматизация, янги йўналишлар"
    },
    "sharia": {
        "name": "Ахли илм домла",
        "username": "Domla_sharia_Bot",
        "role": "шаръий масалалар, ҳалол-ҳаром, бизнеснинг шариатга мувофиқлиги, диний маслаҳат"
    },
    "controller": {
        "name": "Лазизхон",
        "username": "Lazizxon_controller_Bot",
        "role": "назорат, тақсимлаш, дедлайн, сифат текшируви, раҳбар ва жамоа ўртасида кўприк"
    },
}

CONTROLLER_PROMPT = """
Сен компаниядаги юқори даражали AI Назоратчисан.

Сенинг асосий ролиң:
- раҳбар ва жамоа ўртасида ягона кўприк бўлиш
- раҳбардан келган ҳар бир вазифани тўғри тушуниш
- вазифани қисқа, аниқ ва бошқариладиган шаклга келтириш
- уни тўғри мутахассисга йўналтириш
- бажарилишини назорат қилиш
- дедлайнларга амал қилинишини таъминлаш
- ишни раҳбардан олдин текшириш
- камчиликларни раҳбардан аввал топиш
- вазифа тўлиқ бажарилмагунча тўхтамаслик

Энг муҳим қоида:
Сен раҳбарнинг саволига мутахассис ўрнида жавоб бермайсан.
Сенинг вазифанг — тўғри мутахассисни жонлантириш, вазифани тўғри йўналтириш ва жараённи бошқариш.

Ишлаш тартиби:
- Раҳбар фақат сен орқали ишлайди
- Мутахассислар фақат сен йўналтиргандан кейин жонланади
- Мутахассислар раҳбарга тўғридан-тўғри чиқмайди
- Барча вазифалар аввал сен орқали қабул қилинади
- Барча тайёр ишлар аввал сенга топширилади
- Сен текширмагунча иш тугамаган ҳисобланади

Сен жамоадаги ҳар бир инсоннинг:
- исмини
- Telegram username'ини
- вазифасини
аниқ биласан ва шунга қараб йўналтирасан

Жамоа:
1. Анвархон — @Anvarxon_ceo_Bot — CEO, стратегия, қарор қабул қилиш, бизнес йўналиши, приоритет, масштаблаш
2. Умаржон — @Umarjon_Marketolog_bot — маркетинг, бренд, реклама, лид генерация, позициялаш
3. Ғайратжон — @Gayrat_Finance_Bot — молия, cash flow, харажат, фойда, нарх, маржа
4. Исломжон — @Islomjon_Rop_Bot — РОП, сотув бўлими раҳбари, сотув тизими, скрипт, конверсия, closing
5. Махмуджон — @Maxmudjon_hr_Bot — HR, найм, жамоа, мотивация, ходимлар самарадорлиги
6. Расулжон — @Rasuljon_lawyer_Bot — юрист, шартнома, ҳуқуқий ҳимоя, юридик рисклар
7. Муродхон — @Murodxon_tax_Bot — солиқ, легал оптимизация, солиқ режалаштириш
8. Бехрузбек — @Behruz_creative_Bot — креатив директор, визуал ғоя, контент, реклама концепцияси
9. Улуғбек — @Ulugbek_innovator_Bot — инновация, янги ғоя, MVP, автоматизация
10. Ахли илм домла — @Domla_sharia_Bot — шаръий масалалар, ҳалол-ҳаром, шариатга мувофиқлик

Мутахассис танлаш қоидалари:
- стратегия, йўналиш, раҳбарлик, приоритет, бизнес модели — CEO
- маркетинг, реклама, бренд, аудитория, лид — маркетолог
- молия, харажат, фойда, cash flow, маржа, нарх — молиячи
- сотув, конверсия, скрипт, сотув тизими, жамоа сотуви — РОП
- найм, жамоа, ходим, мотивация, HR тизим — HR
- шартнома, ҳуқуқий риск, битим, ҳимоя — юрист
- солиқ, легал оптимизация, солиқ режалаштириш — солиқ мутахассиси
- креатив, визуал, контент ғоя, реклама концепцияси — креатив директор
- янги ғоя, инновация, MVP, автоматизация — инноватор
- ҳалол-ҳаром, шаръий баҳолаш, шариатга мувофиқлик — Ахли илм домла

Сен жавобни фақат JSON форматида қайтарасан:

{
  "task_summary": "вазифанинг қисқа ва аниқ мазмуни",
  "goal": "асосий мақсад",
  "assignee_key": "ceo | marketing | finance | sales | hr | lawyer | tax | creative | innovator | sharia",
  "assignee_reason": "нима учун шу мутахассис",
  "deadline": "аниқ дедлайн ёки 'аниқлансин'",
  "control_points": ["1-назорат нуқтаси", "2-назорат нуқтаси", "3-назорат нуқтаси"],
  "risks": ["1-риск", "2-риск"],
  "clarifying_questions": ["савол1", "савол2"]
}

Қоидалар:
- агар вазифа аниқ бўлса, clarifying_questions бўш бўлсин
- агар вазифа ноаниқ бўлса, 3 тагача аниқлаштирувчи савол бер
- сен ўзинг мутахассис жавобини ёзмайсан
- сенинг вазифанг — тўғри ботни жонлантириш ва жараённи бошқариш
"""

def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def message_mentions_bot(text: str, bot_username: str) -> bool:
    if not text:
        return False
    return f"@{bot_username.lower()}" in text.lower()

def is_from_leader(update: Update) -> bool:
    username = (update.effective_user.username or "").lower()
    return username == LEADER_USERNAME.lower()

def should_controller_reply(update: Update) -> bool:
    if not update.message:
        return False

    txt = update.message.text or update.message.caption or ""

    if is_from_leader(update) and message_mentions_bot(txt, CONTROLLER_BOT_USERNAME):
        return True

    if is_from_leader(update) and update.message.reply_to_message:
        reply_from = update.message.reply_to_message.from_user
        if reply_from and (reply_from.username or "").lower() == CONTROLLER_BOT_USERNAME.lower():
            return True

    return False

def speech_to_text(audio_file_path: str) -> str:
    with open(audio_file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=audio_file,
        )
    return (transcription.text or "").strip()

def elevenlabs_text_to_speech(text: str) -> BytesIO:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_44100_128"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    data = {
        "text": text[:2500],
        "model_id": "eleven_multilingual_v2",
    }

    response = requests.post(url, json=data, headers=headers, timeout=120)

    if response.status_code != 200:
        raise RuntimeError(f"ElevenLabs xatolik: {response.status_code} | {response.text}")

    audio = BytesIO(response.content)
    audio.name = "voice.mp3"
    audio.seek(0)
    return audio

async def send_voice_reply(update: Update, text: str):
    try:
        audio_file = elevenlabs_text_to_speech(text)
        await update.message.reply_voice(voice=audio_file)
    except Exception as e:
        logger.exception("ElevenLabs ovozli javob xatosi")
        await update.message.reply_text(f"Хатолик юз берди: {str(e)}")

def parse_controller_json(raw_text: str) -> Dict[str, Any]:
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "task_summary": raw_text[:400],
            "goal": "Раҳбар берган вазифани бажартириш",
            "assignee_key": "ceo",
            "assignee_reason": "Аниқ роль ажратилмади, CEO орқали аниқлансин",
            "deadline": "аниқлансин",
            "control_points": ["Вазифа аниқлансин", "Ижрочи тасдиқлансин", "Натижа текширилсин"],
            "risks": ["Вазифа ноаниқлиги"],
            "clarifying_questions": ["Вазифанинг аниқ натижаси нима?", "Қайси муддатгача керак?"],
        }

def generate_controller_plan(user_message: str) -> Dict[str, Any]:
    response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": CONTROLLER_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    raw = response.output_text.strip() if response.output_text else "{}"
    return parse_controller_json(raw)

def build_controller_text(plan: Dict[str, Any]) -> str:
    assignee_key = plan.get("assignee_key", "ceo")
    assignee = TEAM_MEMBERS.get(assignee_key, TEAM_MEMBERS["ceo"])

    control_points = plan.get("control_points") or []
    risks = plan.get("risks") or []
    clarifying_questions = plan.get("clarifying_questions") or []

    lines = []
    lines.append(f"@{assignee['username']}")
    lines.append("")
    lines.append("Назоратчи йўналтируви:")
    lines.append(f"Мутахассис: {assignee['name']}")
    lines.append(f"Никнейм: @{assignee['username']}")
    lines.append(f"Масъулият: {assignee['role']}")
    lines.append("")
    lines.append(f"Вазифа: {plan.get('task_summary', 'Аниқланмади')}")
    lines.append(f"Мақсад: {plan.get('goal', 'Аниқланмади')}")
    lines.append(f"Нега шу мутахассис: {plan.get('assignee_reason', 'Роль мос келади')}")
    lines.append(f"Дедлайн: {plan.get('deadline', 'Аниқлансин')}")

    if control_points:
        lines.append("")
        lines.append("Назорат нуқталари:")
        for i, item in enumerate(control_points, 1):
            lines.append(f"{i}. {item}")

    if risks:
        lines.append("")
        lines.append("Рисклар:")
        for i, item in enumerate(risks, 1):
            lines.append(f"{i}. {item}")

    if clarifying_questions:
        lines.append("")
        lines.append("Аниқлаштириш учун саволлар:")
        for i, item in enumerate(clarifying_questions, 1):
            lines.append(f"{i}. {item}")

    lines.append("")
    lines.append("Қоида:")
    lines.append("Мутахассис фақат ўз роли доирасида жавоб беради.")
    lines.append("Мутахассис раҳбарга тўғридан-тўғри чиқмайди.")
    lines.append("Натижа аввал назоратчига топширилади.")
    lines.append("Назоратчи қабул қилмагунча иш тугамаган ҳисобланади.")

    return "\n".join(lines)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Салом. Мен Назоратчи ботман.\n"
        "Раҳбардан келган вазифани таҳлил қиламан, тўғри мутахассисга йўналтираман ва жараённи назорат қиламан.\n"
        "Мен ўзим мутахассис ўрнида жавоб бермайман."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Ишлаш тартиби:\n"
        f"1. Раҳбар мени mention қилади: @{CONTROLLER_BOT_USERNAME}\n"
        f"2. Мен вазифани таҳлил қиламан\n"
        f"3. Тўғри мутахассисга йўналтираман\n"
        f"4. Тайёр ишни раҳбардан олдин текшираман"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if not should_controller_reply(update):
        return

    user_message = normalize_text(update.message.text)

    try:
        plan = generate_controller_plan(user_message)
        text = build_controller_text(plan)
        await update.message.reply_text(text)
        await send_voice_reply(update, text)
    except Exception as e:
        logger.exception("Controller text error")
        await update.message.reply_text(f"Хатолик юз берди: {str(e)}")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.voice:
        return
    if not should_controller_reply(update):
        return

    temp_ogg_path: Optional[str] = None

    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
            temp_ogg_path = temp_audio.name

        await voice_file.download_to_drive(temp_ogg_path)

        user_text = speech_to_text(temp_ogg_path)

        if not user_text:
            await update.message.reply_text("Овозли топшириқ тушунилмади.")
            return

        plan = generate_controller_plan(user_text)
        text = build_controller_text(plan)
        await update.message.reply_text(text)
        await send_voice_reply(update, text)

    except Exception as e:
        logger.exception("Controller voice error")
        await update.message.reply_text(f"Хатолик юз берди: {str(e)}")
    finally:
        if temp_ogg_path and os.path.exists(temp_ogg_path):
            os.remove(temp_ogg_path)

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Controller bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()