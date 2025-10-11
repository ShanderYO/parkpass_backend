# UzumBank Settings Configuration

## Overview

Настройки UzumBank вынесены в переменные окружения для гибкой конфигурации в разных средах (разработка, тестирование, продакшн).

## Environment Variables

### Development/Test Environment

```bash
# UzumBank Test Configuration
UZUM_TERMINAL_ID=eed1f85f-f984-4f4b-b092-fd9b569bb9e7
UZUM_API_KEY=5d9517899744b827a8f29be89ee4006759f9c87845a93c9ead9a5c1e207ff900
UZUM_BASE_URL=https://test-chk-api.uzumcheckout.uz
UZUM_CONTENT_LANGUAGE=uz-UZ
PROD=0
```

### Production Environment

```bash
# UzumBank Production Configuration
UZUM_TERMINAL_ID=your-production-terminal-id
UZUM_API_KEY=your-production-api-key
UZUM_BASE_URL=https://chk-api.uzumcheckout.uz
UZUM_CONTENT_LANGUAGE=uz-UZ
PROD=1
```

## Configuration Logic

1. **Default Values**: В `settings.py` определены значения по умолчанию для разработки и продакшна
2. **Environment Override**: Переменные окружения переопределяют значения по умолчанию
3. **Environment Detection**: Система автоматически выбирает настройки в зависимости от переменной `PROD`

## Settings Structure

```python
# Default development settings
UZUM_DEFAULT_TERMINAL_ID = "eed1f85f-f984-4f4b-b092-fd9b569bb9e7"
UZUM_DEFAULT_API_KEY = "5d9517899744b827a8f29be89ee4006759f9c87845a93c9ead9a5c1e207ff900"
UZUM_DEFAULT_BASE_URL = "https://test-chk-api.uzumcheckout.uz"
UZUM_DEFAULT_CONTENT_LANGUAGE = "uz-UZ"

# Production settings
UZUM_PROD_TERMINAL_ID = "your-prod-terminal-id"
UZUM_PROD_API_KEY = "your-prod-api-key"
UZUM_PROD_BASE_URL = "https://chk-api.uzumcheckout.uz"
UZUM_PROD_CONTENT_LANGUAGE = "uz-UZ"

# Environment-based configuration
if os.environ.get("PROD", "0") == "1":
    # Production environment
    UZUM_TERMINAL_ID = os.environ.get("UZUM_TERMINAL_ID", UZUM_PROD_TERMINAL_ID)
    UZUM_API_KEY = os.environ.get("UZUM_API_KEY", UZUM_PROD_API_KEY)
    UZUM_BASE_URL = os.environ.get("UZUM_BASE_URL", UZUM_PROD_BASE_URL)
    UZUM_CONTENT_LANGUAGE = os.environ.get("UZUM_CONTENT_LANGUAGE", UZUM_PROD_CONTENT_LANGUAGE)
else:
    # Development environment
    UZUM_TERMINAL_ID = os.environ.get("UZUM_TERMINAL_ID", UZUM_DEFAULT_TERMINAL_ID)
    UZUM_API_KEY = os.environ.get("UZUM_API_KEY", UZUM_DEFAULT_API_KEY)
    UZUM_BASE_URL = os.environ.get("UZUM_BASE_URL", UZUM_DEFAULT_BASE_URL)
    UZUM_CONTENT_LANGUAGE = os.environ.get("UZUM_CONTENT_LANGUAGE", UZUM_DEFAULT_CONTENT_LANGUAGE)
```

## Usage in Code

```python
from django.conf import settings
from payments.payment_api import UzumBankAPI

# UzumBankAPI automatically uses settings from Django settings
api = UzumBankAPI()
# api.base_url = settings.UZUM_BASE_URL
# api.api_key = settings.UZUM_API_KEY
# api.terminal_id = settings.UZUM_TERMINAL_ID
# api.language = settings.UZUM_CONTENT_LANGUAGE
```

## Testing

Для тестирования используются отдельные настройки в `tests/settings.py`:

```python
# UzumBank settings for tests
UZUM_TERMINAL_ID = "test-terminal-id"
UZUM_API_KEY = "test-api-key"
UZUM_BASE_URL = "https://test-chk-api.uzumcheckout.uz"
UZUM_CONTENT_LANGUAGE = "uz-UZ"
```

## Security Notes

- Никогда не коммитьте реальные продакшн ключи в репозиторий
- Используйте переменные окружения для продакшн конфигурации
- Обновите значения по умолчанию в `UZUM_PROD_*` константах на реальные продакшн значения
