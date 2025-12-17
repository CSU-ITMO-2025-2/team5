import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Загружаем переменные окружения
OPENAI_API_KEY = os.getenv("API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.proxyapi.ru/openai/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")


def test_openai_connection():
    """Проверка подключения к OpenAI API"""
    if not OPENAI_API_KEY:
        print("❌ API_KEY не установлен в переменных окружения")
        return False

    try:
        # Инициализируем клиент
        client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
        )

        # Простой тестовый запрос
        response = client.responses.create(
            model=OPENAI_MODEL,
            input="Напиши `работает`",
        )

        # Извлекаем текст ответа
        text = (
            response.output[0].content[0].text
            if hasattr(response, "output")
            else str(response)
        )

        print(f"✅ Подключение успешно!")
        print(f"📝 Ответ от OpenAI: {text}")
        print(f"🌐 Используемый URL: {OPENAI_BASE_URL}")
        print(f"🤖 Модель: {OPENAI_MODEL}")

        return True

    except Exception as e:
        print(f"❌ Ошибка подключения: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    print("🔍 Тестируем подключение к OpenAI...")
    test_openai_connection()
