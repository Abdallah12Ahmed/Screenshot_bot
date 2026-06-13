import os
import cv2
import numpy as np
import logging
import shutil
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8600704101:AAH06GOCcDB_ofVRkBi2WI_QJxpj5oNS2YU"


# --- 🌟 الجزء الجديد لتخطي حماية Render المجانية 🌟 ---
class WebServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is Running Successfully!")


def run_web_server():
    # Render يمرر البورت تلقائياً في البيئة، لو مش موجود نستخدم 8080 كافتراضي
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), WebServerHandler)
    logger.info(f"Fake Web Server started on port {port}")
    server.serve_forever()


# --------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to the Automated WhatsApp Chat List Cropper Bot!\n\n"
        "Send me a screenshot of your chat list, and I will instantly split "
        "each conversation into its own clean, individual image."
    )


def process_and_crop_individual_chats(image_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    img = cv2.imread(image_path)
    if img is None:
        return []

    h, w, _ = img.shape
    top_margin = int(h * 0.118)
    row_percentage = 0.093
    row_height = int(h * row_percentage)

    refined_paths = []
    file_index = 1

    for i in range(8):
        base_y_start = int(top_margin + (i * row_height))

        if i == 0:
            top_skip_padding = int(h * 0.006)
        elif i == 1:
            top_skip_padding = int(h * 0.002)
        elif i == 2:
            top_skip_padding = -int(h * 0.005)
        elif i == 3:
            top_skip_padding = -int(h * 0.010)
        elif i == 4:
            top_skip_padding = -int(h * 0.015)
        elif i == 5:
            top_skip_padding = -int(h * 0.020)
        elif i == 6:
            top_skip_padding = -int(h * 0.025)
        elif i == 7:
            top_skip_padding = -int(h * 0.030)

        y_start = base_y_start + top_skip_padding

        y_end_base = base_y_start + row_height

        if i == 0:
            current_padding = int(h * 0.005)
        elif i == 1:
            current_padding = int(h * 0.001)
        elif i == 2:
            current_padding = -int(h * 0.006)
        elif i == 3:
            current_padding = -int(h * 0.011)
        elif i == 4:
            current_padding = -int(h * 0.016)
        elif i == 5:
            current_padding = -int(h * 0.021)
        elif i == 6:
            current_padding = -int(h * 0.026)
        elif i == 7:
            current_padding = -int(h * 0.031)

        y_end_with_padding = y_end_base + current_padding

        if y_start < 0: y_start = 0
        if y_end_with_padding > h: y_end_with_padding = h

        individual_chat_slice = img[y_start:y_end_with_padding, 0:w]

        filename = f"chat_{file_index:02d}.jpg"
        filepath = os.path.join(output_dir, filename)
        cv2.imwrite(filepath, individual_chat_slice)

        refined_paths.append(filepath)
        file_index += 1

    return refined_paths


async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_message = await update.message.reply_text("📥 Screenshot received. Processing individual chat items...")
    temp_working_dir = f"workspace_{update.message.chat_id}_{update.message.message_id}"

    try:
        if not os.path.exists(temp_working_dir):
            os.makedirs(temp_working_dir)

        photo_file = await update.message.photo[-1].get_file()
        input_file_path = os.path.join(temp_working_dir, "raw_input.jpg")
        await photo_file.download_to_drive(input_file_path)

        output_slices_dir = os.path.join(temp_working_dir, "slices")
        generated_slices = process_and_crop_individual_chats(input_file_path, output_slices_dir)

        if not generated_slices:
            await status_message.edit_text("❌ Extraction failed.")
            shutil.rmtree(temp_working_dir, ignore_errors=True)
            return

        await status_message.edit_text(f"✅ Extracted {len(generated_slices)} individual items. Sending now...")

        for slice_path in sorted(generated_slices):
            if os.path.exists(slice_path):
                with open(slice_path, 'rb') as chat_img:
                    await update.message.reply_photo(photo=chat_img)

        await status_message.delete()

    except Exception as e:
        logger.error(f"Execution handling error: {e}")
        await status_message.edit_text("⚠️ An error occurred while parsing the chat rows.")
    finally:
        if os.path.exists(temp_working_dir):
            shutil.rmtree(temp_working_dir, ignore_errors=True)


def main():
    # 🌟 تشغيل سيرفر الويب الوهمي في Thread مستقل حتى لا يعطل البوت
    threading.Thread(target=run_web_server, daemon=True).start()

    # تشغيل البوت الطبيعي
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))

    print("🤖 Production-ready Bot with Fake Webserver is running...")
    application.run_polling()


if __name__ == '__main__':
    main()
