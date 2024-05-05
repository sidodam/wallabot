import requests
import json
import telebot
import time
import os
from dotenv import load_dotenv
import urllib.parse

load_dotenv()
# Replace with your Telegram bot token
BOT_TOKEN = os.getenv('BOT_TOKENN')
print(BOT_TOKEN)

bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=['start'])
def start(message):
    welcome_message = "Welcome to the Wallapop product search bot!\n\n"
    welcome_message += "To get started, please enter the product you'd like to search for."
    bot.send_message(chat_id=message.chat.id, text=welcome_message)
    bot.register_next_step_handler(message, get_product)


def get_product(message):
    product = message.text
    bot.send_message(chat_id=message.chat.id,
                     text=f"Okay, you're looking for '{product}'. Please enter the minimum price you're willing to pay.")
    bot.register_next_step_handler(message, get_min_price, product)


def get_min_price(message, product):
    min_price = message.text
    bot.send_message(chat_id=message.chat.id,
                     text=f"Great, the minimum price is {min_price}. Now, please enter the maximum price you're willing to pay.")
    bot.register_next_step_handler(message, get_max_price, product, min_price)


def get_max_price(message, product, min_price):
    max_price = message.text
    # URL-encode the product name
    encoded_product = urllib.parse.quote(product)
    api_url = f'https://api.wallapop.com/api/v3/general/search?keywords={encoded_product}&min_price={min_price}&max_price={max_price}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    print(f"API URL: {api_url}")
    response = requests.get(api_url, headers=headers)
    data = json.loads(response.text)
    #print(f"API Response Data: {data}")
    matching_objects = data['search_objects']

    if matching_objects:
        for obj in matching_objects:
            product_message = f"***{obj['title']}***\nhttps://es.wallapop.com/item/{obj['web_slug']}\n****{obj['price']} €****"
            bot.send_message(chat_id=message.chat.id, text=product_message, parse_mode='Markdown')
    else:
        bot.send_message(chat_id=message.chat.id, text="Sorry, no matching products were found.")

    bot.send_message(chat_id=message.chat.id,
                     text="Would you like to search for another product? Just send the /start command.")


def main():
    bot.polling()


if __name__ == '__main__':
    main()