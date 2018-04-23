# Webserver for the Parkpass project

### Описание:

Webserver API представляет собой реализацию пользовательского API с использованием фрейворка [Django](https://www.djangoproject.com/start/).
Текущая версия приложения работает на http://parkpass.ru/

### Использование: ###
Внутри есть конфигурации для развертывания внутри Docker-контейнера и через Docker-compose
Сборка контейнера:
```
 docker build ./
```

Запуск контейнера:
```
docker run -i -p (-d) 80:80 [container_id]
```

Можно указать ```--volume``` для папки ```/log``` чтобы логи записывались в файловую систему родительской системы

### Важно: ###
Отсутствует конфигурация PostgreSQL.
В контейнере используется SQLite3. Использовать только в режиме Debug.
Для релизного запуска пользоваться docker-compose утилитой со связкой с PostgreSQL.

## Описание API ##
Все методы принимают и возвращают (Content-type: application/json), если не указан другой тип

```- POST /account/login/ ``` (Логин)
Тело:
```
{
    "phone":"(+code)number", (String)
}
```

Status: 200/201 (Успешно)

Status: 400 (Ошибка)
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Phone is required"
}
```
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "phone format error"
}
```

```- POST /account/login/confirm/``` (Подтвержение кода смс)
Тело:
```
{
    "sms_code":"XXXXX", (String 5-signs)
}
```

Status: 200 (Успешно)
```
{
    "account_id":1, (Long integer)
    "token":"XXXX***", (String 40-signs),
    "expired_at": 1516476342.7 (Linux timestamp)
}
```

Status: 400 (Ошибка)
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Sms-code is required"
}
```
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Invalid sms-code format"
}
```
```
{
    "exception": "AuthException",
    "code": 100,
    "message": "Account with pending sms-code not found"
}
```

```- POST /account/logout/``` (Выход)
Тело:
```
{}
```
Status: 200 (Успешно)

```- GET /account/me/``` (Получение информации об аккаунте)

Status: 200 (Успешно)
```
{
    "id": 1,
    "first_name": "Michael", (Optinal)
    "last_name": "Jackson", (Optional)
    "email": "jackson@gmail.com", (Optional)
    "phone": "(+7)9092661898", (Required)
    "cards": [
        {
            "id": 3932023,
            "is_default": true,
            "pan": "415482******6447" (Number of card)
            "exp_date":"1122" (Month and year of card expiration)
        }
    ]
}
```

```- POST /account/me/``` (Изменение информации об аккаунте)
Тело:
```
{
    "first_name": "Michael", (Optinal)
    "last_name": "Jackson", (Optional)
}
```
Status: 200 (Успешно)

Status: 400 (Ошибка)
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Nothing change"
}
```
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Invalid first_name/last_name"
}
```

```- POST /account/card/add/``` (Добавление карты)
Тело:
```
{} # Empty
```
Status: 200 (Успешно)
```
{
    "payment_url": "https://securepay.tinkoff.ru/pU9Nmt" # Link for first payment
}
```


Status: 400 (Ошибка)
```
{
    "exception": "PaymentException",
    "code": 600 - 607,
    "message": "Message description"
}
```

```- POST /account/card/default/``` (Выбор карты по умолчанию)
Тело:
```
{
    "id": 3932023, (Long integer)
}
```

Status: 200 (Успешно)

Status: 400 (Ошибка)
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Id is required"
}
```
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Id invalid format"
}
```
```
{
    "exception": "ValidationException",
    "code": 402,
    "message": "Your card with such id not found"
}
```


```- POST /account/card/delete/``` (Удаление карты)
Тело:
```
{
    "id": 3932023, (Long integer)
}
```
Status: 200 (Успешно)

Status: 400 (Ошибка)
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Id is required"
}
```
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Id invalid format"
}
```
```
{
    "exception": "ValidationException",
    "code": 402,
    "message": "Your card with such id not found"
}
```
```
{
    "exception": "PermissionException",
    "code": 302,
    "message": "Impossible to delete card" (Maybe only one card)
}
```

```- GET /parking/get/<id>/``` (Получение информации о парковке)

Status 200
```
{
  "id": 1,
  "name": "Best parking",
  "description": "Sample optional information",
  "address": "streat Sezam",
  "latitude": 55.714843,
  "longitude": 37.6784,
  "free_places": 55
}
```

Status 400
```
{
    "exception": "ValidationException",
    "code": 402,
    "message": "Parking with such id not found"
}
```

```- GET /parking/list/?lt_lat=[val1]&lt_lon=[val2]&rb_lat=[val3]&rb_lon=[val4]``` (Получение парковок в квадрате)

Status 200
```
{
  "result": [
    {
      "id": 1,
      "name": "Parking1",
      "latitude": 55.707843,
      "longitude": 37.6784,
      "free_places": 55
    }
    ......
  ]
}
```

Status 400
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Invalid query parametes"
}
```


```- POST /account/session/create/``` (Создание сессии от пользователя. Требует токен сессии)

Тело
```
{
    "session_id":"2", (Session id from vendor storage) String
    "parking_id":1,
    "started_at":1518952262 ( Unix-timestamp )
}
```

Status 200 (ОK)
```
{
    "id":2 (Session id)
}
```

Status 400
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Session id, parking id, client id and started at are required"
}
```

```
{
    "exception": "ValidationException",
    "code": 402,
    "message": "Parking with such id not found"
}
```

```- POST /account/session/complete/``` (Завершение сессии от пользователя. Требует токен сессии)

Тело
```
{
    "session_id":2, (Session id from vendor storage)
    "parking_id":1,
    "client_id":1,
    "completed_at":1518952262 ( Unix-timestamp )
}
```

Status 200


```- POST /account/session/stop/``` (Приостановление текущей сессии пользователем. Требует токен сессии)

Тело
```
{
    "id":2 (Session id)
}
```
Status 200 (OK)

Status 400
```
{
    "exception": "ValidationException",
    "code": 402,
    "message": "ParkingSession with id not found"
}
```



```- POST /account/session/resume/``` (Восстановление текущей сессии пользователем. Требует токен сессии)

Тело
```
{
    "id":2 (Session id)
}
```
Status 200 (OK)

Status 400
```
{
    "exception": "ValidationException",
    "code": 402,
    "message": "ParkingSession with id not found"
}
```


```- GET /account/session/list/``` (Получение истории сессий пользователя. Требует токен сессии)

Status 200 (OK)
```
{
    "result": [
        {
            "id": 4,
            "parking_id": 1,
            "debt": 120.0,
            "state": 0,
            "is_suspended": false,
            "completed_at": 1459814400.0, (Optional)
            "started_at": 1459728000.0,
        },
        ...
}
```

```- GET /account/session/debt/``` (Получениe задолжности по текущей сессии. Требует токен сессии)

Status 200 (OK)
```
{
    'id': 15
    'parking_id': 1,
    'debt': 120.0,
    'state': 6,
    'started_at': 1481587200.0,
    'updated_at': 1481673600.0, (Optional)
    'is_suspended': False,
    'suspended_at': None, (Optional)
    'completed_at': None, (Optional)
    'orders': [ (Optional list)
        {
            'id': 2,
            'sum': 20.0,
            'paid': False
        },
        {
            'id': 1,
            'sum': 20.0,
            'paid': True
        },
        ...
    ]
}
```

Status 400
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Error"
}
```

```- POST /account/session/pay/``` (Запрос на оплату всей задолжности пользователя. Требует токен сессии)

Status 200 (OK)
```
{
    "id": 1 (Long integer, Id-сессии по которой необходимо списать задолженность)
}
```

Status 400
```
{
    "exception": "ValidationException",
    "code": 402,
    "message": "Parking session with id %s does not exist"
}
```

## Информация для вендора: ##
Для использования API вендора необходимо с помощью администратора добавить организацию в список.
Вендору будет выдан секретный ключ ```secret``` для цифровой подписи запросов и имя ```slug``` организации. Например:

```
    secret = 223c63e6c71520cc6d0bf75a054b8c1d00ffc0c3d645af46c0abfdec08d9613f
    vendor_name = 'example-parking-name'
```
Для тестирования API можно использовать эти параметры. Данному тестовому вендору также принадлежит парковка с id=1

Все запросы к API вендора должны содержать в заголовках Header 2 дополнительных параметра c указанием:
```
    Header["x-signature"] = "0cc6d0bf75a054b..." (hmac-sha512 тела запроса c использованием secret в 16-ричном представлении)
    Header["x-vendor-name"] = "example-parking-name"
```
Информацию о ```hmac``` можно найти [здесь](https://ru.wikipedia.org/wiki/HMAC).

API добавление парковок и управления ими в личном кабинете, будет добавлено позднее. В настоящий момент, добавление парковки осуществляется через администратора.

Перечень ошибок при выполнении запросов к API вендора:

Status 400
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Signature is empty. [x-signature] header required"
}
```

```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "The vendor name is empty. [x-vendor-name] header required"
}
```

```
{
    "exception": "PermissionException",
    "code": 303,
    "message": "Vendor does not exist"
}
```

```
{
    "exception": "PermissionException",
    "code": 300,
    "message": "Invalid signature"
}
```

### Описание API ###

```- POST /parking/v1/test/``` (Тестовый метод для проверки ```secret```, выданный вендору. echo-метод)

Тело
```
{
    "sample_key":"lorem"
}
```

Status 200 (ОK)
```
{
    "sample_key":"lorem"
}
```


```- POST /parking/v1/update/``` (Обновление информации о парковке от вендора)

Тело
```
{
    "parking_id":1,
    "free_places":10
}
```
Status 200 (ОK)

Status 400
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Invalid format"
}
```

```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Parking id and free places are required"
}
```

```
{
    "exception": "ValidationException",
    "code": 402,
    "message": "Parking with such id not found"
}
```

```- POST /parking/v1/session/create/``` (Новая сессия от вендора)

Тело
```
{
    "session_id":"2", (String, session id from vendor storage)
    "parking_id":1,
    "client_id":1,
    "started_at":1518952262 ( Unix-timestamp )
}
```

Status 200 (ОK)

Status 400
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Keys 'session_id', 'parking_id', 'client_id' and 'started_at' are required"
}
```

```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Keys session_id / parking_id / client_id / started_at has invalid format"
}
```

```
{
    "exception": "ValidationException",
    "code": 402,
    "message": "Parking with such id for vendor [val] not found"
}
```

```
{
    "exception": "ValidationException",
    "code": 402,
    "message": "Client with such id not found"
}
```

```
{
    "exception": "ValidationException",
    "code": 403,
    "message": "'session_id' value [val] for 'parking_id' [val] is already exist"
}
```

```- POST /parking/v1/session/update/``` (Обновление статуса по сессии от вендора)

Тело
```
{
    "session_id":2, (Session id from vendor storage)
    "debt":0.1,
    "updated_at":1518953262
}
```

Status 200 (ОK)

Status 400
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Session id, debt, updated at are required"
}
```

```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Invalid format debt or updated_at. Debt float required, Updated at int required"
}
```

```
{
    "exception": "ValidationException",
    "code": 402,
    "message": "Session does not exists"
}
```

```- POST /parking/v1/session/complete/``` (Завершение сессии от вендора)

Тело
```
{
    "session_id":2, (Session id from vendor storage)
    "debt":0.1,
    "completed_at":1518953262
}
```

Status 200 (ОK)

Status 400
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Session id, debt, completed at are required"
}
```

```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Invalid format debt or completed_at. Debt float required, Completed at int required"
}
```

```
{
    "exception": "ValidationException",
    "code": 402,
    "message": "Session does not exists"
}
```


```- POST /parking/v1/session/list/update/``` (Обновление списка сессий от вендора)

Тело
```
{
    "parking_id":1,
    "sessions":[
        {
            "session_id":"2", (Session id from vendor storage)
            "debt":0.1,
            "updated_at":1518953262"
        },
        {
            "session_id":"5", (Session id from vendor storage)
            "debt":10.5,
            "updated_at":1518953280"
        },
        ....
    ]
}
```

Status 202 (ОK) (Запрос принят на ассинхронную обработку)

Status 400
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Key 'parking_id' and 'sessions' are required"
}
```

```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Key 'parking_id' and 'sessions' are required"
}
```