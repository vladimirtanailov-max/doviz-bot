import logging
import os
from typing import Dict

import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


API_URL = "https://api.exchangerate-api.com/v4/latest/EUR"
TRACKED_RATES = ("USD", "GBP", "RUB", "PLN", "TRY")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def get_rates() -> Dict[str, float]:
    """Fetch rates from API where base currency is EUR."""
    response = requests.get(API_URL, timeout=10)
    response.raise_for_status()
    data = response.json()
    rates = data.get("rates")

    if not isinstance(rates, dict):
        raise ValueError("Invalid API response: missing rates")

    return rates


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Привет! Я бот курсов валют к EUR.\n\n"
        "Доступные команды:\n"
        "/rates — курсы USD, GBP, RUB, PLN, TRY к EUR\n"
        "/usd — курс USD к EUR\n"
        "/try — курс турецкой лиры (TRY) к EUR\n"
        "/convert 100 USD EUR — конвертация суммы\n"
        "/try2eur 100 — конвертация TRY в EUR\n"
        "/eur2try 100 — конвертация EUR в TRY"
    )
    await update.message.reply_text(text)


async def rates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        all_rates = get_rates()
        lines = ["Курсы к EUR:"]
        for code in TRACKED_RATES:
            value = all_rates.get(code)
            if value is None:
                lines.append(f"{code}: нет данных")
            else:
                lines.append(f"{code}: {value:.4f}")
        await update.message.reply_text("\n".join(lines))
    except Exception as exc:
        logger.exception("Failed to load rates: %s", exc)
        await update.message.reply_text("Не удалось получить курсы. Попробуйте позже.")


async def usd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await single_currency_rate(update, "USD")


async def try_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await single_currency_rate(update, "TRY")


async def single_currency_rate(update: Update, code: str) -> None:
    try:
        all_rates = get_rates()
        value = all_rates.get(code)
        if value is None:
            await update.message.reply_text(f"Нет данных по валюте {code}.")
            return
        await update.message.reply_text(f"1 EUR = {value:.4f} {code}")
    except Exception as exc:
        logger.exception("Failed to load %s rate: %s", code, exc)
        await update.message.reply_text("Не удалось получить курс. Попробуйте позже.")


async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 3:
        await update.message.reply_text("Использование: /convert 100 USD EUR")
        return

    amount_raw, from_currency, to_currency = context.args
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    try:
        amount = float(amount_raw)
    except ValueError:
        await update.message.reply_text("Сумма должна быть числом. Пример: /convert 100 USD EUR")
        return

    try:
        all_rates = get_rates()

        if from_currency == "EUR":
            amount_in_eur = amount
        else:
            from_rate = all_rates.get(from_currency)
            if from_rate is None or from_rate == 0:
                await update.message.reply_text(f"Неизвестная валюта: {from_currency}")
                return
            amount_in_eur = amount / from_rate

        if to_currency == "EUR":
            converted = amount_in_eur
        else:
            to_rate = all_rates.get(to_currency)
            if to_rate is None:
                await update.message.reply_text(f"Неизвестная валюта: {to_currency}")
                return
            converted = amount_in_eur * to_rate

        await update.message.reply_text(
            f"{amount:.2f} {from_currency} = {converted:.4f} {to_currency}"
        )
    except Exception as exc:
        logger.exception("Failed to convert currency: %s", exc)
        await update.message.reply_text("Не удалось выполнить конвертацию. Попробуйте позже.")


async def try2eur(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.message.reply_text("Использование: /try2eur 100")
        return

    try:
        amount_try = float(context.args[0])
    except ValueError:
        await update.message.reply_text("Сумма должна быть числом. Пример: /try2eur 100")
        return

    try:
        all_rates = get_rates()
        try_rate_value = all_rates.get("TRY")
        if try_rate_value is None or try_rate_value == 0:
            await update.message.reply_text("Не удалось получить курс TRY.")
            return

        amount_eur = amount_try / try_rate_value
        await update.message.reply_text(f"{amount_try:.2f} TRY = {amount_eur:.4f} EUR")
    except Exception as exc:
        logger.exception("Failed to convert TRY to EUR: %s", exc)
        await update.message.reply_text("Не удалось выполнить конвертацию. Попробуйте позже.")


async def eur2try(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.message.reply_text("Использование: /eur2try 100")
        return

    try:
        amount_eur = float(context.args[0])
    except ValueError:
        await update.message.reply_text("Сумма должна быть числом. Пример: /eur2try 100")
        return

    try:
        all_rates = get_rates()
        try_rate_value = all_rates.get("TRY")
        if try_rate_value is None:
            await update.message.reply_text("Не удалось получить курс TRY.")
            return

        amount_try = amount_eur * try_rate_value
        await update.message.reply_text(f"{amount_eur:.2f} EUR = {amount_try:.4f} TRY")
    except Exception as exc:
        logger.exception("Failed to convert EUR to TRY: %s", exc)
        await update.message.reply_text("Не удалось выполнить конвертацию. Попробуйте позже.")


def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Environment variable BOT_TOKEN is required")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rates", rates))
    app.add_handler(CommandHandler("usd", usd))
    app.add_handler(CommandHandler("try", try_rate))
    app.add_handler(CommandHandler("convert", convert))
    app.add_handler(CommandHandler("try2eur", try2eur))
    app.add_handler(CommandHandler("eur2try", eur2try))

    app.run_polling()


if __name__ == "__main__":
    main()

