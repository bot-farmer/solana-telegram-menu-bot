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

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN fehlt. Bei Render als Environment Variable eintragen.")

if not WEBHOOK_HOST:
    raise RuntimeError("WEBHOOK_HOST oder RENDER_EXTERNAL_HOSTNAME fehlt.")

WEBHOOK_HOST = WEBHOOK_HOST.replace("https://", "").replace("http://", "").rstrip("/")
WEBHOOK_PATH = f"/telegram/{WEBHOOK_SECRET}"
WEBHOOK_URL = f"https://{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Sprache wird erstmal nur im Speicher gehalten.
# Bei Render-Restart/Deploy kann diese Einstellung zurückgesetzt werden.
USER_LANG = {}


class ImportWalletState(StatesGroup):
    waiting_for_name = State()
    waiting_for_secret = State()


TRANSLATIONS = {
    "en": {
        "btn_import": "🔐 Import Wallet",
        "btn_manage": "💳 Manage Wallet",
        "btn_buy_sell": "💰 Buy/Sell",
        "btn_copy": "👥 Copy Trading",
        "btn_portfolio": "🏦 Portfolio",
        "btn_limit": "📌 Limit Order",
        "btn_settings": "⚙️ Settings",
        "btn_language": "🌐 Language",
        "btn_refer": "🏆 Refer & Earn",
        "btn_help": "📖 Help",
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
        "scan_failed": "Token data could not be loaded yet.",
        "step1": "🔐 <b>Import Wallet - Step 1 of 2</b>\n\nWhat would you like to name this wallet?\n\nLetters and numbers only.\n<i>For example: \"MainWallet\" or \"Wallet123\".</i>",
        "invalid_wallet_name": "⚠️ Please use letters and numbers only.\nExample: \"MainWallet\" or \"Wallet123\".",
        "step2": "🔐 <b>Import Wallet - Step 2 of 2</b>\n\nWallet import is currently disabled in this test version.\n\n⚠️ <b>Do not paste your private key or recovery phrase here.</b>\n\nThis screen is only a placeholder for the wallet import flow.",
        "import_failed": "❌ Import failed!\n\n⚠️ Error: <i>Wallet import is currently disabled in this test version.</i>",
        "manage_wallet": "💳 <b>Manage Wallet</b>\n\nNo wallet connected yet.\n\nImport or create a wallet to continue.",
        "buy_sell": "💰 <b>Buy/Sell</b>\n\nPlease enter the token contract address:",
        "copy_trading": "👥 <b>Copy Trading</b>\n\nCopy trading is not active yet.\n\nSoon you will be able to follow selected wallets.",
        "portfolio": "🏦 <b>Portfolio</b>\n\nWallet: —\nBalance: —\nTokens: —\n\nPlease import or connect a wallet first.",
        "limit_order": "📌 <b>Limit Order</b>\n\nLimit orders are not active yet.\n\nThis menu is already prepared for the next version.",
        "settings": "⚙️ <b>Settings</b>\n\nSlippage: —\nGas/Priority Fee: —\nMEV Protection: —\n\nSettings will be added in the next version.",
        "language_title": "🌐 <b>Language</b>\n\nChoose your language:",
        "language_saved": "✅ Language setting saved.",
        "language_alert": "Language saved",
        "refer_text": "🏆 <b>Refer & Earn</b>\n\nYour referral link:\n{link}\n\nInvite friends and earn rewards.",
        "help": "📖 <b>Help</b>\n\n1. Send a Solana token contract address.\n2. The bot shows token information.\n3. Wallet functions will be added later.\n\nSupport: your-support@email.com",
        "unknown_feature": "This feature is not available yet.",
    },
    "de": {
        "btn_import": "🔐 Wallet importieren",
        "btn_manage": "💳 Wallet verwalten",
        "btn_buy_sell": "💰 Kaufen/Verkaufen",
        "btn_copy": "👥 Copy Trading",
        "btn_portfolio": "🏦 Portfolio",
        "btn_limit": "📌 Limit Order",
        "btn_settings": "⚙️ Einstellungen",
        "btn_language": "🌐 Sprache",
        "btn_refer": "🏆 Freunde einladen",
        "btn_help": "📖 Hilfe",
        "btn_back": "⬅️ Zurück zum Menü",
        "wallet": "Wallet",
        "address": "Adresse",
        "balance": "Guthaben",
        "referral": "Empfehlung",
        "invite": "Freunde einladen und Rewards verdienen",
        "getting_started": "Loslegen",
        "send_token": "Sende eine Token-Contract-Adresse, um sofort zu starten.",
        "follow": "Folge den offiziellen Accounts für Updates und Support.",
        "solana": "Solana",
        "unknown_token": "Unbekannter Token",
        "dex": "DEX",
        "market_cap": "Market Cap",
        "price": "Preis",
        "liquidity": "Liquidität",
        "tax": "Tax",
        "no_wallet": "Du hast noch keine Wallet eingerichtet",
        "access_details": "Um Token-Details zu sehen, importiere bitte zuerst deine Wallet",
        "enter_contract": "Bitte gib die Token-Contract-Adresse ein:",
        "scan_failed": "Token-Daten konnten noch nicht geladen werden.",
        "step1": "🔐 <b>Wallet importieren - Schritt 1 von 2</b>\n\nWie möchtest du diese Wallet nennen?\n\nNur Buchstaben und Zahlen.\n<i>Zum Beispiel: \"MainWallet\" oder \"Wallet123\".</i>",
        "invalid_wallet_name": "⚠️ Bitte nur Buchstaben und Zahlen verwenden.\nBeispiel: \"MainWallet\" oder \"Wallet123\".",
        "step2": "🔐 <b>Wallet importieren - Schritt 2 von 2</b>\n\nDer Wallet-Import ist in dieser Testversion aktuell deaktiviert.\n\n⚠️ <b>Füge hier keinen Private Key und keine Recovery Phrase ein.</b>\n\nDieser Bildschirm ist nur ein Platzhalter für den Wallet-Import.",
        "import_failed": "❌ Import fehlgeschlagen!\n\n⚠️ Fehler: <i>Der Wallet-Import ist in dieser Testversion aktuell deaktiviert.</i>",
        "manage_wallet": "💳 <b>Wallet verwalten</b>\n\nEs ist noch keine Wallet verbunden.\n\nImportiere oder erstelle eine Wallet, um fortzufahren.",
        "buy_sell": "💰 <b>Kaufen/Verkaufen</b>\n\nBitte gib die Token-Contract-Adresse ein:",
        "copy_trading": "👥 <b>Copy Trading</b>\n\nCopy Trading ist noch nicht aktiv.\n\nBald kannst du ausgewählten Wallets folgen.",
        "portfolio": "🏦 <b>Portfolio</b>\n\nWallet: —\nGuthaben: —\nTokens: —\n\nBitte importiere oder verbinde zuerst eine Wallet.",
        "limit_order": "📌 <b>Limit Order</b>\n\nLimit Orders sind noch nicht aktiv.\n\nDieses Menü ist bereits für die nächste Version vorbereitet.",
        "settings": "⚙️ <b>Einstellungen</b>\n\nSlippage: —\nGas/Priority Fee: —\nMEV-Schutz: —\n\nEinstellungen werden in der nächsten Version ergänzt.",
        "language_title": "🌐 <b>Sprache</b>\n\nWähle deine Sprache:",
        "language_saved": "✅ Sprache wurde gespeichert.",
        "language_alert": "Sprache gespeichert",
        "refer_text": "🏆 <b>Freunde einladen</b>\n\nDein Referral-Link:\n{link}\n\nLade Freunde ein und verdiene Rewards.",
        "help": "📖 <b>Hilfe</b>\n\n1. Sende eine Solana Token-Contract-Adresse.\n2. Der Bot zeigt Token-Informationen an.\n3. Wallet-Funktionen werden später ergänzt.\n\nSupport: your-support@email.com",
        "unknown_feature": "Diese Funktion ist noch nicht verfügbar.",
    },
    "fr": {
        "btn_import": "🔐 Importer Wallet",
        "btn_manage": "💳 Gérer Wallet",
        "btn_buy_sell": "💰 Acheter/Vendre",
        "btn_copy": "👥 Copy Trading",
        "btn_portfolio": "🏦 Portefeuille",
        "btn_limit": "📌 Ordre Limite",
        "btn_settings": "⚙️ Paramètres",
        "btn_language": "🌐 Langue",
        "btn_refer": "🏆 Parrainage",
        "btn_help": "📖 Aide",
        "btn_back": "⬅️ Retour au menu",
        "wallet": "Wallet",
        "address": "Adresse",
        "balance": "Solde",
        "referral": "Parrainage",
        "invite": "Invitez des amis et gagnez des récompenses",
        "getting_started": "Commencer",
        "send_token": "Envoyez une adresse de contrat token pour commencer.",
        "follow": "Suivez les comptes officiels pour les mises à jour et le support.",
        "solana": "Solana",
        "unknown_token": "Token inconnu",
        "dex": "DEX",
        "market_cap": "Capitalisation",
        "price": "Prix",
        "liquidity": "Liquidité",
        "tax": "Taxe",
        "no_wallet": "Vous n'avez pas encore configuré de wallet",
        "access_details": "Pour accéder aux détails du token, importez d'abord votre wallet",
        "enter_contract": "Veuillez saisir l'adresse du contrat token :",
        "scan_failed": "Les données du token n'ont pas pu être chargées.",
        "step1": "🔐 <b>Importer Wallet - Étape 1 sur 2</b>\n\nQuel nom souhaitez-vous donner à ce wallet ?\n\nLettres et chiffres uniquement.\n<i>Par exemple : \"MainWallet\" ou \"Wallet123\".</i>",
        "invalid_wallet_name": "⚠️ Utilisez uniquement des lettres et des chiffres.\nExemple : \"MainWallet\" ou \"Wallet123\".",
        "step2": "🔐 <b>Importer Wallet - Étape 2 sur 2</b>\n\nL'import de wallet est désactivé dans cette version de test.\n\n⚠️ <b>Ne collez pas votre clé privée ou phrase de récupération ici.</b>\n\nCet écran est seulement un placeholder.",
        "import_failed": "❌ Import échoué !\n\n⚠️ Erreur : <i>L'import de wallet est désactivé dans cette version de test.</i>",
        "manage_wallet": "💳 <b>Gérer Wallet</b>\n\nAucun wallet connecté.\n\nImportez ou créez un wallet pour continuer.",
        "buy_sell": "💰 <b>Acheter/Vendre</b>\n\nVeuillez saisir l'adresse du contrat token :",
        "copy_trading": "👥 <b>Copy Trading</b>\n\nLe copy trading n'est pas encore actif.\n\nBientôt, vous pourrez suivre des wallets sélectionnés.",
        "portfolio": "🏦 <b>Portefeuille</b>\n\nWallet : —\nSolde : —\nTokens : —\n\nVeuillez d'abord importer ou connecter un wallet.",
        "limit_order": "📌 <b>Ordre Limite</b>\n\nLes ordres limites ne sont pas encore actifs.\n\nCe menu est préparé pour la prochaine version.",
        "settings": "⚙️ <b>Paramètres</b>\n\nSlippage : —\nGas/Priority Fee : —\nProtection MEV : —\n\nLes paramètres seront ajoutés plus tard.",
        "language_title": "🌐 <b>Langue</b>\n\nChoisissez votre langue :",
        "language_saved": "✅ Langue enregistrée.",
        "language_alert": "Langue enregistrée",
        "refer_text": "🏆 <b>Parrainage</b>\n\nVotre lien :\n{link}\n\nInvitez des amis et gagnez des récompenses.",
        "help": "📖 <b>Aide</b>\n\n1. Envoyez une adresse de contrat Solana.\n2. Le bot affiche les informations du token.\n3. Les fonctions wallet seront ajoutées plus tard.\n\nSupport : your-support@email.com",
        "unknown_feature": "Cette fonction n'est pas encore disponible.",
    },
    "es": {
        "btn_import": "🔐 Importar Wallet",
        "btn_manage": "💳 Gestionar Wallet",
        "btn_buy_sell": "💰 Comprar/Vender",
        "btn_copy": "👥 Copy Trading",
        "btn_portfolio": "🏦 Portafolio",
        "btn_limit": "📌 Orden Límite",
        "btn_settings": "⚙️ Ajustes",
        "btn_language": "🌐 Idioma",
        "btn_refer": "🏆 Invitar",
        "btn_help": "📖 Ayuda",
        "btn_back": "⬅️ Volver al menú",
        "wallet": "Wallet",
        "address": "Dirección",
        "balance": "Saldo",
        "referral": "Referidos",
        "invite": "Invita amigos y gana recompensas",
        "getting_started": "Primeros pasos",
        "send_token": "Envía una dirección de contrato token para empezar.",
        "follow": "Sigue las cuentas oficiales para actualizaciones y soporte.",
        "solana": "Solana",
        "unknown_token": "Token desconocido",
        "dex": "DEX",
        "market_cap": "Capitalización",
        "price": "Precio",
        "liquidity": "Liquidez",
        "tax": "Impuesto",
        "no_wallet": "Aún no has configurado una wallet",
        "access_details": "Para ver detalles del token, primero importa tu wallet",
        "enter_contract": "Introduce la dirección del contrato token:",
        "scan_failed": "No se pudieron cargar los datos del token.",
        "step1": "🔐 <b>Importar Wallet - Paso 1 de 2</b>\n\n¿Cómo quieres llamar a esta wallet?\n\nSolo letras y números.\n<i>Por ejemplo: \"MainWallet\" o \"Wallet123\".</i>",
        "invalid_wallet_name": "⚠️ Usa solo letras y números.\nEjemplo: \"MainWallet\" o \"Wallet123\".",
        "step2": "🔐 <b>Importar Wallet - Paso 2 de 2</b>\n\nLa importación de wallet está desactivada en esta versión de prueba.\n\n⚠️ <b>No pegues aquí tu clave privada ni frase de recuperación.</b>\n\nEsta pantalla es solo un placeholder.",
        "import_failed": "❌ ¡Importación fallida!\n\n⚠️ Error: <i>La importación de wallet está desactivada en esta versión de prueba.</i>",
        "manage_wallet": "💳 <b>Gestionar Wallet</b>\n\nNo hay wallet conectada.\n\nImporta o crea una wallet para continuar.",
        "buy_sell": "💰 <b>Comprar/Vender</b>\n\nIntroduce la dirección del contrato token:",
        "copy_trading": "👥 <b>Copy Trading</b>\n\nCopy trading aún no está activo.\n\nPronto podrás seguir wallets seleccionadas.",
        "portfolio": "🏦 <b>Portafolio</b>\n\nWallet: —\nSaldo: —\nTokens: —\n\nPrimero importa o conecta una wallet.",
        "limit_order": "📌 <b>Orden Límite</b>\n\nLas órdenes límite aún no están activas.\n\nEste menú está preparado para la próxima versión.",
        "settings": "⚙️ <b>Ajustes</b>\n\nSlippage: —\nGas/Priority Fee: —\nProtección MEV: —\n\nLos ajustes se añadirán después.",
        "language_title": "🌐 <b>Idioma</b>\n\nElige tu idioma:",
        "language_saved": "✅ Idioma guardado.",
        "language_alert": "Idioma guardado",
        "refer_text": "🏆 <b>Invitar</b>\n\nTu enlace de referido:\n{link}\n\nInvita amigos y gana recompensas.",
        "help": "📖 <b>Ayuda</b>\n\n1. Envía una dirección de contrato Solana.\n2. El bot muestra información del token.\n3. Las funciones wallet se añadirán después.\n\nSoporte: your-support@email.com",
        "unknown_feature": "Esta función aún no está disponible.",
    },
    "pt": {
        "btn_import": "🔐 Importar Wallet",
        "btn_manage": "💳 Gerenciar Wallet",
        "btn_buy_sell": "💰 Comprar/Vender",
        "btn_copy": "👥 Copy Trading",
        "btn_portfolio": "🏦 Portfólio",
        "btn_limit": "📌 Ordem Limitada",
        "btn_settings": "⚙️ Configurações",
        "btn_language": "🌐 Idioma",
        "btn_refer": "🏆 Indicar",
        "btn_help": "📖 Ajuda",
        "btn_back": "⬅️ Voltar ao menu",
        "wallet": "Wallet",
        "address": "Endereço",
        "balance": "Saldo",
        "referral": "Indicação",
        "invite": "Convide amigos e ganhe recompensas",
        "getting_started": "Começando",
        "send_token": "Envie um endereço de contrato token para começar.",
        "follow": "Siga as contas oficiais para atualizações e suporte.",
        "solana": "Solana",
        "unknown_token": "Token desconhecido",
        "dex": "DEX",
        "market_cap": "Valor de mercado",
        "price": "Preço",
        "liquidity": "Liquidez",
        "tax": "Taxa",
        "no_wallet": "Você ainda não configurou uma wallet",
        "access_details": "Para acessar detalhes do token, importe sua wallet primeiro",
        "enter_contract": "Digite o endereço do contrato token:",
        "scan_failed": "Não foi possível carregar os dados do token.",
        "step1": "🔐 <b>Importar Wallet - Etapa 1 de 2</b>\n\nQual nome você quer dar a esta wallet?\n\nApenas letras e números.\n<i>Por exemplo: \"MainWallet\" ou \"Wallet123\".</i>",
        "invalid_wallet_name": "⚠️ Use apenas letras e números.\nExemplo: \"MainWallet\" ou \"Wallet123\".",
        "step2": "🔐 <b>Importar Wallet - Etapa 2 de 2</b>\n\nA importação de wallet está desativada nesta versão de teste.\n\n⚠️ <b>Não cole sua chave privada ou frase de recuperação aqui.</b>\n\nEsta tela é apenas um placeholder.",
        "import_failed": "❌ Importação falhou!\n\n⚠️ Erro: <i>A importação de wallet está desativada nesta versão de teste.</i>",
        "manage_wallet": "💳 <b>Gerenciar Wallet</b>\n\nNenhuma wallet conectada.\n\nImporte ou crie uma wallet para continuar.",
        "buy_sell": "💰 <b>Comprar/Vender</b>\n\nDigite o endereço do contrato token:",
        "copy_trading": "👥 <b>Copy Trading</b>\n\nCopy trading ainda não está ativo.\n\nEm breve você poderá seguir wallets selecionadas.",
        "portfolio": "🏦 <b>Portfólio</b>\n\nWallet: —\nSaldo: —\nTokens: —\n\nImporte ou conecte uma wallet primeiro.",
        "limit_order": "📌 <b>Ordem Limitada</b>\n\nOrdens limitadas ainda não estão ativas.\n\nEste menu já está preparado para a próxima versão.",
        "settings": "⚙️ <b>Configurações</b>\n\nSlippage: —\nGas/Priority Fee: —\nProteção MEV: —\n\nConfigurações serão adicionadas depois.",
        "language_title": "🌐 <b>Idioma</b>\n\nEscolha seu idioma:",
        "language_saved": "✅ Idioma salvo.",
        "language_alert": "Idioma salvo",
        "refer_text": "🏆 <b>Indicar</b>\n\nSeu link de indicação:\n{link}\n\nConvide amigos e ganhe recompensas.",
        "help": "📖 <b>Ajuda</b>\n\n1. Envie um endereço de contrato Solana.\n2. O bot mostra informações do token.\n3. Funções de wallet serão adicionadas depois.\n\nSuporte: your-support@email.com",
        "unknown_feature": "Esta função ainda não está disponível.",
    },
    "tr": {
        "btn_import": "🔐 Wallet İçe Aktar",
        "btn_manage": "💳 Wallet Yönet",
        "btn_buy_sell": "💰 Al/Sat",
        "btn_copy": "👥 Copy Trading",
        "btn_portfolio": "🏦 Portföy",
        "btn_limit": "📌 Limit Emir",
        "btn_settings": "⚙️ Ayarlar",
        "btn_language": "🌐 Dil",
        "btn_refer": "🏆 Davet Et",
        "btn_help": "📖 Yardım",
        "btn_back": "⬅️ Menüye Dön",
        "wallet": "Wallet",
        "address": "Adres",
        "balance": "Bakiye",
        "referral": "Referans",
        "invite": "Arkadaşlarını davet et ve ödül kazan",
        "getting_started": "Başlangıç",
        "send_token": "Başlamak için token kontrat adresi gönder.",
        "follow": "Güncellemeler ve destek için resmi hesapları takip et.",
        "solana": "Solana",
        "unknown_token": "Bilinmeyen Token",
        "dex": "DEX",
        "market_cap": "Piyasa Değeri",
        "price": "Fiyat",
        "liquidity": "Likidite",
        "tax": "Vergi",
        "no_wallet": "Henüz wallet kurmadın",
        "access_details": "Token detaylarına erişmek için önce wallet içe aktar",
        "enter_contract": "Lütfen token kontrat adresini gir:",
        "scan_failed": "Token verileri yüklenemedi.",
        "step1": "🔐 <b>Wallet İçe Aktar - Adım 1/2</b>\n\nBu wallet için hangi adı kullanmak istersin?\n\nSadece harf ve rakam.\n<i>Örneğin: \"MainWallet\" veya \"Wallet123\".</i>",
        "invalid_wallet_name": "⚠️ Lütfen sadece harf ve rakam kullan.\nÖrnek: \"MainWallet\" veya \"Wallet123\".",
        "step2": "🔐 <b>Wallet İçe Aktar - Adım 2/2</b>\n\nWallet import bu test sürümünde devre dışı.\n\n⚠️ <b>Buraya private key veya recovery phrase yazma.</b>\n\nBu ekran sadece wallet import akışı için placeholder.",
        "import_failed": "❌ Import başarısız!\n\n⚠️ Hata: <i>Wallet import bu test sürümünde devre dışı.</i>",
        "manage_wallet": "💳 <b>Wallet Yönet</b>\n\nHenüz bağlı wallet yok.\n\nDevam etmek için wallet import et veya oluştur.",
        "buy_sell": "💰 <b>Al/Sat</b>\n\nLütfen token kontrat adresini gir:",
        "copy_trading": "👥 <b>Copy Trading</b>\n\nCopy trading henüz aktif değil.\n\nYakında seçili walletları takip edebileceksin.",
        "portfolio": "🏦 <b>Portföy</b>\n\nWallet: —\nBakiye: —\nTokenlar: —\n\nLütfen önce wallet import et veya bağla.",
        "limit_order": "📌 <b>Limit Emir</b>\n\nLimit emirler henüz aktif değil.\n\nBu menü sonraki sürüm için hazırlandı.",
        "settings": "⚙️ <b>Ayarlar</b>\n\nSlippage: —\nGas/Priority Fee: —\nMEV Koruması: —\n\nAyarlar sonraki sürümde eklenecek.",
        "language_title": "🌐 <b>Dil</b>\n\nDilini seç:",
        "language_saved": "✅ Dil kaydedildi.",
        "language_alert": "Dil kaydedildi",
        "refer_text": "🏆 <b>Davet Et</b>\n\nReferans linkin:\n{link}\n\nArkadaşlarını davet et ve ödül kazan.",
        "help": "📖 <b>Yardım</b>\n\n1. Solana token kontrat adresi gönder.\n2. Bot token bilgilerini gösterir.\n3. Wallet özellikleri daha sonra eklenecek.\n\nDestek: your-support@email.com",
        "unknown_feature": "Bu özellik henüz mevcut değil.",
    },
}


def get_lang(chat_id) -> str:
    return USER_LANG.get(chat_id, "en")


def t(lang: str, key: str) -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))


def get_ref_code(user) -> str:
    if user and user.username:
        username = re.sub(r"[^A-Za-z0-9_]", "", user.username)
        return f"ref_{username}"

    user_id = user.id if user else "unknown"
    return f"ref_id{user_id}"


def get_ref_link(user) -> str:
    ref_code = get_ref_code(user)
    return f"https://t.me/{BOT_USERNAME}?start={ref_code}"


def main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "btn_import"), callback_data="import_wallet"),
                InlineKeyboardButton(text=t(lang, "btn_manage"), callback_data="manage_wallet"),
            ],
            [
                InlineKeyboardButton(text=t(lang, "btn_buy_sell"), callback_data="buy_sell"),
                InlineKeyboardButton(text=t(lang, "btn_copy"), callback_data="copy_trading"),
            ],
            [
                InlineKeyboardButton(text=t(lang, "btn_portfolio"), callback_data="portfolio"),
                InlineKeyboardButton(text=t(lang, "btn_limit"), callback_data="limit_order"),
            ],
            [
                InlineKeyboardButton(text=t(lang, "btn_settings"), callback_data="settings"),
                InlineKeyboardButton(text=t(lang, "btn_language"), callback_data="language"),
            ],
            [
                InlineKeyboardButton(text=t(lang, "btn_refer"), callback_data="refer"),
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
            [InlineKeyboardButton(text=t(lang, "btn_import"), callback_data="import_wallet")]
        ]
    )


def language_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
                InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="lang_de"),
            ],
            [
                InlineKeyboardButton(text="🇫🇷 Français", callback_data="lang_fr"),
                InlineKeyboardButton(text="🇪🇸 Español", callback_data="lang_es"),
            ],
            [
                InlineKeyboardButton(text="🇵🇹 Português", callback_data="lang_pt"),
                InlineKeyboardButton(text="🇹🇷 Türkçe", callback_data="lang_tr"),
            ],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back_to_menu")],
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


async def fetch_token_data(address: str):
    url = f"https://api.dexscreener.com/token-pairs/v1/solana/{address}"

    try:
        timeout = ClientTimeout(total=10)

        async with ClientSession(timeout=timeout) as session:
            async with session.get(url, headers={"User-Agent": "TelegramMenuBot/1.0"}) as response:
                if response.status != 200:
                    return None

                data = await response.json()

        if not isinstance(data, list) or not data:
            return None

        pairs = [pair for pair in data if pair.get("chainId") == "solana"]
        if not pairs:
            pairs = data

        best_pair = choose_best_pair(pairs)
        if not best_pair:
            return None

        base_token = best_pair.get("baseToken") or {}
        quote_token = best_pair.get("quoteToken") or {}

        if quote_token.get("address") == address:
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
            "pair_url": best_pair.get("url"),
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

    return (
        f"📌 <b>{t(lang, 'solana')}</b>\n"
        f"{html.escape(name)} · <b>${html.escape(ticker)}</b>\n"
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


@dp.callback_query(F.data == "manage_wallet")
async def manage_wallet(callback: CallbackQuery):
    lang = get_lang(callback.message.chat.id)

    await callback.answer()
    await callback.message.answer(
        t(lang, "manage_wallet"),
        parse_mode="HTML",
        reply_markup=import_wallet_keyboard(lang),
    )


@dp.callback_query(F.data == "buy_sell")
async def buy_sell(callback: CallbackQuery):
    lang = get_lang(callback.message.chat.id)

    await callback.answer()
    await callback.message.answer(
        t(lang, "buy_sell"),
        parse_mode="HTML",
        reply_markup=back_keyboard(lang),
    )


@dp.callback_query(F.data == "copy_trading")
async def copy_trading(callback: CallbackQuery):
    lang = get_lang(callback.message.chat.id)

    await callback.answer()
    await callback.message.answer(
        t(lang, "copy_trading"),
        parse_mode="HTML",
        reply_markup=back_keyboard(lang),
    )


@dp.callback_query(F.data == "portfolio")
async def portfolio(callback: CallbackQuery):
    lang = get_lang(callback.message.chat.id)

    await callback.answer()
    await callback.message.answer(
        t(lang, "portfolio"),
        parse_mode="HTML",
        reply_markup=import_wallet_keyboard(lang),
    )


@dp.callback_query(F.data == "limit_order")
async def limit_order(callback: CallbackQuery):
    lang = get_lang(callback.message.chat.id)

    await callback.answer()
    await callback.message.answer(
        t(lang, "limit_order"),
        parse_mode="HTML",
        reply_markup=back_keyboard(lang),
    )


@dp.callback_query(F.data == "settings")
async def settings(callback: CallbackQuery):
    lang = get_lang(callback.message.chat.id)

    await callback.answer()
    await callback.message.answer(
        t(lang, "settings"),
        parse_mode="HTML",
        reply_markup=back_keyboard(lang),
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


@dp.callback_query(F.data.in_({"lang_en", "lang_de", "lang_fr", "lang_es", "lang_pt", "lang_tr"}))
async def choose_language(callback: CallbackQuery):
    new_lang = callback.data.replace("lang_", "")
    USER_LANG[callback.message.chat.id] = new_lang

    await callback.answer(t(new_lang, "language_alert"))
    await callback.message.answer(
        t(new_lang, "language_saved"),
        parse_mode="HTML",
        reply_markup=back_keyboard(new_lang),
    )


@dp.callback_query(F.data == "refer")
async def refer(callback: CallbackQuery):
    lang = get_lang(callback.message.chat.id)
    referral_link = get_ref_link(callback.from_user)

    await callback.answer()
    await callback.message.answer(
        t(lang, "refer_text").format(link=html.escape(referral_link)),
        parse_mode="HTML",
        reply_markup=back_keyboard(lang),
        disable_web_page_preview=False,
    )


@dp.callback_query(F.data == "help")
async def help_handler(callback: CallbackQuery):
    lang = get_lang(callback.message.chat.id)

    await callback.answer()
    await callback.message.answer(
        t(lang, "help"),
        parse_mode="HTML",
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