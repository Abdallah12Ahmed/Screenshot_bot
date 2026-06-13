import os
import cv2
import numpy as np
import logging
import shutil
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Logging setup to monitor the bot
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔴 Insert your Bot Token from BotFather here
TOKEN = "8600704101:AAH06GOCcDB_ofVRkBi2WI_QJxpj5oNS2YU"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Welcome message when the bot is started """
    await update.message.reply_text(
        "Welcome to the Automated WhatsApp Chat List Cropper Bot!\n\n"
        "Send me a screenshot of your chat list, and I will instantly split "
        "each conversation into its own clean, individual image."
    )


def process_and_crop_individual_chats(image_path, output_dir):
    """
    Complete calibrated Shift-Up slicing for all 8 chats.
    Dynamically shifts the window higher for chats 5, 6, 7, and 8 to reveal top data and cut bottom data.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # قراءة الصورة الأصلية
    img = cv2.imread(image_path)
    if img is None:
        return []

    h, w, _ = img.shape

    # 📌 نقطة البداية القياسية الثابتة للشات الأول (مظبوطة)
    top_margin = int(h * 0.118)

    # الارتفاع المرجعي
    row_percentage = 0.093
    row_height = int(h * row_percentage)

    refined_paths = []
    file_index = 1

    for i in range(8):
        # حساب النقطة المرجعية الثابتة رياضياً لكل خطوة لمنع الترحيل التراكمي
        base_y_start = int(top_margin + (i * row_height))

        # 🌟 ضبط خطوات البداية من فوق (إزاحة لأعلى لإظهار داتا من بكسلات قبلها)
        if i == 0:  # صورة 1
            top_skip_padding = int(h * 0.006)
        elif i == 1:  # صورة 2
            top_skip_padding = int(h * 0.002)
        elif i == 2:  # صورة 3
            top_skip_padding = -int(h * 0.005)
        elif i == 3:  # صورة 4
            top_skip_padding = -int(h * 0.010)
        elif i == 4:  # صورة 5 (تم سحب المقص لأعلى شويتين)
            top_skip_padding = -int(h * 0.015)
        elif i == 5:  # صورة 6 (سحب أعلى تصاعدي)
            top_skip_padding = -int(h * 0.020)
        elif i == 6:  # صورة 7 (سحب أعلى تصاعدي)
            top_skip_padding = -int(h * 0.025)
        elif i == 7:  # صورة 8 (سحب أعلى تصاعدي للأخير)
            top_skip_padding = -int(h * 0.030)

        y_start = base_y_start + top_skip_padding

        # حساب نقطة النهاية الأساسية
        y_end_base = base_y_start + row_height

        # 🌟 ضبط هوامش النهاية من تحت (سحب المقص لأعلى لحذف الداتا والتعويض الموازي)
        if i == 0:  # صورة 1
            current_padding = int(h * 0.005)
        elif i == 1:  # صورة 2
            current_padding = int(h * 0.001)
        elif i == 2:  # صورة 3
            current_padding = -int(h * 0.006)
        elif i == 3:  # صورة 4
            current_padding = -int(h * 0.011)
        elif i == 4:  # صورة 5 (تقليل وقص من الأسفل للموازنة)
            current_padding = -int(h * 0.016)
        elif i == 5:  # صورة 6
            current_padding = -int(h * 0.021)
        elif i == 6:  # صورة 7
            current_padding = -int(h * 0.026)
        elif i == 7:  # صورة 8
            current_padding = -int(h * 0.031)

        y_end_with_padding = y_end_base + current_padding

        # ضمان عدم تجاوز أبعاد الصورة الفعلية
        if y_start < 0: y_start = 0
        if y_end_with_padding > h: y_end_with_padding = h

        # تنفيذ القص الإزاحي المحكم لأعلى
        individual_chat_slice = img[y_start:y_end_with_padding, 0:w]

        filename = f"chat_{file_index:02d}.jpg"
        filepath = os.path.join(output_dir, filename)
        cv2.imwrite(filepath, individual_chat_slice)

        refined_paths.append(filepath)
        file_index += 1

    return refined_paths


async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Handles image download, executes dynamic processing, and returns clean standalone cuts """
    status_message = await update.message.reply_text("📥 Screenshot received. Processing individual chat items...")

    # Unique transactional temporary working directory
    temp_working_dir = f"workspace_{update.message.chat_id}_{update.message.message_id}"

    try:
        if not os.path.exists(temp_working_dir):
            os.makedirs(temp_working_dir)

        # Download target image structure
        photo_file = await update.message.photo[-1].get_file()
        input_file_path = os.path.join(temp_working_dir, "raw_input.jpg")
        await photo_file.download_to_drive(input_file_path)

        # Trigger processing segmentation routine
        output_slices_dir = os.path.join(temp_working_dir, "slices")
        generated_slices = process_and_crop_individual_chats(input_file_path, output_slices_dir)

        if not generated_slices:
            await status_message.edit_text(
                "❌ Extraction failed. Please ensure the screenshot captures a valid WhatsApp chat window list in Dark Mode."
            )
            shutil.rmtree(temp_working_dir, ignore_errors=True)
            return

        # Notify final step execution phase
        await status_message.edit_text(f"✅ Extracted {len(generated_slices)} individual items. Sending now...")

        # Sequential dispatch loop: delivers each extracted row independently
        for slice_path in sorted(generated_slices):
            if os.path.exists(slice_path):
                with open(slice_path, 'rb') as chat_img:
                    await update.message.reply_photo(photo=chat_img)

        # Clean-up operational notification tracking
        await status_message.delete()

    except Exception as e:
        logger.error(f"Execution handling error: {e}")
        await status_message.edit_text("⚠️ An error occurred while parsing the chat rows. Please try again.")

    finally:
        # Secure complete purge of operational caches
        if os.path.exists(temp_working_dir):
            shutil.rmtree(temp_working_dir, ignore_errors=True)


def main():
    """ Initialize framework deployment polling loop """
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))

    print("🤖 Production-ready Bot is running smoothly. Awaiting inputs...")
    application.run_polling()


if __name__ == '__main__':
    main()