import logging
from datetime import datetime
from telegram import Update, LabeledPrice
from telegram.ext import ContextTypes, PreCheckoutQueryHandler, MessageHandler, filters
from tgbot.services.users import get_user, grant_premium, deduct_credits
from tgbot.utils.keyboards import premium_kb, back_menu_kb
from tgbot.utils.messages import PREMIUM_COMPARE, PAYMENT_SUCCESS, CREDIT_UPGRADE_SUCCESS
from tgbot.config import config
from tgbot.utils.decorators import require_registered

logger = logging.getLogger(__name__)

@require_registered
async def premium_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Renders the Premium upgrade panel showing detailed tier comparisons."""
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        return

    query = update.callback_query
    
    # Check if they are already Premium
    if user.get("tier") == "premium" and user.get("premium_until"):
        expiry_raw = user["premium_until"]
        try:
            # Clean possible trailing format errors
            if " " in expiry_raw:
                expiry_dt = datetime.strptime(expiry_raw, "%Y-%m-%d %H:%M:%S")
            else:
                expiry_dt = datetime.fromisoformat(expiry_raw)
            expiry_str = expiry_dt.strftime("%d %b %Y, %H:%M")
        except Exception:
            expiry_str = expiry_raw
            
        stats_msg = (
            "⭐ <b>You are a Premium Member!</b>\n\n"
            f"⏳ <b>Expiration Date:</b> <code>{expiry_str}</code>\n"
            f"💰 <b>Your Balance:</b> <code>{user.get('credits', 0)}</code> credits\n\n"
            "All speed throttles, cap limitations, and link restrictions are completely disabled."
        )
        if query:
            await query.answer()
            await query.edit_message_text(stats_msg, parse_mode="HTML", reply_markup=back_menu_kb())
        else:
            await update.message.reply_text(stats_msg, parse_mode="HTML", reply_markup=back_menu_kb())
        return

    # User is Free - Render comparison table
    stars_price = config.stars_per_premium_day * 30
    credits_needed = 100 # Standard credit-to-premium conversion rate
    
    table_text = PREMIUM_COMPARE.format(
        stars_cost=stars_price,
        credits_cost=credits_needed
    )
    
    if query:
        await query.answer()
        await query.edit_message_text(table_text, parse_mode="HTML", reply_markup=premium_kb(stars_price, credits_needed))
    else:
        await update.message.reply_text(table_text, parse_mode="HTML", reply_markup=premium_kb(stars_price, credits_needed))

async def buy_stars_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggers the Telegram Stars checkout flow by issuing a visual Invoice."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    stars_qty = config.stars_per_premium_day * 30
    
    invoice_payload = f"premium_ref_{user_id}_30d"
    
    try:
        # For Telegram Stars (XTR), the provider_token MUST be an empty string
        await context.bot.send_invoice(
            chat_id=user_id,
            title="Premium Upgrade - 30 Days",
            description="Activate unlimited scrapes, custom short link expiries, and priority speed.",
            payload=invoice_payload,
            provider_token="", # Must be empty for Stars payments
            currency="XTR",
            prices=[LabeledPrice("Premium 30 Days", stars_qty)]
        )
    except Exception as ie:
        logger.error(f"Invoicing dispatch failed: {ie}")
        await query.message.reply_text(
            f"❌ <b>Invoicing Error!</b>\n"
            f"Failed to generate Telegram Stars invoice. Internal error log: {ie}",
            parse_mode="HTML"
        )

async def buy_credits_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Converts a threshold count of credits to a 30-day Premium membership."""
    query = update.callback_query
    user_id = update.effective_user.id
    credits_needed = 100
    
    # Fetch user account balance
    user = await get_user(user_id)
    if not user:
        await query.answer("Profile not found!", show_alert=True)
        return
        
    current_credits = user.get("credits", 0)
    if current_credits < credits_needed:
        await query.answer(
            f"❌ Deficit! You need {credits_needed} credits but only have {current_credits}.",
            show_alert=True
        )
        return
        
    # Deduct and upgrade
    deducted = await deduct_credits(user_id, credits_needed)
    if deducted:
        await grant_premium(user_id, days=30)
        await query.answer("🎉 Premium Activated!", show_alert=True)
        await query.edit_message_text(
            CREDIT_UPGRADE_SUCCESS.format(credits_spent=credits_needed),
            parse_mode="HTML",
            reply_markup=back_menu_kb()
        )
    else:
        await query.answer("❌ Transaction failed! Try again.", show_alert=True)

# --------------------------------------------------------------------------
# pre_checkout_query and successful_payment System Handlers
# --------------------------------------------------------------------------

async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Answers pre-checkout queries directly indicating validation approval."""
    pre_checkout = update.pre_checkout_query
    # Perform quick checks. Payload structure looks like: premium_ref_12345_30d
    if not pre_checkout.invoice_payload.startswith("premium_ref_"):
        await pre_checkout.answer(ok=False, error_message="Invalid transaction packet context!")
        return
        
    await pre_checkout.answer(ok=True)

async def payment_success_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback invoked after successful Star settlements."""
    user_id = update.effective_user.id
    payment_info = update.message.successful_payment
    
    logger.info(f"Payment success: User {user_id} bought premium. Charge ID: {payment_info.telegram_payment_charge_id}")
    
    # Upgrade user in DB
    await grant_premium(user_id, days=30)
    
    await update.message.reply_text(
        PAYMENT_SUCCESS,
        parse_mode="HTML",
        reply_markup=back_menu_kb()
    )
