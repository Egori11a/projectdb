### Гайд по созданию базы данных и настройке `.env`

---

#### 1. **Установка PostgreSQL**

1. Убедитесь, что PostgreSQL установлен на вашем компьютере.
   - На **Ubuntu**:
     ```bash
     sudo apt update
     sudo apt install postgresql postgresql-contrib
     ```
   - На **Windows** или **macOS** скачайте установщик с [официального сайта PostgreSQL](https://www.postgresql.org/).

2. Убедитесь, что PostgreSQL работает:
   ```bash
   sudo service postgresql start  # Для Ubuntu
   ```

3. Войдите в PostgreSQL:
   ```bash
   psql -U postgres
   ```

---

#### 2. **Создание базы данных и пользователя**

1. **Создайте нового пользователя и базу данных:**
   ```sql
   CREATE USER project_user WITH PASSWORD 'project_password';
   CREATE DATABASE project_db OWNER project_user;
   ```

2. **Дайте пользователю необходимые права:**
   ```sql
   GRANT ALL PRIVILEGES ON DATABASE project_db TO project_user;
   ```

3. **Подключитесь к базе данных:**
   ```bash
   psql -U project_user -d project_db
   ```

4. **Установите расширение `uuid-ossp` для работы с UUID:**
   ```sql
   CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
   ```

---

#### 3. **Создание файла `.env`**

Для удобного хранения конфиденциальных данных, таких как URL подключения к базе данных, создайте файл `.env` в корне вашего проекта.

**Пример содержимого `.env`:**
```dotenv
# Настройки базы данных
DB_HOST=localhost
DB_PORT=5432
DB_NAME=project_db
DB_USER=project_user
DB_PASSWORD=project_password

# Настройки приложения
APP_ENV=development
DEBUG=True

# Секретный ключ приложения
SECRET_KEY=your_secret_key
```

**Объяснение параметров:**
- `DB_HOST`: Адрес хоста базы данных (локально — `localhost`).
- `DB_PORT`: Порт подключения (стандартный для PostgreSQL — `5432`).
- `DB_NAME`: Имя вашей базы данных (`project_db`).
- `DB_USER`: Имя пользователя базы данных (`project_user`).
- `DB_PASSWORD`: Пароль пользователя (`project_password`).
---

#### 4. **Запуск скрипта для создания таблиц**

Если у вас есть SQL-скрипт для создания таблиц, запустите его в базе данных.

1. Сохраните скрипт (например, `schema.sql`).
2. Запустите его с помощью `psql`:
   ```bash
   psql -U project_user -d project_db -f schema.sql
   ```

---

#### 5. **Проверка базы данных**

После выполнения скрипта проверьте, что таблицы созданы:

1. Подключитесь к базе данных:
   ```bash
   psql -U project_user -d project_db
   ```

2. Выполните команду для отображения всех таблиц:
   ```sql
   \dt
   ```

---

#### 6. **Как использовать `.env` в Python**

Для работы с `.env` в Python используйте библиотеку `python-dotenv`.

1. Установите библиотеку:
   ```bash
   pip install python-dotenv
   ```

2. Добавьте в ваш Python-код чтение `.env`:
   ```python
   from dotenv import load_dotenv
   import os

   # Загрузка переменных из .env
   load_dotenv()

   # Пример доступа к переменным
   db_host = os.getenv("DB_HOST")
   db_port = os.getenv("DB_PORT")
   db_name = os.getenv("DB_NAME")
   db_user = os.getenv("DB_USER")
   db_password = os.getenv("DB_PASSWORD")
   ```

   Тебе это врятли понадобится, но на всякий

---
