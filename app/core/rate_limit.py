from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import HTTPException, Request

<<<<<<< HEAD
class RateLimiter:
    def __init__(self, max_requests: int = 5, window_seconds: int = 86400):
        self.max_requests = max_requests  # макс запросов
        self.window = window_seconds  # за период (сек)
=======
from app.core.config import settings


class RateLimiter:
    def __init__(self, max_requests: int = None, window_seconds: int = None):
        # Magic number extracted to config for environment flexibility
        self.max_requests = max_requests if max_requests is not None else settings.MAX_REQUESTS
        self.window = window_seconds if window_seconds is not None else settings.RATE_LIMIT_WINDOW_SECONDS
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
        self.requests = defaultdict(list)  # user_id -> [timestamps]
    
    def check(self, user_id: int) -> bool:
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window)
        
        # Очищаем старые записи
        self.requests[user_id] = [
            ts for ts in self.requests[user_id] 
            if ts > cutoff
        ]
        
        # Проверяем лимит
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        # Добавляем новый запрос
        self.requests[user_id].append(now)
        return True

<<<<<<< HEAD
rate_limiter = RateLimiter(max_requests=5, window_seconds=86400)
=======

rate_limiter = RateLimiter()
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
