import requests
import json
import telebot
import time
import os
from dotenv import load_dotenv
import urllib.parse
from threading import Thread
import uuid

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKENN')
bot = telebot.TeleBot(BOT_TOKEN)

user_products = {}
posted_products = {}  #set object does not support item assignment

@bot.message_handler(commands=['add'])
def add_product(message):
    global user_products, posted_products
    if message.chat.id not in user_products:
        user_products[message.chat.id] = []
        posted_products[message.chat.id] = {}
    bot.send_message(chat_id=message.chat.id, text=" Please enter the product name.")
    bot.register_next_step_handler(message, get_product)


def get_product(message):
    global user_products
    product = message.text
    product_id = str(uuid.uuid4())
    user_products[message.chat.id].append({
        'id': product_id,
        'index': len(user_products[message.chat.id]),
        'product': product,
        'min_price': None,
        'max_price': None
    })
    bot.send_message(chat_id=message.chat.id,
                     text=f"You're looking for '{product}'. Please enter the minimum price you're willing to pay.")
    bot.register_next_step_handler(message, get_min_price, product_id)


def get_min_price(message, product_id):
    global user_products
    min_price = message.text
    for product_info in user_products[message.chat.id]:
        if product_info['id'] == product_id:
            product_info['min_price'] = min_price
            break
    bot.send_message(chat_id=message.chat.id,
                     text=f"Great, the minimum price is {min_price}. Now, please enter the maximum price you're willing to pay.")
    bot.register_next_step_handler(message, get_max_price, product_id)

def get_max_price(message, product_id):
    global user_products
    max_price = message.text
    for product_info in user_products[message.chat.id]:
        if product_info['id'] == product_id:
            product_info['max_price'] = max_price
            break
    bot.send_message(chat_id=message.chat.id, text="Okay, let me see what I can find.")
    search_products(message.chat.id)

def search_products(chat_id):
    global user_products, posted_products
    for product_info in user_products[chat_id]:
        product = product_info['product'].lower()
        product_name = product.split()
        min_price = product_info['min_price']
        max_price = product_info['max_price']
        product_id = product_info['id']
        product_index = product_info['index']

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
            if product_id not in posted_products[chat_id]:
                posted_products[chat_id][product_id] = []
            for obj in matching_objects:
                product_url = f"https://es.wallapop.com/item/{obj['web_slug']}"
                if product_url not in posted_products[chat_id][product_id]:
                    if all(word in obj['title'].lower() for word in product_name) or all(word in obj['description'].lower() for word in product_name): # for a richer output
                        if float(min_price) <= obj['price'] <= float(max_price):
                            product_message = f"***{obj['title']}***\n{product_url}\n****{obj['price']} €****\n(Index: {product_index})"
                            bot.send_message(chat_id=chat_id, text=product_message, parse_mode='Markdown')
                            posted_products[chat_id][product_id].append(product_url)
        else:
            bot.send_message(chat_id=chat_id, text=f"Sorry, no matching products were found for '{product}'.")


@bot.message_handler(commands=['ls'])
def show_products(message):
    global user_products
    if message.chat.id in user_products and user_products[message.chat.id]:
        product_list = "Currently tracked products:\n\n"
        for product_info in user_products[message.chat.id]:
            product_list += f"- {product_info['product']} (min price: {product_info['min_price']}, max price: {product_info['max_price']}, Index: {product_info['index']})\n"
        bot.send_message(chat_id=message.chat.id, text=product_list)
        print('user_products', user_products)
        print('posted_products', posted_products)
    else:
        bot.send_message(chat_id=message.chat.id, text="You are not currently tracking any products.")

@bot.message_handler(commands=['rm'])
def remove_product(message):
    global user_products, posted_products
    if message.chat.id in user_products and user_products[message.chat.id]:
        product_list = "Currently tracked products:\n\n"
        for product_info in user_products[message.chat.id]:
            product_list += f"- {product_info['product']} (Index: {product_info['index']})\n"
        bot.send_message(chat_id=message.chat.id, text=product_list)
        bot.send_message(chat_id=message.chat.id, text="Please enter the index of the product you want to remove.")
        bot.register_next_step_handler(message, delete_product)
    else:
        bot.send_message(chat_id=message.chat.id, text="You are not currently tracking any products.")

def delete_product(message):
    global user_products, posted_products
    chat_id = message.chat.id
    try:
        index_to_remove = int(message.text)
        if index_to_remove >= 0 and index_to_remove < len(user_products[chat_id]):
            product_to_remove = user_products[chat_id][index_to_remove]
            product_id = product_to_remove['id']
            del user_products[chat_id][index_to_remove]
            del posted_products[chat_id][product_id]
            bot.send_message(chat_id=chat_id, text=f"Removed product '{product_to_remove['product']}' from your tracked products.")
        else:
            bot.send_message(chat_id=chat_id, text="Invalid index. Please try again.")
    except (ValueError, IndexError):
        bot.send_message(chat_id=chat_id, text="Invalid index. Please try again.")

def check_for_new_products():
    global user_products, posted_products
    while True:
        for chat_id, products in user_products.items():
            search_products(chat_id)
        time.sleep(80)

def main():
    product_checker = Thread(target=check_for_new_products)
    product_checker.start()
    bot.polling(none_stop=True)

if __name__ == '__main__':
    main()