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


### Описание протокола состояний сессии: ###
**Активная сессия** - это сессия, от момента создания (или клиентом, или вендором) до момента завершения вендором или приостановления пользователем.
В случае, если клиент завершает сессию, открытие которой не было подтверджено вендором, сессия переводится в приостановленное состояние флагом ```is_suspended = True```

**Статусы активной сессии:**

* ```Started_by_client = 1``` - открытие активной сессии было выполнено клиентом, но не подтверждено вендором
* ```Started_by_vendor = 2``` - открытие активной сессии было выполнено вендором, но не подтверждено клиентом
* ```Started = 3``` - сумма состояний предыдущих значений. Означает, что открытие активной сессии было обозначено как вендором, так и клиентом
* ```Completed_by_client = 6``` - завершение активной сессией было подтверждено только клиентом. Открытие сессии было подтверждено только вендором
* ```Completed_by_client_fully = 7``` - завершение активной сессией было подтверждено только клиентом. Открытие сессии было подтверждено обоими субъектами
* ```Completed_by_vendor = 10``` - завершение активной сессии вендором. Открытие не было подтверждено клиентом
* ```Completed_by_vendor_fully = 11``` - завершение активной сессии вендором. Открытие сессии было подтверждено обоими субъектами
* ```Completed = 14``` - завершение сессии двумя субъектами. Открытие сессии не было подтверждено пользователем
* ```Completed_fully = 15``` - завершение сессии двумя субъектами. Открытие сессии было подтверждено также обоими субъектами

**Закрытая сессия** (```Closed = 0```) - это сессия, которая была открыта и завершена вендором и задолжность которой было оплачено пользователем

**Отмененная сессия** (```Canceled = -1``` ) - сессия, которая была отменена вендором при отказе вьезда пользователем.
Средства должны быть возвращены пользователю, если были списаны.

**Приостановленная сессия** - сессия, которая была переведена пользователем самостоятельно при каких-либо обстоятельствах.
Такая сессия содержит выставленный флаг ```is_suspended``` и содержит время приостановки ```suspended_at```.
Данный статус блокирует возможность списания средств сервером по приходящим от вендора новых задолжностям в обновлениях сессии.
Флаг ```is_suspended``` также неявно выставляется при завершении активной сессии пользователем в случае, если вендор не подтвердил ее создание.
Приостановленная сессия позволяет создавать новую активную сессию пользователю.


**Пользователь имеет возможность создания новой парковочной сессии, если:**
- имеет хотя бы одну привязанную к аккаунту карту
- имеет все успешные парковочные сессии в истории в состоянии ```Closed```, что означает отcутствие неоплаченой задолжности
- имеет последнюю парковочную сессию в состоянии ```Canceled```. Этот статус устанавливает вендор при отказе пользователя от вьезда на парковку
- имеет последнюю парковку с флагом ```is_suspended```. Позволяет пользователю вручную завершить активную сессию по некоторым причинам.

**Смена id начиная с константы :**
Через ```psql``` выполнить команды:
```
parkpass=# use parkpass
parkpass-# \d+ accounts_account
parkpass=# ALTER SEQUENCE accounts_account_id_seq RESTART WITH 100000000000000001;
```
Изменение типов данных для столбцов foreign key (например в таблице ```payments_creditcard```):
```
    alter table payments_creditcard alter column account_id type bigint using account_id::bigint;
```

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

```- POST /account/login/email/``` (Получение сессии по паре email/password)
Тело:
```
{
    "email":"myemail@gmail.com",
    "password":"qwerty"
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

Status 400 (Ошибка)
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Email and password are required"
}
```

```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Invalid email format"
}
```

```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "To short password. Must be 6 or more symbols"
}
```

```
{
    "exception": "AuthException",
    "code": 100,
    "message": "User with such email not found"
}
```

```
{
    "exception": "AuthException",
    "code": 100,
    "message": "User with such email not found"
}
```

```
{
    "exception": "AuthException",
    "code": 101,
    "message": "Invalid password"
}
```

```
{
    "exception": "AuthException",
    "code": 103,
    "message": "Invalid session. Login with phone required"
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

```
{
    "exception": "PermissionException",
    "code": 304,
    "message": "It's impossible to create second active session"
}
```

```
{
    "exception": "PermissionException",
    "code": 305,
    "message": "It's impossible to create session without credit card"
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


```- GET /account/session/list/?page=<next>&from_date=<timestamp>&to_date=<timestamp>``` (Получение истории сессий пользователя. Требует токен сессии)

Status 200 (OK) (В случае интервала next=None)
```
{
    "result": [
        {
            "id": 4,
            "parking": {
                "id":1,
                "name":"Parking name"
            }
            "debt": 120.0,
            "state": 0,
            "is_suspended": true,
            "suspended_at": 1459814400.0, (Optional)
            "completed_at": 1459814400.0, (Optional)
            "started_at": 1459728000.0,
        },
        ...
    ],
    "next":"324123342"
}
```

Status 400
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "from_date and to_date unix-timestamps are required"
}
```

```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Key 'to_date' must be more than 'from_date' key"
}
```

```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Max time interval exceeded. Max value %s, accepted %s"
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

```- POST account/email/add/``` (Привязка почты к аккаунту. Требует токен сессии)

Тело:
```
{
    "email": "my-email@gmail.com",
}
```

Status 200 (OK)

Status 400
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Key 'email' is required"
}
```

```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Invalid email format"
}
```

```
{
    "exception": "ValidationException",
    "code": 403,
    "message": "Such email is already binded to account"
}
```

```- POST account/email/confirm/<activate_code>``` (Подтверждение почты из email)

```
{
    "status": "Success| Error",
}
```

```- POST account/session/receipt/``` (Получение чеков по заказам. Требует токен сессии)

Тело:
```
{
    "id": 2,
}
```

Status 200 (OK)
```
{
    "result": [
        {
            "order": {
                "id": 1,
                "sum": 150.0
            },
            "fiscal":
            {
                "fiscal_document_number": 102,
                "ofd": "ofd",
                "ecr_reg_number": "ecr_reg_number_sample",
                "url": "http://yandex.ru",
                "receipt": "recept_text",
                "shift_number": 101,
                "token": "token_sample",
                "receipt_datetime": 1526591673.0, # Unix-timestamp
                "fiscal_document_attribute": 103,
                "qr_code_url": "http://qr_code_url.ru",
                "type": "type_of_notification",
                "fn_number": "fn_number_sample",
                "fiscal_number": 100
            },
          },
          ....
    ]
}
```

Status 400
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Key 'id' is required"
}
```

```
{
    "exception": "ValidationException",
    "code": 402,
    "message": "Parking session with id # does not exist"
}
```

```- POST account/session/receipt/send/``` (Отправика чеков на почту. Требует токен сессии)

Тело:
```
{
    "id": 1
}
```
Status 200 (Успешно)

Status 400
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Key 'id' is required"
}
```

```
{
    "exception": "ValidationException",
    "code": 402,
    "message": "Parking session with id # does not exist"
}
```

```
{
    "exception": "PermissionException",
    "code": 306,
    "message": "Your account doesn't have binded email"
}
```

```- POST /parking/complain/``` (Отправка жалобы. Требует токен сессии)

Тело:
```
{
    "id": 1, (Id сессии в системе parkpass)
    "type": (1-5) тип жалобы
    "message": "Complain description"
}
```

Status 200 (OK)

Status 400
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Keys 'type', 'session_id' and 'message' are required"
}
```

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

```- POST /parking/v1/session/cancel/``` (Отмена сессии от вендора)

Тело
```
{
    "session_id":"2", (String, session id from vendor storage)
    "parking_id":1
}
```

Status 200 (ОK)

Status 400
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Keys 'session_id' and 'parking_id' are required"
}
```

```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Keys session_id / parking_id / has invalid format"
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

### Описание API для RPS ###

```- POST /parking/rps/session/create/``` (Новая сессия)

Тело
```
{
    "client_id":1,
    "started_at":1518952262, ( Unix-timestamp )
    "parking_id":1
}
```

Status 200 (ОK)

Status 400
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Keys 'parking_id', 'client_id' and 'started_at' are required"
}
```

```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Keys parking_id / client_id / started_at has invalid format"
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
    (В случае, если комбинация (client_id + started_at) уже была добавлена ранее для parking_id
}
```

```- POST /parking/rps/session/update/``` (Обновление статуса по сессии)

Тело
```
{
    "client_id":1,
    "started_at":1518952262, ( Unix-timestamp )
    "parking_id":1,
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
    "message": "Keys 'parking_id', 'client_id', 'started_at', 'debt' and 'updated_at' are required"
}
```

```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Keys parking_id / client_id / started_at / debt / updated_at has invalid format"
}
```

```
{
    "exception": "ValidationException",
    "code": 402,
    "message": "Session [client_id+started_at] does not exists"
}
```

```- POST /parking/rps/session/complete/``` (Завершение сессии)

Тело
```
{
    "client_id":1,
    "started_at":1518952262, ( Unix-timestamp )
    "parking_id":1,
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
    "message": "Keys 'parking_id', 'client_id', 'started_at', 'debt' and 'completed_at' are required"
}
```

```
{
    "exception": "ValidationException",
    "code": 400,
    "message":  "Keys parking_id / client_id / started_at / debt / completed_at has invalid format"
}
```

```
{
    "exception": "ValidationException",
    "code": 402,
    "message": "Session [client_id+started_at] does not exists"
}
```

```- POST /parking/rps/session/cancel/``` (Отмена сессии)

Тело
```
{
    "client_id":1,
    "started_at":1518952262, ( Unix-timestamp )
    "parking_id":1
}
```
Status 200 (ОK)

Status 400
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Keys 'parking_id', 'client_id' and 'started_at' are required"
}
```

```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "Keys parking_id / client_id / started_at has invalid format"
}
```

```
{
    "exception": "ValidationException",
    "code": 402,
    "message": "Session [client_id+started_at] does not exists"
}
```


```- POST /parking/rps/session/list/update/``` (Обновление списка сессий от вендора)

Тело
```
{
    "parking_id":1,
    "sessions":[
        {
            "client_id":1,
            "started_at":1518952262, ( Unix-timestamp )
            "debt":0.1,
            "updated_at":1518953262"
        },
        {
            "client_id":1,
            "started_at":1518952262, ( Unix-timestamp )
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
    "message": "Invalid [Key] Item [number]"
}
```