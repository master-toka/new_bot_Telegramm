# config.py
BOT_TOKEN = "8574910283:AAEsWinwcwZ0vl3gy3qTMISS1wwef5x-zOs"
GROUP_ID = -1003886758989  # ID группы монтажников
ADMIN_CHAT_ID = -1003886758989  # Если отдельный чат для руководства - укажите другой ID

# Список районов (ID: название)
DISTRICTS = {
    1: "Советский",
    2: "Железнодорожный",
    3: "Октябрьский",
    4: "Иволгинский",
    5: "Тарбагатайский",
    6: "Заиграевский",
    7: "Селенгинский",
    8: "Другой"
}

# ID районов для быстрого доступа
SOVETSKY = 1
ZHELEZNODOROZHNY = 2
OKTYABRSKY = 3
IVOLGINSKY = 4
TARBAGATAYSKY = 5
ZAIGRAEVSKY = 6
SELENGINSKY = 7
OTHER = 8

# Контактные данные
COMPANY_NAME = "Мастер Тока - дарим свет своим клиентам"
DISPATCHER_PHONE = "8(3012)180054"

# Настройки времени (в секундах)
ORDER_TIMEOUT = 900  # 15 минут
MAX_ORDERS_PER_ELECTRICIAN = 3
RATE_LIMIT = 60

# Путь к базе данных
DATABASE_PATH = "electrician_bot.db"
