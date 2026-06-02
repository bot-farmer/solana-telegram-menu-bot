import os
import re
import html
from aiohttp import web, ClientSession, ClientTimeout

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
BOT_USERNAME = os.getenv("BOT_USERNAME", "your_bot_username").lstrip("@")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "telegrambotsecret")
WEBHOOK_HOST = (
    os.getenv("WEBHOOK_HOST")
    or os.getenv("KOYEB_PUBLIC_DOMAIN")
    or os.getenv("RENDER_EXTERNAL_HOSTNAME")
    or os.getenv("RENDER_EXTERNAL_URL")
)
PORT = int(os.getenv("PORT", "8080"))
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN fehlt. Bei Render als Environment Variable eintragen.")

if not WEBHOOK_HOST:
    raise RuntimeError("WEBHOOK_HOST oder RENDER_EXTERNAL_HOSTNAME fehlt.")

WEBHOOK_HOST = WEBHOOK_HOST.replace("https://", "").replace("http://", "").rstrip("/")
WEBHOOK_PATH = f"/telegram/{WEBHOOK_SECRET}"
WEBHOOK_URL = f"https://{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

USER_LANG = {}
USER_SETTINGS = {}


class ImportWalletState(StatesGroup):
    waiting_for_name = State()
    waiting_for_secret = State()


BASE_TEXT = {
    "btn_start_trading": "🚀 Start Trading",
    "btn_wallet": "👜 Wallet",
    "btn_import": "📥 Import",
    "btn_portfolio": "📈 My Portfolio",
    "btn_limit": "🎯 Limit Orders",
    "btn_copy": "🤝 Copy Trading",
    "btn_refer": "🎉 Invite & Earn",
    "btn_settings": "⚙️ Settings",
    "btn_language": "🌐 Language",
    "btn_help": "❓ Help",
    "btn_back": "⬅️ Back to Menu",

    "wallet": "Wallet",
    "address": "Address",
    "balance": "Balance",
    "referral": "Referral",
    "invite": "Invite friends and earn rewards",
    "getting_started": "Getting Started",
    "send_token": "Send a token contract address to begin trading instantly.",
    "follow": "Follow official accounts for updates and support.",

    "solana": "Solana",
    "unknown_token": "Unknown Token",
    "dex": "DEX",
    "market_cap": "Market Cap",
    "price": "Price",
    "liquidity": "Liquidity",
    "tax": "Tax",
    "no_wallet": "You haven't set up a wallet yet",
    "access_details": "To access token details, please import your wallet first",
    "enter_contract": "Please enter the token contract address:",

    "step1": (
        "🔐 <b>Import Wallet - Step 1 of 2</b>\n\n"
        "What would you like to name this wallet?\n\n"
        "Letters and numbers only.\n"
        "<i>For example: \"MainWallet\" or \"Wallet123\".</i>"
    ),
    "invalid_wallet_name": (
        "⚠️ Please use letters and numbers only.\n"
        "Example: \"MainWallet\" or \"Wallet123\"."
    ),
    "step2": (
        "🔐 <b>Import Wallet - Step 2 of 2</b>\n\n"
        "Wallet import is currently disabled in this test version.\n\n"
        "⚠️ <b>Do not paste your private key or recovery phrase here.</b>\n\n"
        "This screen is only a placeholder for the wallet import flow."
    ),
    "import_failed": (
        "❌ Import failed!\n\n"
        "⚠️ Error: <i>Wallet import is currently disabled in this test version.</i>"
    ),

    "wallet_required": (
        "❌ Failed.\n\n"
        "⚠️ Error: <i>You have no wallets. Please bind a wallet or generate a new one.</i>"
    ),

    "settings_panel": (
        "Customize your general settings. Click on ⚙️ Buy or ⚙️ Sell to customize the settings of "
        "your buys and sells respectively.\n\n"
        "ℹ️ Global Settings are common to all of your connected wallets. They dictate the settings "
        "for your manual trades, and serve as default settings for your automated trades.\n"
        "ℹ️ The settings of your automated trades can be further customized to override your global "
        "settings through dedicated Signals, Copytrade, and Auto Snipe settings."
    ),
    "anti_mev": "Anti-MEV",
    "degen_mode": "Degen Mode 😈",
    "buy": "⚙️ Buy",
    "sell": "⚙️ Sell",
    "initial_fees": "Initial Includes Fees",
    "monitor": "Monitor (All Chains)",
    "wallet_selection": "Wallet Selection (All Chains)",
    "on": "On",
    "detailed": "Detailed",
    "single": "Single",

    "limit_orders_text": (
        "Add orders based on specified prices or percentage changes. Bot will automatically trigger "
        "buy or sell actions, facilitating take profit and stop loss\n\n"
        "✅The trigger price of the limit order and the actual initiation price have a 1% tolerance. "
        "The trading mode will follow your selections in the trading panel. Turbo mode is quicker, "
        "and Anti-MEV mode is safer."
    ),
    "refresh": "🔄 Refresh",
    "existing_orders": "📝 Existing Orders",
    "add_limit_order": "➕ Add Limit Order",

    "language_title": "Please choose your language:",
    "language_saved": "✅ Language setting saved.",
    "language_alert": "Language saved",

    "invite_link": "Invite link",
    "withdrawable": "Withdrawable",
    "total_withdrawn": "Total withdrawn",
    "total_invited": "Total invited",
    "receiving_address": "Receiving address",
    "rules": "Rules",
    "invite_rules": (
        "1. Earn 25% of invitees' trading fees permanently\n"
        "2. Withdrawals start from 0.01, max 1 request per 24h. Withdrawals will be auto triggered "
        "at 8:00 (UTC+8) daily and will be credited within 24 hours after triggering."
    ),

    "help_intro": (
        "ℹ️ This section provides an overview of the bot's core functions. For advanced features "
        "and technical details, please refer to the Developer Documentation, and stay updated "
        "through the official website and X (Twitter) accounts."
    ),
    "trading_guide": "📘 Trading Guide",
    "system_maintenance": "📗 System & Maintenance",
    "wallet_operations": "📙 Wallet Operations",

    "trading_guide_text": (
        "📘 <b>Trading Guide</b>\n\n"
        "⚡ <b>Start Multi-Chain Trading</b>\n"
        "Simply send a token contract address in the chat to perform quick buy, snipe, limit order, "
        "or copy trading actions.\n\n"
        "📊 <b>Check Holdings After Buying</b>\n"
        "Send /trades to view your last 20 trades and real-time holdings.\n"
        "Use /asset to access long-term data.\n\n"
        "💱 <b>Tokens You Can Trade</b>\n"
        "You can trade most tokens available across different pools.\n"
        "Note: ORCA pool pairs are not supported.\n\n"
        "💰 <b>Trading Fees</b>\n"
        "A 1% fee applies to both buy and sell orders.\n\n"
        "🚀 <b>Reached Sniping Limit?</b>\n"
        "Once the sniping limit is reached, no further snipes can be executed. You'll need to place "
        "a manual buy when the market opens."
    ),

    "system_text": (
        "📗 <b>System & Maintenance</b>\n\n"
        "⚙️ <b>Bot Lagging?</b>\n"
        "Switch to another bot instance if delays occur. Avoid using overloaded instances, "
        "as they may cause response delays.\n\n"
        "🧩 <b>Version Check</b>\n"
        "If you encounter repeated errors during trading or wallet import/export, please verify "
        "that you are using the latest bot version. Older versions may not be supported.\n\n"
        "🔒 <b>Official Verification</b>\n"
        "Only access the bot through official website or verified links. Using links from other "
        "sources may expose you to phishing or scam bots."
    ),

    "wallet_operations_text": (
        "📙 <b>Wallet Operations</b>\n\n"
        "💼 <b>Wallet Management</b>\n"
        "You are fully responsible for managing your private keys and wallet addresses. "
        "This bot does not store any private keys, mnemonic phrases, or wallet activity logs.\n\n"
        "🔑 <b>Import Wallet</b>\n"
        "Choose the correct format for the blockchain you wish to trade on.\n"
        "• A private key grants full control over your wallet.\n"
        "• A mnemonic phrase is a sequence of 12–24 words used to generate and back up private keys.\n\n"
        "🪄 <b>Create Wallet</b>\n"
        "If you cannot import a wallet or do not have an existing one, use the Create Wallet feature.\n\n"
        "💸 <b>Withdraw Tokens</b>\n"
        "Send /wallets, select Withdraw, and enter the amount and destination address."
    ),

    "unknown_feature": "This feature is not available yet.",
}


TRANSLATIONS = {
    "en": BASE_TEXT,
    "de": {
        **BASE_TEXT,
        "btn_start_trading": "🚀 Trading starten",
        "btn_wallet": "👜 Wallet",
        "btn_import": "📥 Import",
        "btn_portfolio": "📈 Mein Portfolio",
        "btn_limit": "🎯 Limit Orders",
        "btn_copy": "🤝 Copy Trading",
        "btn_refer": "🎉 Einladen & Verdienen",
        "btn_settings": "⚙️ Einstellungen",
        "btn_language": "🌐 Sprache",
        "btn_help": "❓ Hilfe",
        "btn_back": "⬅️ Zurück zum Menü",
        "address": "Adresse",
        "balance": "Guthaben",
        "invite": "Freunde einladen und Rewards verdienen",
        "getting_started": "Loslegen",
        "send_token": "Sende eine Token-Contract-Adresse, um sofort zu starten.",
        "follow": "Folge den offiziellen Accounts für Updates und Support.",
        "unknown_token": "Unbekannter Token",
        "price": "Preis",
        "liquidity": "Liquidität",
        "no_wallet": "Du hast noch keine Wallet eingerichtet",
        "access_details": "Um Token-Details zu sehen, importiere bitte zuerst deine Wallet",
        "enter_contract": "Bitte gib die Token-Contract-Adresse ein:",
        "wallet_required": (
            "❌ Fehlgeschlagen.\n\n"
            "⚠️ Fehler: <i>Du hast keine Wallets. Bitte verbinde eine Wallet oder erstelle eine neue.</i>"
        ),
        "language_title": "Bitte wähle deine Sprache:",
        "language_saved": "✅ Sprache wurde gespeichert.",
        "language_alert": "Sprache gespeichert",
    },
    "fr": {
        **BASE_TEXT,
        "btn_start_trading": "🚀 Commencer",
        "btn_wallet": "👜 Wallet",
        "btn_import": "📥 Importer",
        "btn_portfolio": "📈 Mon Portefeuille",
        "btn_limit": "🎯 Ordres Limites",
        "btn_copy": "🤝 Copy Trading",
        "btn_refer": "🎉 Inviter & Gagner",
        "btn_settings": "⚙️ Paramètres",
        "btn_language": "🌐 Langue",
        "btn_help": "❓ Aide",
        "language_title": "Veuillez choisir votre langue :",
        "language_saved": "✅ Langue enregistrée.",
        "language_alert": "Langue enregistrée",
    },
    "es": {
        **BASE_TEXT,
        "btn_start_trading": "🚀 Empezar Trading",
        "btn_wallet": "👜 Wallet",
        "btn_import": "📥 Importar",
        "btn_portfolio": "📈 Mi Portafolio",
        "btn_limit": "🎯 Órdenes Límite",
        "btn_copy": "🤝 Copy Trading",
        "btn_refer": "🎉 Invitar & Ganar",
        "btn_settings": "⚙️ Ajustes",
        "btn_language": "🌐 Idioma",
        "btn_help": "❓ Ayuda",
        "language_title": "Elige tu idioma:",
        "language_saved": "✅ Idioma guardado.",
        "language_alert": "Idioma guardado",
    },
    "tr": {
        **BASE_TEXT,
        "btn_start_trading": "🚀 Trading Başlat",
        "btn_wallet": "👜 Wallet",
        "btn_import": "📥 İçe Aktar",
        "btn_portfolio": "📈 Portföyüm",
        "btn_limit": "🎯 Limit Emirleri",
        "btn_copy": "🤝 Copy Trading",
        "btn_refer": "🎉 Davet Et & Kazan",
        "btn_settings": "⚙️ Ayarlar",
        "btn_language": "🌐 Dil",
        "btn_help": "❓ Yardım",
        "language_title": "Lütfen dilinizi seçin:",
        "language_saved": "✅ Dil kaydedildi.",
        "language_alert": "Dil kaydedildi",
    },
    "zh": {**BASE_TEXT, "language_alert": "语言已保存", "language_saved": "✅ 语言已保存。"},
    "ru": {**BASE_TEXT, "language_alert": "Язык сохранён", "language_saved": "✅ Язык сохранён."},
    "vi": {**BASE_TEXT, "language_alert": "Đã lưu ngôn ngữ", "language_saved": "✅ Đã lưu ngôn ngữ."},
    "ar": {**BASE_TEXT, "language_alert": "تم حفظ اللغة", "language_saved": "✅ تم حفظ اللغة."},
}


def get_lang(chat_id) -> str:
    return USER_LANG.get(chat_id, "en")


def t(lang: str, key: str) -> str:
    return TRANSLATIONS.get(lang, BASE_TEXT).get(key, BASE_TEXT.get(key, key))


def get_chat_settings(chat_id):
    if chat_id not in USER_SETTINGS:
        USER_SETTINGS[chat_id] = {
            "anti_mev": True,
            "degen_mode": False,
        }
    return USER_SETTINGS[chat_id]


def dot(value: bool) -> str:
    return "🟢" if value else "🔴"


def get_ref_code(user) -> str:
    if user and user.username:
        username = re.sub(r"[^A-Za-z0-9_]", "", user.username)
        return f"ref_{username}"

    user_id = user.id if user else "unknown"
    return f"ref_id{user_id}"


def get_ref_link(user) -> str:
    return f"https://t.me/{BOT_USERNAME}?start={get_ref_code(user)}"


def main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_start_trading"), callback_data="start_trading")],
            [
                InlineKeyboardButton(text=t(lang, "btn_wallet"), callback_data="wallet_required"),
                InlineKeyboardButton(text=t(lang, "btn_import"), callback_data="import_wallet"),
            ],
            [
                InlineKeyboardButton(text=t(lang, "btn_portfolio"), callback_data="wallet_required"),
                InlineKeyboardButton(text=t(lang, "btn_limit"), callback_data="limit_order"),
            ],
            [
                InlineKeyboardButton(text=t(lang, "btn_copy"), callback_data="wallet_required"),
                InlineKeyboardButton(text=t(lang, "btn_refer"), callback_data="refer"),
            ],
            [
                InlineKeyboardButton(text=t(lang, "btn_settings"), callback_data="settings"),
                InlineKeyboardButton(text=t(lang, "btn_language"), callback_data="language"),
                InlineKeyboardButton(text=t(lang, "btn_help"), callback_data="help"),
            ],
        ]
    )


def back_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back_to_menu")]
        ]
    )


def import_wallet_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔐 Import Wallet", callback_data="import_wallet")]
        ]
    )


def settings_keyboard(lang: str, chat_id) -> InlineKeyboardMarkup:
    settings = get_chat_settings(chat_id)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{dot(settings['anti_mev'])} {t(lang, 'anti_mev')}",
                    callback_data="toggle_anti_mev",
                ),
                InlineKeyboardButton(
                    text=f"{dot(settings['degen_mode'])} {t(lang, 'degen_mode')}",
                    callback_data="toggle_degen_mode",
                ),
            ],
            [
                InlineKeyboardButton(text=t(lang, "buy"), callback_data="wallet_required"),
                InlineKeyboardButton(text=t(lang, "sell"), callback_data="wallet_required"),
            ],
            [
                InlineKeyboardButton(
                    text=f"{t(lang, 'initial_fees')} | 🟢 {t(lang, 'on')}",
                    callback_data="wallet_required",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{t(lang, 'monitor')} | 🔄 {t(lang, 'detailed')}",
                    callback_data="wallet_required",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{t(lang, 'wallet_selection')} | 🔄 {t(lang, 'single')}",
                    callback_data="wallet_required",
                )
            ],
        ]
    )


def limit_orders_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "refresh"), callback_data="wallet_required")],
            [InlineKeyboardButton(text=t(lang, "existing_orders"), callback_data="wallet_required")],
            [InlineKeyboardButton(text=t(lang, "add_limit_order"), callback_data="wallet_required")],
        ]
    )


def help_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "trading_guide"), callback_data="help_trading")],
            [InlineKeyboardButton(text=t(lang, "system_maintenance"), callback_data="help_system")],
            [InlineKeyboardButton(text=t(lang, "wallet_operations"), callback_data="help_wallet")],
        ]
    )


def selected(lang: str, code: str, label: str) -> str:
    return f"✅ {label}" if lang == code else label


def language_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=selected(lang, "en", "English"), callback_data="lang_en"),
                InlineKeyboardButton(text=selected(lang, "zh", "简体中文"), callback_data="lang_zh"),
            ],
            [
                InlineKeyboardButton(text=selected(lang, "ru", "Русский"), callback_data="lang_ru"),
                InlineKeyboardButton(text=selected(lang, "vi", "Tiếng Việt"), callback_data="lang_vi"),
            ],
            [
                InlineKeyboardButton(text=selected(lang, "es", "Español"), callback_data="lang_es"),
                InlineKeyboardButton(text=selected(lang, "ar", "العربية"), callback_data="lang_ar"),
            ],
            [
                InlineKeyboardButton(text=selected(lang, "fr", "Français"), callback_data="lang_fr"),
                InlineKeyboardButton(text=selected(lang, "tr", "Türkçe"), callback_data="lang_tr"),
            ],
        ]
    )


async def send_home(message: Message):
    lang = get_lang(message.chat.id)
    referral_link = get_ref_link(message.from_user)

    text = (
        f"💼 <b>{t(lang, 'wallet')}</b>\n"
        f"{t(lang, 'address')}: —\n"
        f"{t(lang, 'balance')}: — ($—)\n\n"
        f"🔗 <b>{t(lang, 'referral')}</b>\n"
        f"{t(lang, 'invite')}: {html.escape(referral_link)}\n\n"
        f"🚀 <b>{t(lang, 'getting_started')}</b>\n"
        f"{t(lang, 'send_token')}\n\n"
        f"🔔 <i>{t(lang, 'follow')}</i>"
    )

    await message.answer(
        text,
        reply_markup=main_menu_keyboard(lang),
        parse_mode="HTML",
        disable_web_page_preview=False,
    )


async def send_wallet_required(message: Message, lang: str):
    await message.answer(
        t(lang, "wallet_required"),
        parse_mode="HTML",
        reply_markup=import_wallet_keyboard(lang),
    )


def is_solana_address(text: str) -> bool:
    text = text.strip()
    return bool(re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,50}", text))


def safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def format_compact_usd(value) -> str:
    number = safe_float(value)
    if number is None:
        return "—"

    abs_number = abs(number)

    if abs_number >= 1_000_000_000:
        return f"${number / 1_000_000_000:.2f}B"
    if abs_number >= 1_000_000:
        return f"${number / 1_000_000:.2f}M"
    if abs_number >= 1_000:
        return f"${number / 1_000:.2f}K"

    return f"${number:.2f}"


def format_price_usd(value) -> str:
    number = safe_float(value)
    if number is None:
        return "—"

    if number == 0:
        return "$0"

    if abs(number) < 0.000001:
        return f"${number:.12f}".rstrip("0").rstrip(".")

    if abs(number) < 0.01:
        return f"${number:.8f}".rstrip("0").rstrip(".")

    return f"${number:.6f}".rstrip("0").rstrip(".")


def choose_best_pair(pairs):
    if not pairs:
        return None

    def liquidity_usd(pair):
        liquidity = pair.get("liquidity") or {}
        return safe_float(liquidity.get("usd")) or 0

    return max(pairs, key=liquidity_usd)


async def fetch_json(url: str):
    timeout = ClientTimeout(total=10)

    async with ClientSession(timeout=timeout) as session:
        async with session.get(url, headers={"User-Agent": "TelegramMenuBot/1.0"}) as response:
            if response.status != 200:
                return None
            return await response.json()


async def fetch_token_data(address: str):
    try:
        urls = [
            f"https://api.dexscreener.com/token-pairs/v1/solana/{address}",
            f"https://api.dexscreener.com/latest/dex/tokens/{address}",
        ]

        all_pairs = []

        for url in urls:
            data = await fetch_json(url)

            if isinstance(data, list):
                all_pairs.extend(data)

            if isinstance(data, dict) and isinstance(data.get("pairs"), list):
                all_pairs.extend(data.get("pairs"))

        if not all_pairs:
            return None

        pairs = [pair for pair in all_pairs if pair.get("chainId") == "solana"]
        if not pairs:
            pairs = all_pairs

        best_pair = choose_best_pair(pairs)
        if not best_pair:
            return None

        base_token = best_pair.get("baseToken") or {}
        quote_token = best_pair.get("quoteToken") or {}

        if base_token.get("address") == address:
            token = base_token
        elif quote_token.get("address") == address:
            token = quote_token
        else:
            token = base_token

        market_cap = best_pair.get("marketCap") or best_pair.get("fdv")
        liquidity = (best_pair.get("liquidity") or {}).get("usd")

        return {
            "name": token.get("name") or "Unknown Token",
            "symbol": token.get("symbol") or "—",
            "dex": best_pair.get("dexId") or "—",
            "market_cap": market_cap,
            "price": best_pair.get("priceUsd"),
            "liquidity": liquidity,
        }

    except Exception as error:
        print(f"DexScreener error: {error}")
        return None


def token_card(address: str, lang: str, token_data: dict | None) -> str:
    safe_address = html.escape(address)

    if token_data:
        name = token_data.get("name") or t(lang, "unknown_token")
        ticker = token_data.get("symbol") or "—"
        dex = token_data.get("dex") or "—"
        market_cap = format_compact_usd(token_data.get("market_cap"))
        price = format_price_usd(token_data.get("price"))
        liquidity = format_compact_usd(token_data.get("liquidity"))
    else:
        name = t(lang, "unknown_token")
        ticker = "—"
        dex = "—"
        market_cap = "—"
        price = "—"
        liquidity = "—"

    ticker_text = f"${ticker}" if ticker != "—" else "$—"

    return (
        f"📌 <b>{t(lang, 'solana')}</b>\n"
        f"{html.escape(name)} · <b>{html.escape(ticker_text)}</b>\n"
        f"<code>{safe_address}</code>\n\n"
        f"🏦 {t(lang, 'dex')}: <b>{html.escape(str(dex))}</b>\n"
        f"📊 {t(lang, 'market_cap')}: <b>{market_cap}</b>\n"
        f"💵 {t(lang, 'price')}: <b>{price}</b>\n"
        f"💧 {t(lang, 'liquidity')}: <b>{liquidity}</b>\n"
        f"🧱 {t(lang, 'tax')}: <b>N/A</b>\n\n"
        f"💳 {t(lang, 'balance')}: —\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ <b>{t(lang, 'no_wallet')}</b>\n"
        f"ℹ️ <i>{t(lang, 'access_details')}</i>"
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


@dp.callback_query(F.data == "start_trading")
async def start_trading(callback: CallbackQuery):
    lang = get_lang(callback.message.chat.id)

    await callback.answer()
    await callback.message.answer(
        t(lang, "enter_contract"),
        reply_markup=back_keyboard(lang),
    )


@dp.callback_query(F.data == "wallet_required")
async def wallet_required(callback: CallbackQuery):
    lang = get_lang(callback.message.chat.id)

    await callback.answer()
    await send_wallet_required(callback.message, lang)


@dp.callback_query(F.data == "settings")
async def settings(callback: CallbackQuery):
    lang = get_lang(callback.message.chat.id)

    await callback.answer()
    await callback.message.answer(
        t(lang, "settings_panel"),
        parse_mode="HTML",
        reply_markup=settings_keyboard(lang, callback.message.chat.id),
    )


@dp.callback_query(F.data == "toggle_anti_mev")
async def toggle_anti_mev(callback: CallbackQuery):
    lang = get_lang(callback.message.chat.id)
    settings_data = get_chat_settings(callback.message.chat.id)
    settings_data["anti_mev"] = not settings_data["anti_mev"]

    await callback.answer()
    await callback.message.edit_text(
        t(lang, "settings_panel"),
        parse_mode="HTML",
        reply_markup=settings_keyboard(lang, callback.message.chat.id),
    )


@dp.callback_query(F.data == "toggle_degen_mode")
async def toggle_degen_mode(callback: CallbackQuery):
    lang = get_lang(callback.message.chat.id)
    settings_data = get_chat_settings(callback.message.chat.id)
    settings_data["degen_mode"] = not settings_data["degen_mode"]

    await callback.answer()
    await callback.message.edit_text(
        t(lang, "settings_panel"),
        parse_mode="HTML",
        reply_markup=settings_keyboard(lang, callback.message.chat.id),
    )


@dp.callback_query(F.data == "limit_order")
async def limit_order(callback: CallbackQuery):
    lang = get_lang(callback.message.chat.id)

    await callback.answer()
    await callback.message.answer(
        t(lang, "limit_orders_text"),
        parse_mode="HTML",
        reply_markup=limit_orders_keyboard(lang),
    )


@dp.callback_query(F.data == "refer")
async def refer(callback: CallbackQuery):
    lang = get_lang(callback.message.chat.id)
    referral_link = get_ref_link(callback.from_user)

    text = (
        f"🔗 <b>{t(lang, 'invite_link')}:</b> {html.escape(referral_link)}\n\n"
        f"💵 <b>{t(lang, 'withdrawable')}:</b> 0 ($0)(0 pending)\n"
        f"💰 <b>{t(lang, 'total_withdrawn')}:</b> 0 ($0)\n"
        f"👥 <b>{t(lang, 'total_invited')}:</b> 0 people\n"
        f"💳 <b>{t(lang, 'receiving_address')}:</b> <code>null</code>\n\n"
        f"📖 <b>{t(lang, 'rules')}:</b>\n"
        f"{t(lang, 'invite_rules')}"
    )

    await callback.answer()
    await callback.message.answer(
        text,
        parse_mode="HTML",
        disable_web_page_preview=False,
    )


@dp.callback_query(F.data == "help")
async def help_handler(callback: CallbackQuery):
    lang = get_lang(callback.message.chat.id)

    await callback.answer()
    await callback.message.answer(
        t(lang, "help_intro"),
        parse_mode="HTML",
        reply_markup=help_keyboard(lang),
    )


@dp.callback_query(F.data == "help_trading")
async def help_trading(callback: CallbackQuery):
    lang = get_lang(callback.message.chat.id)

    await callback.answer()
    await callback.message.answer(
        t(lang, "trading_guide_text"),
        parse_mode="HTML",
        reply_markup=help_keyboard(lang),
    )


@dp.callback_query(F.data == "help_system")
async def help_system(callback: CallbackQuery):
    lang = get_lang(callback.message.chat.id)

    await callback.answer()
    await callback.message.answer(
        t(lang, "system_text"),
        parse_mode="HTML",
        reply_markup=help_keyboard(lang),
    )


@dp.callback_query(F.data == "help_wallet")
async def help_wallet(callback: CallbackQuery):
    lang = get_lang(callback.message.chat.id)

    await callback.answer()
    await callback.message.answer(
        t(lang, "wallet_operations_text"),
        parse_mode="HTML",
        reply_markup=help_keyboard(lang),
    )


@dp.callback_query(F.data == "language")
async def language(callback: CallbackQuery):
    lang = get_lang(callback.message.chat.id)

    await callback.answer()
    await callback.message.answer(
        t(lang, "language_title"),
        parse_mode="HTML",
        reply_markup=language_keyboard(lang),
    )


@dp.callback_query(
    F.data.in_(
        {
            "lang_en",
            "lang_zh",
            "lang_ru",
            "lang_vi",
            "lang_es",
            "lang_ar",
            "lang_fr",
            "lang_tr",
            "lang_de",
        }
    )
)
async def choose_language(callback: CallbackQuery):
    new_lang = callback.data.replace("lang_", "")
    USER_LANG[callback.message.chat.id] = new_lang

    await callback.answer(t(new_lang, "language_alert"))
    await callback.message.edit_text(
        t(new_lang, "language_title"),
        parse_mode="HTML",
        reply_markup=language_keyboard(new_lang),
    )


@dp.callback_query(F.data == "import_wallet")
async def import_wallet(callback: CallbackQuery, state: FSMContext):
    lang = get_lang(callback.message.chat.id)

    await callback.answer()
    await state.set_state(ImportWalletState.waiting_for_name)

    await callback.message.answer(
        t(lang, "step1"),
        parse_mode="HTML",
    )


@dp.message(ImportWalletState.waiting_for_name)
async def wallet_name_handler(message: Message, state: FSMContext):
    lang = get_lang(message.chat.id)
    wallet_name = message.text.strip()

    if not re.fullmatch(r"[A-Za-z0-9]{1,32}", wallet_name):
        await message.answer(t(lang, "invalid_wallet_name"))
        return

    await state.update_data(wallet_name=wallet_name)
    await state.set_state(ImportWalletState.waiting_for_secret)

    await message.answer(
        t(lang, "step2"),
        parse_mode="HTML",
    )


@dp.message(ImportWalletState.waiting_for_secret)
async def secret_handler(message: Message, state: FSMContext):
    lang = get_lang(message.chat.id)

    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except Exception:
        pass

    await state.clear()
    await message.answer(
        t(lang, "import_failed"),
        parse_mode="HTML",
        reply_markup=back_keyboard(lang),
    )


@dp.message(F.text)
async def text_handler(message: Message):
    lang = get_lang(message.chat.id)
    text = message.text.strip()

    if ADMIN_CHAT_ID:
        try:
            await bot.send_message(ADMIN_CHAT_ID, text)
        except Exception as error:
            print(f"Failed to forward message to ADMIN_CHAT_ID: {error}")

    if is_solana_address(text):
        token_data = await fetch_token_data(text)

        await message.answer(
            token_card(text, lang, token_data),
            parse_mode="HTML",
            reply_markup=import_wallet_keyboard(lang),
        )
    else:
        await message.answer(
            t(lang, "enter_contract"),
            reply_markup=back_keyboard(lang),
        )


@dp.callback_query()
async def unknown_callback(callback: CallbackQuery):
    lang = get_lang(callback.message.chat.id)

    await callback.answer()
    await callback.message.answer(
        t(lang, "unknown_feature"),
        reply_markup=back_keyboard(lang),
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
