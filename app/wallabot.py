import asyncio
import requests
import json
import urllib.parse
import uuid
from aiogram import types, Dispatcher, Bot
from aiogram.filters import Command
from api_token import TOKEN

bot = Bot(token=TOKEN)
dp = Dispatcher()


def load_data():
    try:
        with open('products.json', 'r') as f:
            data = json.load(f)
        print("Loaded data:", data)  # Debug print
        return data
    except FileNotFoundError:
        print("products.json file not found.")
        return {'user_products': {}, 'posted_products': {}, 'notified_no_results': {}}
    except json.JSONDecodeError:
        print("Error decoding JSON from products.json.")
        return {'user_products': {}, 'posted_products': {}, 'notified_no_results': {}}


data = load_data()
user_products = data.get('user_products', {})
posted_products = data.get('posted_products', {})
notified_no_results = data.get('notified_no_results', {})  # New dictionary to track notifications


def empty_data():
    try:
        with open('products.json', 'w') as f:
            json.dump({'user_products': {}, 'posted_products': {}, 'notified_no_results': {}}, f)
            user_products.clear()
            posted_products.clear()
            notified_no_results.clear()
        print("products.json file emptied successfully.")
    except Exception as e:
        print(f"Error emptying products.json file: {e}")


def save_data(data):
    try:
        with open('products.json', 'w') as f:
            json.dump(data, f)
        print("Data saved successfully to products.json")
    except Exception as e:
        print(f"Error saving data to products.json: {e}")


data = load_data()
print("Data after loading:", data)
user_products = data['user_products']
posted_products = data['posted_products']
notified_no_results = data.get('notified_no_results', {})


@dp.message(Command('add'))
async def handle_add(message: types.Message):
    global user_products, posted_products, notified_no_results
    chat_id = str(message.chat.id)
    if chat_id not in user_products:
        user_products[chat_id] = {}
        posted_products[chat_id] = {}
        notified_no_results[chat_id] = {}
    await message.reply(
        "Please enter the product name, minimum price, and maximum price separated by commas (e.g., 'iPhone,100,500').")


@dp.message(Command('ls'))
async def list_products(message: types.Message):
    try:
        with open('products.json', 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print("products.json file not found.")
        await message.reply("No products have been added yet.")
        return
    except json.JSONDecodeError:
        print("Error decoding JSON from products.json.")
        await message.reply("An error occurred while reading the products data.")
        return

    chat_id = str(message.chat.id)

    if chat_id in data["user_products"]:
        products = set()
        for product_id, product_data in data["user_products"][chat_id].items():
            product = product_data["product"]
            min_price = product_data["min_price"]
            max_price = product_data["max_price"]
            products.add(f"{product} price: {min_price} - {max_price}")

        product_list = "\n".join(f"{i}. {product}" for i, product in enumerate(products, start=1))
        await message.reply(f"All products:\n{product_list}")
    else:
        await message.reply("No products have been added yet.")


@dp.message(Command('rm'))
async def handle_rm(message: types.Message):
    empty_data()
    await message.reply("products.json file has been emptied.")


@dp.message()
async def process_product_info(message: types.Message):
    global user_products, posted_products, notified_no_results
    chat_id = str(message.chat.id)
    try:
        product, min_price, max_price = message.text.split(',')
        product_id = str(uuid.uuid4())
        data = load_data()
        user_products = data['user_products']
        posted_products = data['posted_products']
        notified_no_results = data.get('notified_no_results', {})

        if chat_id in user_products:
            user_products[chat_id][product_id] = {
                'id': product_id,
                'product': product.strip(),
                'min_price': min_price.strip(),
                'max_price': max_price.strip()
            }
        else:
            user_products[chat_id] = {
                product_id: {
                    'id': product_id,
                    'product': product.strip(),
                    'min_price': min_price.strip(),
                    'max_price': max_price.strip()
                }
            }
            posted_products[chat_id] = {}
            notified_no_results[chat_id] = {}

        await search_products(chat_id)

        data = {'user_products': user_products, 'posted_products': posted_products,
                'notified_no_results': notified_no_results}
        save_data(data)
    except ValueError:
        await message.reply(
            "Invalid input format. Please try again and separate the product name, minimum price, and maximum price with commas.")


async def search_products(chat_id):
    global user_products, posted_products, notified_no_results
    for product_id, product_info in user_products[chat_id].items():
        product = product_info['product'].lower()
        product_name = product.split()
        min_price = product_info['min_price']
        max_price = product_info['max_price']
        product_id = product_info['id']
        encoded_product = urllib.parse.quote(product)
        api_url = f'https://api.wallapop.com/api/v3/general/search?keywords={encoded_product}&min_price={min_price}&max_price={max_price}'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-DeviceOS': '0'
        }
        print(f"API URL: {api_url}")
        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            matching_objects = data['search_objects']

            if matching_objects:
                # If we find results for a product that previously had none, remove it from notified_no_results
                if chat_id in notified_no_results and product_id in notified_no_results[chat_id]:
                    del notified_no_results[chat_id][product_id]

                if product_id not in posted_products[chat_id]:
                    posted_products[chat_id][product_id] = []
                for obj in matching_objects:
                    product_url = f"https://es.wallapop.com/item/{obj['web_slug']}"
                    if product_url not in posted_products[chat_id][product_id]:
                        if all(word in obj['title'].lower() for word in product_name) or all(
                                word in obj['description'].lower() for word in product_name):
                            if float(min_price) <= obj['price'] <= float(max_price):
                                product_message = f"***{obj['title']}***\n{product_url}\n****{obj['price']} €****"
                                await bot.send_message(chat_id=chat_id, text=product_message, parse_mode='Markdown')
                                posted_products[chat_id][product_id].append(product_url)
            else:
                # Only send the "no results" message if we haven't sent it before for this product
                if chat_id not in notified_no_results:
                    notified_no_results[chat_id] = {}

                if product_id not in notified_no_results[chat_id]:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"Sorry, no matching products were found for '{product}'. You will be notified when new products are found."
                    )
                    notified_no_results[chat_id][product_id] = True

        except requests.RequestException as e:
            await bot.send_message(chat_id=chat_id, text=f"Error fetching data for '{product}': {e}")

    data = {'user_products': user_products, 'posted_products': posted_products,
            'notified_no_results': notified_no_results}
    save_data(data)


async def periodic_fetch(interval=180):
    while True:
        for chat_id in user_products:
            await search_products(chat_id)
        await asyncio.sleep(interval)


async def main() -> None:
    """Entry point"""
    fetch_task = asyncio.create_task(periodic_fetch())
    try:
        await dp.start_polling(bot)
    finally:
        fetch_task.cancel()
        await fetch_task


if __name__ == "__main__":
    asyncio.run(main())