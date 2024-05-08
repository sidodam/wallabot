import requests
import json
import telebot
import time
import os
from dotenv import load_dotenv
import urllib.parse
from threading import Thread

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKENN')
bot = telebot.TeleBot(BOT_TOKEN)

user_products = {}
posted_products = {}

@bot.message_handler(commands=['add'])
def add_product(message):
    global user_products, posted_products
    if message.chat.id not in user_products:
        user_products[message.chat.id] = []
        posted_products[message.chat.id] = set()
    bot.send_message(chat_id=message.chat.id, text=" Please enter the product name.")
    bot.register_next_step_handler(message, get_product)

def get_product(message):
    global user_products
    product = message.text
    user_products[message.chat.id].append({
        'product': product,
        'min_price': None,
        'max_price': None
    })
    bot.send_message(chat_id=message.chat.id,
                     text=f"Okay, you're looking for '{product}'. Please enter the minimum price you're willing to pay.")
    bot.register_next_step_handler(message, get_min_price)

def get_min_price(message):
    global user_products
    min_price = message.text
    user_products[message.chat.id][-1]['min_price'] = min_price
    bot.send_message(chat_id=message.chat.id,
                     text=f"Great, the minimum price is {min_price}. Now, please enter the maximum price you're willing to pay.")
    bot.register_next_step_handler(message, get_max_price)

def get_max_price(message):
    global user_products
    max_price = message.text
    user_products[message.chat.id][-1]['max_price'] = max_price
    bot.send_message(chat_id=message.chat.id, text="Okay, let me search for products that match your criteria.")
    search_products(message.chat.id)

def search_products(chat_id):
    global user_products, posted_products
    for product_info in user_products[chat_id]:
        product = product_info['product']
        min_price = product_info['min_price']
        max_price = product_info['max_price']
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
        matching_objects = data['search_objects']

        if matching_objects:
            for obj in matching_objects:
                product_url = f"https://es.wallapop.com/item/{obj['web_slug']}"
                if product_url not in posted_products[chat_id]:
                    product_message = f"***{obj['title']}***\n{product_url}\n****{obj['price']} €****"
                    bot.send_message(chat_id=chat_id, text=product_message, parse_mode='Markdown')
                    posted_products[chat_id].add(product_url)
        else:
            bot.send_message(chat_id=chat_id, text=f"Sorry, no matching products were found for '{product}'.")

def check_for_new_products():
    global user_products, posted_products
    while True:
        for chat_id, products in user_products.items():
            search_products(chat_id)
        time.sleep(120)  # Wait for 2 minutes before checking again

@bot.message_handler(commands=['products'])
def show_products(message):
    global user_products
    if message.chat.id in user_products and user_products[message.chat.id]:
        product_list = "Currently tracked products:\n\n"
        for product_info in user_products[message.chat.id]:
            product_list += f"- {product_info['product']} (min price: {product_info['min_price']}, max price: {product_info['max_price']})\n"
        bot.send_message(chat_id=message.chat.id, text=product_list)
    else:
        bot.send_message(chat_id=message.chat.id, text="You are not currently tracking any products.")

def main():
    product_checker = Thread(target=check_for_new_products)
    product_checker.start()
    bot.polling(none_stop=True)

if __name__ == '__main__':
    main()