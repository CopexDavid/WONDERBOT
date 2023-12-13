import telebot
import json
import random
import time
from threading import Timer
import openai
import difflib


TOKEN = ''
bot = telebot.TeleBot(TOKEN)
openai.api_key = ''

class BotState:
    def __init__(self):
        self.stop_words = set()
        self.quiz_active = False
        self.correct_number = None
        self.participants = {}
        self.attempts = {}
        self.winning_time = {}
        self.winners = {}

bot_state = BotState()

#начало игры в снежки
players = {}
game_started = False
round_number = 0

weapon_hit_chances = {
    '/снежок': 65,
    '/лед': 35,
    '/петарда': 50,
}

used_weapons_per_player = {}
snow_per_player = {}
snow_search_used = {}

weapon_snow_cost = {
    '/снежок': 3,
    '/лед': 4,
    '/петарда': 5,
}

@bot.message_handler(commands=['snow'])
def start_snow_game(message):
    global game_started
    chat_id = message.chat.id

    if not game_started:
        game_started = True
        players[chat_id] = {}
        bot.send_message(chat_id, "НАСТУПИЛА НОЧЬ, ПОШЕЛ СНЕГОПАД, ЗАРЯЖАЙТЕ ПЕТАРДЫ И ПРИНИМАЙТЕ УЧАСТИЕ /s")
    else:
        bot.send_message(chat_id, "Игра уже идет. Чтобы присоединиться, используйте команду /s")

@bot.message_handler(commands=['s'])
def join_snow_game(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if game_started:
        if user_id not in players[chat_id]:
            players[chat_id][user_id] = {'health': 5}
            snow_per_player[chat_id] = snow_per_player.get(chat_id, {})
            snow_per_player[chat_id][user_id] = 3  # Начальное количество снега
            bot.send_message(chat_id, f"@{message.from_user.username} присоединился к игре.")
            show_game_status(chat_id)
        else:
            bot.send_message(chat_id, "Вы уже присоединились к игре.")
    else:
        bot.send_message(chat_id, "Игра еще не начата. Чтобы присоединиться, используйте команду /snow")

def show_game_status(chat_id):
    total_players = len(players.get(chat_id, {}))
    bot.send_message(chat_id, f"Всего участников: {total_players}. СНЕЖКИ НАЧАЛИСЬ!")

@bot.message_handler(commands=['snowstart'])
def start_snow_battle(message):
    global game_started, round_number
    chat_id = message.chat.id

    if game_started:
        if len(players[chat_id]) > 1:
            round_number += 1
            used_weapons_per_player[chat_id] = {}  # Очищаем использованные оружия для нового раунда
            snow_search_used[chat_id] = set()  # Очищаем использование поиска снега
            bot.send_message(chat_id, f"Раунд {round_number}: Сражение началось! Приготовьтесь к битве!")
            show_initial_health(chat_id)
            show_game_status(chat_id)
        else:
            bot.send_message(chat_id, "Для начала битвы нужно хотя бы два участника. Подключитесь командой /s")
    else:
        bot.send_message(chat_id, "Игра еще не начата. Подключитесь командой /snow")

def show_initial_health(chat_id):
    for user_id in players[chat_id]:
        bot.send_message(chat_id, f"@{get_username(chat_id, user_id)} начинает с {players[chat_id][user_id]['health']} HP и {snow_per_player[chat_id][user_id]} снега.")

def get_username(chat_id, user_id):
    user = bot.get_chat_member(chat_id, user_id).user
    return user.username if user.username else user.first_name

@bot.message_handler(commands=['снежок', 'лед', 'петарда'])
def use_weapon(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    weapon = message.text.split('@', maxsplit=1)[0].lower().strip()  # Получаем первое слово из команды

    if game_started and chat_id in players and user_id in players[chat_id]:
        if user_id not in used_weapons_per_player.get(chat_id, {}):
            target_username = message.text.split('@', maxsplit=1)[-1].strip()
            target_user_id = find_user_id_by_username(chat_id, target_username)

            if target_user_id:
                if target_user_id in players[chat_id]:
                    hit_chance = weapon_hit_chances.get(weapon, 100)
                    print(f"Используется оружие: {weapon}, Шанс попадания: {hit_chance}")
                    process_attack(chat_id, user_id, target_user_id, weapon, hit_chance)
                    used_weapons_per_player.setdefault(chat_id, {})[user_id] = weapon  # Отмечаем оружие как использованное
                    snow_cost = get_weapon_snow_cost(weapon)
                    if snow_cost <= snow_per_player[chat_id][user_id]:
                        snow_per_player[chat_id][user_id] -= snow_cost  # Уменьшаем количество снега у игрока
                        bot.send_message(chat_id, f"@{get_username(chat_id, user_id)}, вы использовали {weapon}. Осталось {snow_per_player[chat_id][user_id]} снега.")
                    else:
                        bot.send_message(chat_id, f"@{get_username(chat_id, user_id)}, не хватает снега! Попробуйте найти его с помощью команды /снег.")
                else:
                    bot.send_message(chat_id, f"@{target_username} не участвует в битве.")
            else:
                bot.send_message(chat_id, "Указанный пользователь не найден.")
        else:
            bot.send_message(chat_id, "Вы уже использовали оружие в этом раунде.")
    elif not game_started:
        bot.send_message(chat_id, "Игра еще не начата. Подключитесь командой /s")
    else:
        bot.send_message(chat_id, "Вы не участвуете в битве.")

def find_user_id_by_username(chat_id, target_username):
    for user_id, user_info in players[chat_id].items():
        username = get_username(chat_id, user_id).lower()
        if username == target_username.lower():
            return user_id
    return None

def process_attack(chat_id, attacker_id, target_id, weapon, hit_chance):
    try:
        random_value = random.randint(1, 100)

        print(f"Сгенерированное случайное значение: {random_value}, Шанс попадания: {hit_chance}")

        if random_value < hit_chance:
            damage = get_weapon_damage(weapon)
            players[chat_id][target_id]['health'] = max(0, players[chat_id][target_id]['health'] - damage)
            bot.send_message(chat_id, f"@{get_username(chat_id, attacker_id)} использовал {weapon} и попал в @{get_username(chat_id, target_id)}! Осталось {players[chat_id][target_id]['health']} HP.")
            check_game_over(chat_id)
        else:
            if weapon == '/петарда':
                # Уменьшаем здоровье атакующего при промахе петарды
                players[chat_id][attacker_id]['health'] = max(0, players[chat_id][attacker_id]['health'] - get_weapon_damage(weapon))
                bot.send_message(chat_id, f"@{get_username(chat_id, attacker_id)} использовал {weapon}, но промахнулся и погиб! Осталось {players[chat_id][attacker_id]['health']} HP.")
                check_game_over(chat_id)
            else:
                bot.send_message(chat_id, f"@{get_username(chat_id, attacker_id)} использовал {weapon}, но промахнулся!")
    except Exception as e:
        print(f"Ошибка в функции process_attack: {e}")

def get_weapon_damage(weapon):
    return {
        '/снежок': 1,
        '/лед': 2,
        '/петарда': 5,
    }.get(weapon, 0)

def get_weapon_snow_cost(weapon):
    return weapon_snow_cost.get(weapon, 0)

def check_game_over(chat_id):
    alive_players = [user_id for user_id, user_info in players[chat_id].items() if user_info['health'] > 0]
    if len(alive_players) == 1:
        winner_id = alive_players[0]
        bot.send_message(chat_id, f"@{get_username(chat_id, winner_id)} одержал победу! Игра завершена.")
        reset_game(chat_id)

def reset_game(chat_id):
    global game_started, round_number
    game_started = False
    round_number = 0
    players[chat_id] = {}

# Добавим новую команду /снег для поиска снега
@bot.message_handler(commands=['снег'])
def search_for_snow(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if game_started and chat_id in players and user_id in players[chat_id]:
        if user_id not in snow_search_used.get(chat_id, {}):
            snow_found = random.randint(1, 5)
            snow_per_player[chat_id][user_id] += snow_found  # Добавляем найденный снег игроку
            snow_search_used.setdefault(chat_id, set()).add(user_id)  # Отмечаем поиск снега как использованный
            bot.send_message(chat_id, f"@{get_username(chat_id, user_id)}, вы нашли {snow_found} снега. Теперь у вас {snow_per_player[chat_id][user_id]} снега.")
        else:
            bot.send_message(chat_id, "Вы уже использовали поиск снега в этом раунде.")
    elif not game_started:
        bot.send_message(chat_id, "Игра еще не начата. Подключитесь командой /s")
    else:
        bot.send_message(chat_id, "Вы не участвуете в битве.")
# Конец игры в снежки


@bot.message_handler(commands=['talk'])
def talk_handle(message):
    # Получаем текст из команды
    input_text = " ".join(message.text.split()[1:])

    # Взаимодействуем с GPT-3.5 Turbo
    try:
        gpt_response = openai.Completion.create(
            engine="text-davinci-003",  
            prompt=input_text,
            max_tokens=1000,  
            temperature=0.7,  
            stop=None  # Строка или список строк, указывающих, когда следует завершить генерацию
        )

        # Получаем ответ от GPT-3.5 Turbo
        gpt_response_text = gpt_response["choices"][0]["text"]

      
        bot.send_message(message.chat.id, gpt_response_text, parse_mode='HTML')
    except Exception as e:
        print(f"Error interacting with GPT: {e}")
        bot.send_message(message.chat.id, "An error occurred while processing your request.")



def save_bot_state():
    with open("bot_state.json", "w", encoding="utf-8") as file:
        state_data = {
            'stop_words': list(bot_state.stop_words),
            'quiz_active': bot_state.quiz_active,
            'correct_number': bot_state.correct_number,
            'participants': bot_state.participants,
            'attempts': bot_state.attempts,
            'winning_time': bot_state.winning_time
        }
        json.dump(state_data, file, ensure_ascii=False)

def load_bot_state():
    try:
        with open("bot_state.json", "r", encoding="utf-8") as file:
            state_data = json.load(file)
            bot_state.stop_words = set(state_data.get('stop_words', []))
            bot_state.quiz_active = state_data.get('quiz_active', False)
            bot_state.correct_number = state_data.get('correct_number', None)
            bot_state.participants = state_data.get('participants', {})
            bot_state.attempts = state_data.get('attempts', {})
            bot_state.winning_time = state_data.get('winning_time', {})
    except (json.decoder.JSONDecodeError, FileNotFoundError):
        print("Error loading 'bot_state.json'. Creating a new one with initial values.")

load_bot_state()

# Добавим переменную для отслеживания первого старта бота
first_start = True


# Список персонажей Dota 2 и позиций
dota_heroes = ["Anti-Mage", "Axe", "Bane", "Bloodseeker", "Crystal Maiden", "Drow Ranger", "Earthshaker",
                       "Juggernaut", "Mirana", "Morphling", "Shadow Fiend", "Phantom Lancer", "Puck", "Pudge", "Razor",
                       "Sand King", "Storm Spirit", "Sven", "Tiny", "Vengeful Spirit", "Windranger", "Zeus", "Kunkka",
                       "Lina", "Lion", "Shadow Shaman", "Slardar", "Tidehunter", "Witch Doctor", "Lich", "Riki",
                       "Enigma", "Tinker", "Sniper", "Necrophos", "Warlock", "Beastmaster", "Queen of Pain",
                       "Venomancer", "Faceless Void", "Wraith King", "Death Prophet", "Phantom Assassin", "Pugna",
                       "Templar Assassin", "Viper", "Luna", "Dragon Knight", "Dazzle", "Clockwerk", "Leshrac",
                       "Nature's Prophet", "Lifestealer", "Dark Seer", "Clinkz", "Omniknight", "Enchantress", "Huskar",
                       "Night Stalker", "Broodmother", "Bounty Hunter", "Weaver", "Jakiro", "Batrider", "Chen",
                       "Spectre", "Ancient Apparition", "Doom", "Ursa", "Spirit Breaker", "Gyrocopter", "Alchemist",
                       "Invoker", "Silencer", "Outworld Devourer", "Lycan", "Brewmaster", "Shadow Demon", "Lone Druid",
                       "Chaos Knight", "Meepo", "Treant Protector", "Ogre Magi", "Undying", "Rubick", "Disruptor",
                       "Nyx Assassin", "Naga Siren", "Keeper of the Light", "Io", "Visage", "Slark", "Medusa",
                       "Troll Warlord", "Centaur Warrunner", "Magnus", "Timbersaw", "Bristleback", "Tusk",
                       "Skywrath Mage", "Abaddon", "Elder Titan", "Legion Commander", "Techies", "Ember Spirit",
                       "Earth Spirit", "Underlord", "Terrorblade", "Phoenix", "Oracle", "Winter Wyvern", "Arc Warden",
                       "Monkey King", "Pangolier", "Dark Willow", "Grimstroke", "Hoodwink"]

positions = ["Carry", "Mid", "Offlane", "Support", "Hard Support"]

@bot.message_handler(commands=['', 'help'])
def send_welcome(message):
            bot.reply_to(message,
                         "Привет! Я бот, который может помочь тебе выбрать героя и позицию в Dota 2. Просто напиши /roll hero, /roll pos или /roll all.")

@bot.message_handler(commands=['roll', 'roll_hero'])
def roll_hero(message):
            random_hero = random.choice(dota_heroes)
            response = f"Тебе выпал герой: {random_hero}. Удачи в игре!"
            bot.reply_to(message, response)

@bot.message_handler(commands=['roll_pos'])
def roll_position(message):
            random_position = random.choice(positions)
            response = f"Тебе выпала позиция: {random_position}. Удачи в игре!"
            bot.reply_to(message, response)

@bot.message_handler(commands=['roll_all'])
def roll_all(message):
            random_hero = random.choice(dota_heroes)
            random_position = random.choice(positions)
            response = f"Тебе выпал герой: {random_hero}, и позиция: {random_position}. Удачи в игре!"
            bot.reply_to(message, response)
def delete_message_by_word(message, word):
    try:
        bot.delete_message(message.chat.id, message.message_id)
        username = message.from_user.username if message.from_user.username else message.from_user.first_name
        response = f"Слышь Чушпан @{username}, такие слова тут запрещены, выражайся проще чепух."
        sent_message = bot.send_message(message.chat.id, response)
        # Устанавливаем таймер на удаление своего ответа через 5 секунд
        Timer(5, delete_bot_message, args=(message.chat.id, sent_message.message_id)).start()
    except Exception as e:
        print(f"Error deleting message: {e}")

def delete_bot_message(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception as e:
        print(f"Error deleting bot message: {e}")

# Добавьте обработчик команды ./mytime
@bot.message_handler(commands=['mytime'])
def my_time_handler(message):
    user_id = message.from_user.id
    if user_id in bot_state.participants:
        elapsed_time = time.time() - bot_state.participants[user_id]
        remaining_time = max(0, 12 * 60 * 60 - elapsed_time)
        hours, remainder = divmod(remaining_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        response = f"У вас осталось {int(hours)} часов, {int(minutes)} минут, {int(seconds)} секунд до окончания прав на стоп-слова."
        bot.reply_to(message, response)
    else:
        bot.reply_to(message, "Вы не участвуете в викторине, у вас нет прав на стоп-слова.")

def save_winners():
    with open("winners.json", "w", encoding="utf-8") as file:
        json.dump(bot_state.winners, file, ensure_ascii=False)

def load_winners():
    try:
        with open("winners.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.decoder.JSONDecodeError, FileNotFoundError):
        return {}

bot_state.winners = load_winners()

@bot.message_handler(commands=['victory'])
def start_victory(message):
    global first_start
    if bot_state.quiz_active and not first_start:
        bot.reply_to(message, "Викторина уже запущена.")
    else:
        bot_state.quiz_active = True
        bot_state.correct_number = random.randint(1, 10)
        bot_state.participants = {}
        bot_state.attempts = {}
        save_bot_state()
        print(f"Бот загадал число: {bot_state.correct_number}")  # Вывод в консоль
        bot.reply_to(message, "Викторина началась! Я загадал число от 1 до 10. Угадывайте!")
        first_start = False  # После первого запуска меняем статус

#добавление слов в стоп лист
@bot.message_handler(commands=['addword'])
def add_word(message):
    words = message.text.split()[1:]
    for word in words:
        add_stop_word(word.lower())
    save_bot_state()
    bot.reply_to(message, f"Слова {', '.join(words)} добавлены в список стоп-слов.")

@bot.message_handler(commands=['delword'])
def del_word(message):
    words = message.text.split()[1:]
    for word in words:
        remove_stop_word(word.lower())
    save_bot_state()
    bot.reply_to(message, f"Слова {', '.join(words)} удалены из списка стоп-слов.")

def add_stop_word(word):
    bot_state.stop_words.add(word)

def remove_stop_word(word):
    bot_state.stop_words.discard(word)

def save_stop_words():
    with open("stop_words.json", "w", encoding="utf-8") as file:
        json.dump(list(bot_state.stop_words), file, ensure_ascii=False)

def load_stop_words():
    try:
        with open("stop_words.json", "r", encoding="utf-8") as file:
            return set(json.load(file))
    except FileNotFoundError:
        return set()

bot_state.stop_words = load_stop_words()

def has_stop_word_rights(user_id):
    if user_id in bot_state.winning_time:
        elapsed_time = time.time() - bot_state.winning_time[user_id]
        return elapsed_time < 12 * 60 * 60  # Пользователь имеет права на стоп-слова в течение 12 часов
    return False

@bot.message_handler(func=lambda message: bot_state.quiz_active)
def handle_quiz_message(message):
    user_id = message.from_user.id

    if user_id not in bot_state.participants:
        try:
            guessed_number = int(message.text)
            if guessed_number == bot_state.correct_number:
                bot.reply_to(message, "Поздравляю! Вы угадали! Теперь у вас 12 часов без ограничений.")
                bot_state.participants[user_id] = time.time() + 12 * 60 * 60
                bot_state.quiz_active = False  # Завершение викторины
                bot_state.winning_time[user_id] = time.time()  # Запоминаем время выигрыша
                bot_state.winners[user_id] = time.time()  # Запоминаем время победы
                save_bot_state()
                save_winners()  # Сохраняем информацию о победителях
            else:
                if user_id in bot_state.attempts and bot_state.attempts[user_id] == 1:
                    bot.reply_to(message, "Вы уже ответили на викторину. У вас была одна попытка.")
                else:
                    bot.reply_to(message, "Увы, вы не угадали. Попробуйте еще раз.")
                    bot_state.attempts[user_id] = 1
                bot_state.participants[user_id] = time.time()
                save_bot_state()
        except ValueError:
            pass  # Игнорируем текст, который не является числом

@bot.message_handler(func=lambda message: not bot_state.quiz_active)
def handle_non_quiz_message(message):
    user_id = message.from_user.id

    if has_stop_word_rights(user_id):
        return  # Пользователь имеет права на стоп-слова, пропускаем проверку

    text = message.text.lower()
    for word in bot_state.stop_words:
        if word in text:
            delete_message_by_word(message, word)
            break



if __name__ == "__main__":
    print("Bot started")
    bot.polling(none_stop=True)
