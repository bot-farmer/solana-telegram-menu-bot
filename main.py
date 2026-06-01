import os
import re
import html
from aiohttp import web

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand,
    Update,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "your_bot_username")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "telegrambotsecret")
WEBHOOK_HOST = (
    os.getenv("WEBHOOK_HOST")
    or os.getenv("KOYEB_PUBLIC_DOMAIN")
    or os.getenv("RENDER_EXTERNAL_HOSTNAME")
    or os.getenv("RENDER_EXTERNAL_URL")
)
PORT = int(os.getenv("PORT", "8080"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN fehlt. Bei Render als Environment Variable eintragen.")

if not WEBHOOK_HOST:
    raise RuntimeError("WEBHOOK_HOST oder RENDER_EXTERNAL_HOSTNAME fehlt.")

WEBHOOK_HOST = WEBHOOK_HOST.replace("https://", "").replace("http://", "").rstrip("/")
WEBHOOK_PATH = f"/telegram/{WEBHOOK_SECRET}"
WEBHOOK_URL = f"https://{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class ImportWalletState(StatesGroup):
    waiting_for_name = State()
    waiting_for_secret = State()


def get_ref_code(user) -> str:
    """
    Referral-Code wie im Screenshot:
    ref_username

    Wenn der User keinen Telegram-Username hat:
    ref_id123456789
    """
    if user and user.username:
        username = re.sub(r"[^A-Za-z0-9_]", "", user.username)
        return f"ref_{username}"

    user_id = user.id if user else "unknown"
    return f"ref_id{user_id}"


def get_ref_link(user) -> str:
    ref_code = get_ref_code(user)
    return f"https://t.me/{BOT_USERNAME}?start={ref_code}"


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔐 Import Wallet", callback_data="import_wallet"),
                InlineKeyboardButton(text="💳 Manage Wallet", callback_data="manage_wallet"),
            ],
            [
                InlineKeyboardButton(text="💰 Buy/Sell", callback_data="buy_sell"),
                InlineKeyboardButton(text="👥 Copy Trading", callback_data="copy_trading"),
            ],
            [
                InlineKeyboardButton(text="🏦 Portfolio", callback_data="portfolio"),
                InlineKeyboardButton(text="📌 Limit Order", callback_data="limit_order"),
            ],
            [
                InlineKeyboardButton(text="⚙️ Settings", callback_data="settings"),
                InlineKeyboardButton(text="🌐 Language", callback_data="language"),
            ],
            [
                InlineKeyboardButton(text="🏆 Refer & Earn", callback_data="refer"),
                InlineKeyboardButton(text="📖 Help", callback_data="help"),
            ],
        ]
    )


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_to_menu")]
        ]
    )


def import_wallet_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔐 Import Wallet", callback_data="import_wallet")]
        ]
    )


async def send_home(message: Message):
    referral_link = get_ref_link(message.from_user)

    text = (
        "💼 <b>Wallet</b>\n"
        "Address: —\n"
        "Balance: — ($—)\n\n"
        "🔗 <b>Referral</b>\n"
        f"Invite friends and earn rewards: {referral_link}\n\n"
        "🚀 <b>Getting Started</b>\n"
        "Send a token contract address to begin trading instantly.\n\n"
        "🔔 <i>Follow official accounts for updates and support.</i>"
    )

    await message.answer(
        text,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
        disable_web_page_preview=False,
    )


def is_solana_address(text: str) -> bool:
    text = text.strip()
    return bool(re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,50}", text))


def token_card(address: str) -> str:
    safe_address = html.escape(address)

    if address == "FDVu3VmwoeF2rymVkkmptNBAZxmBLqpjRBcGfZ4npump":
        name = "The Brainrot Kid"
        ticker = "$Brainrot"
        dex = "pumpswap"
        market_cap = "$98.86K"
        price = "$0.00009887"
        liquidity = "$25.35K"
    else:
        name = "Unknown Token"
        ticker = "$—"
        dex = "pumpswap"
        market_cap = "—"
        price = "—"
        liquidity = "—"

    return (
        "📌 <b>Solana</b>\n"
        f"{html.escape(name)} · <b>{html.escape(ticker)}</b>\n"
        f"<code>{safe_address}</code>\n\n"
        f"🏦 DEX: <b>{dex}</b>\n"
        f"📊 Market Cap: <b>{market_cap}</b>\n"
        f"💵 Price: <b>{price}</b>\n"
        f"💧 Liquidity: <b>{liquidity}</b>\n"
        "🧱 Tax: <b>N/A</b>\n\n"
        "💳 Balance: —\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ <b>You haven't set up a wallet yet</b>\n"
        "ℹ️ <i>To access token details, please import your wallet first</i>"
    )


async def set_commands():
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Open bot"),
            BotCommand(command="menu", description="Open menu"),
        ]
    )


@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    await send_home(message)


@dp.message(Command("menu"))
async def menu_handler(message: Message, state: FSMContext):
    await state.clear()
    await send_home(message)


@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await send_home(callback.message)


@dp.callback_query(F.data == "import_wallet")
async def import_wallet(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(ImportWalletState.waiting_for_name)

    await callback.message.answer(
        "🔐 <b>Import Wallet - Step 1 of 2</b>\n\n"
        "What would you like to name this wallet?\n\n"
        "Letters and numbers only.\n"
        '<i>For example: "MainWallet" or "Wallet123".</i>',
        parse_mode="HTML",
    )


@dp.message(ImportWalletState.waiting_for_name)
async def wallet_name_handler(message: Message, state: FSMContext):
    wallet_name = message.text.strip()

    if not re.fullmatch(r"[A-Za-z0-9]{1,32}", wallet_name):
        await message.answer(
            "⚠️ Please use letters and numbers only.\n"
            'Example: "MainWallet" or "Wallet123".'
        )
        return

    await state.update_data(wallet_name=wallet_name)
    await state.set_state(ImportWalletState.waiting_for_secret)

    await message.answer(
        "🔐 <b>Import Wallet - Step 2 of 2</b>\n\n"
        "Wallet import is currently disabled in this test version.\n\n"
        "⚠️ <b>Do not paste your private key or recovery phrase here.</b>\n\n"
        "This screen is only a placeholder for the wallet import flow.",
        parse_mode="HTML",
    )


@dp.message(ImportWalletState.waiting_for_secret)
async def secret_handler(message: Message, state: FSMContext):
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except Exception:
        pass

    await state.clear()
    await message.answer(
        "❌ Import failed!\n\n"
        "⚠️ Error: <i>Wallet import is currently disabled in this test version.</i>",
        parse_mode="HTML",
        reply_markup=back_keyboard(),
    )


@dp.message(F.text)
async def text_handler(message: Message):
    text = message.text.strip()

    if is_solana_address(text):
        await message.answer(
            token_card(text),
            parse_mode="HTML",
            reply_markup=import_wallet_keyboard(),
        )
    else:
        await message.answer(
            "Please enter the token contract address:",
            reply_markup=back_keyboard(),
        )


@dp.callback_query(F.data == "manage_wallet")
async def manage_wallet(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "💳 <b>Manage Wallet</b>\n\n"
        "No wallet connected yet.\n\n"
        "Import or create a wallet to continue.",
        parse_mode="HTML",
        reply_markup=import_wallet_keyboard(),
    )


@dp.callback_query(F.data == "buy_sell")
async def buy_sell(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "💰 <b>Buy/Sell</b>\n\n"
        "Please enter the token contract address:",
        parse_mode="HTML",
        reply_markup=back_keyboard(),
    )


@dp.callback_query(F.data == "copy_trading")
async def copy_trading(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "👥 <b>Copy Trading</b>\n\n"
        "Copy trading is not active yet.\n\n"
        "Soon you will be able to follow selected wallets.",
        parse_mode="HTML",
        reply_markup=back_keyboard(),
    )


@dp.callback_query(F.data == "portfolio")
async def portfolio(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "🏦 <b>Portfolio</b>\n\n"
        "Wallet: —\n"
        "Balance: —\n"
        "Tokens: —\n\n"
        "Please import or connect a wallet first.",
        parse_mode="HTML",
        reply_markup=import_wallet_keyboard(),
    )


@dp.callback_query(F.data == "limit_order")
async def limit_order(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "📌 <b>Limit Order</b>\n\n"
        "Limit orders are not active yet.\n\n"
        "This menu is already prepared for the next version.",
        parse_mode="HTML",
        reply_markup=back_keyboard(),
    )


@dp.callback_query(F.data == "settings")
async def settings(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "⚙️ <b>Settings</b>\n\n"
        "Slippage: —\n"
        "Gas/Priority Fee: —\n"
        "MEV Protection: —\n\n"
        "Settings will be added in the next version.",
        parse_mode="HTML",
        reply_markup=back_keyboard(),
    )


@dp.callback_query(F.data == "language")
async def language(callback: CallbackQuery):
    await callback.answer()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
                InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="lang_de"),
            ],
            [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_to_menu")],
        ]
    )
    await callback.message.answer(
        "🌐 <b>Language</b>\n\n"
        "Choose your language:",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@dp.callback_query(F.data.in_({"lang_en", "lang_de"}))
async def choose_language(callback: CallbackQuery):
    await callback.answer("Language saved")
    await callback.message.answer(
        "✅ Language setting saved.",
        reply_markup=back_keyboard(),
    )


@dp.callback_query(F.data == "refer")
async def refer(callback: CallbackQuery):
    await callback.answer()

    referral_link = get_ref_link(callback.from_user)

    await callback.message.answer(
        "🏆 <b>Refer & Earn</b>\n\n"
        f"Your referral link:\n{referral_link}\n\n"
        "Invite friends and earn rewards.",
        parse_mode="HTML",
        reply_markup=back_keyboard(),
        disable_web_page_preview=False,
    )


@dp.callback_query(F.data == "help")
async def help_handler(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "📖 <b>Help</b>\n\n"
        "1. Send a Solana token contract address.\n"
        "2. The bot shows token information.\n"
        "3. Wallet functions will be added later.\n\n"
        "Support: your-support@email.com",
        parse_mode="HTML",
        reply_markup=back_keyboard(),
    )


@dp.callback_query()
async def unknown_callback(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "This feature is not available yet.",
        reply_markup=back_keyboard(),
    )


async def health_check(request: web.Request):
    return web.Response(text="Bot is running.")


async def telegram_webhook(request: web.Request):
    secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")

    if secret_header != WEBHOOK_SECRET:
        return web.Response(status=403, text="Forbidden")

    update_data = await request.json()
    update = Update.model_validate(update_data, context={"bot": bot})
    await dp.feed_update(bot, update)

    return web.Response(text="OK")


async def on_startup(app: web.Application):
    await set_commands()
    await bot.set_webhook(WEBHOOK_URL, secret_token=WEBHOOK_SECRET)
    print(f"Webhook set to: {WEBHOOK_URL}")


async def on_shutdown(app: web.Application):
    await bot.session.close()


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_post(WEBHOOK_PATH, telegram_webhook)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="0.0.0.0", port=PORT)