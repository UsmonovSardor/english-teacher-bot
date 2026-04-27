"""Student registration — one-time on first entry."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from core import database as db

logger = logging.getLogger(__name__)

async def check_and_register(update, context):
    u = update.effective_user
    if not u: return True
    name = f"{u.first_name or ''} {u.last_name or ''}".strip()
    db.upsert_student(u.id, u.username or "", name)
    if db.is_registered(u.id): return True
    await start_registration(update, context)
    return False

async def start_registration(update, context):
    u = update.effective_user
    context.user_data["reg_step"] = "full_name"
    text = (
        f"👋 *Salom, {u.first_name}!*\n\n"
        "📚 *Lingua Bot*'ga xush kelibsiz!\n\n"
        "Botdan foydalanish uchun bir marta ro'yxatdan o'tishingiz kerak.\n\n"
        "📝 *To'liq ismingizni kiriting:*\n"
        "_Ism Familya (masalan: Sardor Usmonov)_"
    )
    if update.callback_query:
        await update.callback_query.answer()
        try: await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        except: await update.effective_chat.send_message(text, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.effective_chat.send_message(text, parse_mode=ParseMode.MARKDOWN)

async def handle_registration_text(update, context):
    step = context.user_data.get("reg_step")
    if not step: return False
    text = update.message.text.strip()
    if step == "full_name":
        if len(text) < 3:
            await update.message.reply_text("⚠️ To'liq ism familyangizni kiriting (kamida 3 harf)."); return True
        context.user_data["reg_full_name"] = text
        context.user_data["reg_step"] = "group"
        await update.message.reply_text(
            f"✅ *{text}*\n\n📚 *Qaysi guruhdasiz?*\n_Guruh raqamingizni kiriting (masalan: IDU-25-1)_",
            parse_mode=ParseMode.MARKDOWN)
        return True
    if step == "group":
        if len(text) < 1:
            await update.message.reply_text("⚠️ Guruh nomini kiriting."); return True
        full_name = context.user_data.pop("reg_full_name", "")
        context.user_data.pop("reg_step", None)
        db.register_student(update.effective_user.id, full_name, text)
        await update.message.reply_text(
            f"🎉 *Ro'yxatdan o'tdingiz!*\n\n👤 Ism: *{full_name}*\n📚 Guruh: *{text}*\n\nDarslarni boshlang:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📚 Darslarni ko'rish", callback_data="student")
            ]]))
        return True
    return False

async def show_profile(update, context):
    await update.callback_query.answer()
    u = update.effective_user
    student = db.get_student(u.id)
    if not student:
        await update.callback_query.answer("Profil topilmadi.", show_alert=True); return
    student = dict(student)
    stats  = db.student_stats(u.id)
    name   = student.get("full_name") or u.first_name or "Noma'lum"
    group  = student.get("group_name") or "Ko'rsatilmagan"
    joined = (student.get("joined_at") or "")[:10]
    text = (
        f"👤 *Mening profilim*\n\n"
        f"📛 Ism: *{name}*\n📚 Guruh: *{group}*\n📅 A'zo bo'lgan: *{joined}*\n\n"
        f"📊 *Statistika:*\n"
        f"👁 Ko'rilgan: *{stats['views']}* marta\n"
        f"📝 Topshirilgan: *{stats['tasks']}* vazifa\n"
        f"🎯 Quizlar: *{stats['quiz_count']}* ta | O'rtacha: *{stats['avg_score']}%*"
    )
    await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Bosh sahifa", callback_data="student")
        ]]))
