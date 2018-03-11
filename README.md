# Webserver for the Parkpass project

### Описание:

Webserver API представляет собой реализацию пользовательского API с использованием фрейворка [Django](https://www.djangoproject.com/start/).
Текущая версия приложения работает на http://176.9.158.147:5000/

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
    "sms_code":"XXXXXX", (String 6-signs)
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
            "id": 1,
            "is_default": true,
            "number":"0987" (Last 4-sign of number)
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
{
    "number": "XXXXX", (Card number [String])
    "owner": "FIRSTNAME LASTNAME",
    "expiration_date_month": 12, (1-12)
    "expiration_date_year": 2019
}
```
Status: 200 (Успешно)

Status: 400 (Ошибка)
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Number, owner, expiration_date_month and
        expiration_date_year are required"
}
```
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Invalid first_name/last_name"
}
```

```- POST /account/card/default/``` (Выбор карты по умолчанию)
Тело:
```
{
    "id": 1, (Long integer)
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


```- POST /account/card/delete/``` (Добавление карты)
Тело:
```
{
    "id": 1, (Long integer)
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
    "message": "Impossible to delete card"
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

```- POST /update/``` (Обновление парковки от вендора)

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

```- POST /parking/session/create/``` (Новая сессия от вендора)

Тело
```
{
    "session_id":2, (Session id from vendor storage)
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

```
{
    "exception": "ValidationException",
    "code": 402,
    "message": "Account with such id not found"
}
```

```
{
    "exception": "ValidationException",
    "code": 403,
    "message": "Parking Session with such id for this parking is found"
}
```

```- POST /parking/session/update/``` (Обновление статуса по сессии от вендора)

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

```- POST /parking/session/complete/``` (Завершение сессии от вендора)

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

```- POST /account/session/create/``` (Создание сессии от пользователя. Требует токен сессии)

Тело
```
{
    "session_id":2, (Session id from vendor storage)
    "parking_id":1,
    "client_id":1,
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


```- POST /account/session/cancel/``` (Отмена сессии от пользователя. Требует токен сессии)

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
    "code": 400,
    "message": "Error"
}
```


```- POST /account/debt/current/``` (Получени задолжности по текущей сессии. Требует токен сессии)

Status 200 (OK)
```
{
    "session_id": "BCHHASAX..." (Account session id)
    "debt":10.25,
    "paid_debt":8.50,
    "started_at":1518952262, ( Unix-timestamp )
    "updated_at":1518952452 ( Unix-timestamp )
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

### Информация для вендора: ###
Для использования API-вендора необходимо с помощью администратора добавить организацию в список.
Вендору будет выдан секретный ключ для цифровой подписи запросов. Например:

```
    secret = 223c63e6c71520cc6d0bf75a054b8c1d00ffc0c3d645af46c0abfdec08d9613f
    vendor_name = 'example-parking-name'
```

Все запросы к API вендора должны содержать в header 2 дополнительных параметра c указанием этих параметров:
```
    Header["x_signature"] = "0cc6d0bf75a054b..." (hmac-sha512 тела запроса c использованием secret в 16-ричном представлении)
    Header["x_vendor_name"] = "example-parking-name"
    vendor_name = 'example-parking-name'
```

Перечень ошибок при выполнении запросов к API вендора:
Status 400
```
{
    "error": "Signature is empty. [x-signature] header required"
}
```

```
{
    "error": "The vendor name is empty. [X-VENDOR-UNIQUE-NAME] header required"
}
```

```
{
    "error": "Vendor not found"
}
```

```
{
    "error": "Invalid signature"
}
```

