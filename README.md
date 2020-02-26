Основаная документация перенесена в [вики](/strevg/parkpass_backend/wiki/Home)

### Описание использования API партнера

#### Регистрация партнера
Для начала работы необходимо зарегистрироваться как партнер.
При регистрации патнер получает пару значений
 ```partner_name``` и ```partner_secret``` от администратора сервиса PARKPASS.
Значения этих полей необходимы при обращении к API партнеров PARKPASS

#### Использование API
API партнера позволяет получить или отправить данные в PARKPASS через GET и POST запросы.
При выполнениие GET-запроса партнер должен указать выданные ему ```partner_name``` в заголовке запроса:

```bash
curl https://parkpass.ru/api/v1/partner/<url> -H "x-partner-name: partner_name"
```

При передаче пустого заголовка ```x-partner-name``` в ответ будет получена ошибка:
```json
{
  "code": 400,
  "exception": "ValidationException",
  "message": "The partner name is empty. [x-partner-name] header required",
}
```

При передаче ошибочного значения ```partner_name``` в ответ будет получена ошибка:
```json
{
  "code": 303,
  "exception": "PermissionException",
  "message": "Invalid partner name"
}
```
При выполнении POST-запросов сервису PARKPASS необходимо предать
вместе с телом запроса подпись. Подпись осуществляется с помощью алгоритма hmac-sha512.

Например для ```partner_secret=secret``` и тела
```{"foo": "bar"}```
Зачение hmac-sha512 hex-сигнатуры - ```c92a5c48818a913faa02546ca27079405e5d49b98690e1030435555662674f53f96281ad803b75cb651a5c908908f27b95c63c814a8cc72d73c299a6e1e04e00```

При отправке POST-запроса без передачи подписи в заголовке, будет выдана ошибку:
```json
{
  "code": 400,
  "exception": "ValidationException",
  "message": "Signature is empty. [x-signature] header required"
}
```

При ошибке валидации на стороне сервиса PARKPASS:
```json
{
  "code": 300,
  "exception": "ValidationException",
  "message": "Invalid signature"
}
```

#### Проверка интеграции с API партнера
Для проверки интеграции можно использовать тестовый сервер сервиса PARKPASS
``` https://sandbox.parkpass.ru ```

Например, чтобы получить список доступных парковок, выполните: 
```bash
curl https://sandbox.parkpass.ru/api/v1/partner/all/ -H "x-partner-name: test_partner"
```

Для отправки POST-запросов используйте ```partner_secret=c2a0a5647d33080ad103ac33d02be4d3671c774a30a2e90d4a54de0f6f81ccf8```


### Описание API для работы с парковочными картами
Все используемые REST API вызовы используют только подписанные запросы с помощью ```hmac-sha512"```.
Все методы по умолчанию используют ```Content-type: application/json```

``` - POST api/v1/parking/rps/cards/debt/ ``` - Получение задолженности по парковочной карте. (не требует токенов доступа)
Тело:
```
{
    "card_id": "N..", # must be more 6 symbols 
    "parking_id": 2
    "phone":"+7(909)1234332"
}
```

Status 200
```
{
    "duration":100, # (sec)
    "debt":10 # (rub)
}
```

Status 400
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "<Some validation error>"
}
```

```
{
    "exception": "ValidationException",
    "code": 402,
    "message": "Parking does not found or parking card is unavailable"
}
```

``` - GET api/v1/parking/rps/cards/guest/payment/init/ ``` - Запрос на формирование оплаты задолженности по парковочной карте. Задолженность в системе формируется после успешного получения в методе, укаазаном выше. Для формирования платежа необходимо указать ```card_session``` объекта задолженности. Не требует токена доступа, для отслеживания платежа пользователя генерится ```client_uuid``` вместе со ссылкой для оформления платежа.

Тело:
```
{
    "card_session": 1
}
```

Status 200
```
{
    "client_uuid": "e81458da-2116-42e5-af1b-c99a8ea81f04",
    "payment_url": <tinkoff_url>
}
```

Status 400
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "<Some validation error>"
}

{
    "exception": "ValidationException",
    "code": 400,
    "message": "Parking card session is already paid"
}

{
    "exception": "ValidationException",
    "code": 402,
    "message": "Parking card session does not exist"
}
```

``` - GET api/v1/parking/rps/cards/account/payment/init/ ``` - Запрос на формирование оплаты задолженности по парковочной карте из МП. Задолженность в системе формируется после успешного получения также в методе, укаазаном выше. Для формирования платежа необходимо указать ```card_session``` объекта задолженности. Требует токен пользователя.

Тело:
```
{
    "card_session": 1
}
```

Status 200
```
{
    "payment_url": <tinkoff_url>
}
```

Status 400
```
{
    "exception": "ValidationException",
    "code": 400,
    "message": "<Some validation error>"
}

{
    "exception": "ValidationException",
    "code": 400,
    "message": "Parking card session is already paid"
}

{
    "exception": "ValidationException",
    "code": 402,
    "message": "Parking card session does not exist"
}
```

``` - GET api/v1/parking/rps/cards/payment/status/ ``` - Запрос на получение статуса оплаты задолженности по парковочной карте. Для формирования платежа необходимо указать ```card_session``` объекта задолженности. Не требует токен пользователя.

Тело:
```
{
    "card_session": 1
}
```

Status 200
```
{   
    "order_id":1,
    "sum":10,
    "refunded_sum":0,
    "authorized":true/false,
    "paid":true/false,
    "error":"Error reason" # (Optional)
}
```

Status 400
```
{
    "exception": "ValidationException",
    "code": 402,
    "message": "Parking card session does not exist"
}

{
    "exception": "ValidationException",
    "code": 400,
    "message": "Validation error"
}

{
    "exception": "ValidationException",
    "code": 406,
    "message": "Payment is not yet inited. Please, call /payment/init/ method"
}
```

### Требуемый API от RPS
- ```POST```-метод на получения задолженности по парковочной карте
Тело:
```
{
    "card_id": "SOME_STRING", # (Номер парковочной карты)
    "parking_id": 1, # (Id парковки RPS в системе Parkpass)
    "phone": 790912335229,
}
```
Валидый ответ
```
{
    "card_id": "SOME_STRING", # (Номер парковочной карты)
    "parking_id": 1, # (Id парковки RPS в системе Parkpass)
    "duration": 200, # (Время парковки в секундах)
    "debt": 10 # (Сумма для оплаты в рублях)
}
```
Если задолженностей нет, то присылать ```duration=0``` и ```debt=0```

- ```POST```- метод на авторизацию оплаты задолженности (холдирование)

Тело:
```
{
    "card_id": "SOME_STRING", # (Номер парковочной карты)
    "order_id": 1, # (Id объекта оплаты в Parkpass)
    "sum": 100 # (Заблокированная оплата в рублях)
}
```
Валидый ответ:
Status 200
```
{}
```
При получении статуса 200 по запросу у клиента будет автоматически вызвано поздтвержжение оплаты. При любом другом полученном ```status_code``` будет вызывана отмена платежа

- ```POST```- метод на подтверждение оплаты задолженности
Тело:
```
{
    "card_id": "SOME_STRING", # (Номер парковочной карты)
    "order_id": 1, # (Id объекта оплаты в Parkpass)
}
```
Валидый ответ:
Status 200
```
{}
```
При получении статуса отличного от 200, платеж будет помечен в системе Parkpass как требующий оповещения. Возвращение средств пользователю инициализироваться не будет

- ```POST```- метод на возврат оплаты задолженности (после подтверждения)
Тело:
```
{
    "card_id": "SOME_STRING", # (Номер парковочной карты)
    "order_id": 1, # (Id объекта оплаты в Parkpass)
    "refund_sum": 10, # (Полная или частичная сумма отмены)
    "refund_reason": "<some text about refund reason>"
}
```
Валидый ответ:
Status 200
```
{}
```
Другие значения ```status_code``` будут игнорироваться
