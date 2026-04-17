import re
from typing import Tuple, Optional

class SpamFilter:
    # Запрещенные паттерны
    PATTERNS = {
        'repeated_chars': re.compile(r'(.)\1{10,}'),  # аааааааааа
        'url_shorteners': re.compile(r'(bit\.ly|goo\.gl|tinyurl|ow\.ly)'),
        'phone_numbers': re.compile(r'(\+7|8)[\s-]?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}'),
        'emails': re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
    }
    
    # Стоп-слова (спам)
    STOP_WORDS = [
    'идиот', 'дурак', 'тупой', 'дебил', 'кретин', 'придурок',
    'урод', 'ублюдок', 'сволочь', 'мразь', 'тварь', 'гнида',
    'ничтожество', 'нищий', 'бомж', 'алкаш', 'наркоман',
    'жирный', 'толстый', 'уродина', 'страшный', 'косой', 'рыжий',
    'хуй', 'пизда', 'ебать', 'блядь', 'блять', 'сука', 'нахер', 'заебал',
    'пидор', 'пидорас', 'гандон', 'мудак', 'уебок', 'долбоеб',
    'хуев', 'хуёв', 'хуево', 'пиздец', 'ебан', 'еблан', 'уебан',
    'заебало', 'пиздатый', 'хуйня', 'ебанутый', 'выебон'
]

    
    @classmethod
    def check(cls, text: str) -> Tuple[bool, Optional[str]]:
        """
        Проверка текста на спам
        Returns: (is_spam, reason)
        """
        text_lower = text.lower()
        
        # 1. Проверка на повторяющиеся символы
        if cls.PATTERNS['repeated_chars'].search(text):
            return True, "Обнаружены повторяющиеся символы"
        
        # 2. Проверка на ссылки-сокращатели
        if cls.PATTERNS['url_shorteners'].search(text_lower):
            return True, "Запрещены сокращенные ссылки"
        
        # 3. Проверка на телефоны (если не разрешены)
        if cls.PATTERNS['phone_numbers'].search(text):
            return True, "Номера телефонов запрещены"
        
        # 4. Проверка на email
        if cls.PATTERNS['emails'].search(text):
            return True, "Email адреса запрещены"
        
        # 5. Проверка на стоп-слова
        for word in cls.STOP_WORDS:
            if word in text_lower:
                return True, f"Обнаружено запрещенное слово: {word}"
        
        # 6. Проверка на КАПС (более 50% заглавных)
        if len(text) > 20:
            upper_count = sum(1 for c in text if c.isupper())
            if upper_count / len(text) > 0.5:
                return True, "Слишком много заглавных букв"
        
        # 7. Проверка на количество ссылок
        urls = re.findall(r'https?://[^\s]+', text_lower)
        if len(urls) > 2:
            return True, "Слишком много ссылок"
        
        return False, None