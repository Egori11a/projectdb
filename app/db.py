import asyncpg
import uuid
import bcrypt
import logging

logger = logging.getLogger(__name__)

async def get_all_products(pool):
    """
    Получить список всех продуктов.
    """
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT product_id, name, description, price, stock, manufacturer
            FROM products
        """)

async def get_role_id_by_name(pool: asyncpg.pool.Pool, role_name: str) -> int:
    """
    Получить ID роли по её имени.
    """
    async with pool.acquire() as conn:
        role_id = await conn.fetchval("""
            SELECT role_id FROM roles WHERE name = $1
        """, role_name)
        if not role_id:
            logger.error(f"Роль с именем {role_name} не найдена.")
        return role_id

async def get_user_roles(pool: asyncpg.pool.Pool, user_id: str):
    """
    Получить список ролей пользователя.
    """
    async with pool.acquire() as conn:
        roles = await conn.fetch("""
            SELECT r.name
            FROM user_roles ur
            JOIN roles r ON ur.role_id = r.role_id
            WHERE ur.user_id = $1
        """, user_id)
        return [role['name'] for role in roles]

async def get_user_by_id(pool: asyncpg.pool.Pool, user_id: str):
    """
    Получить информацию о пользователе по user_id.
    """
    async with pool.acquire() as conn:
        return await conn.fetchrow("""
            SELECT username, email
            FROM users
            WHERE user_id = $1
        """, user_id)

async def create_user(pool: asyncpg.pool.Pool, username: str, hashed_password: str, email: str):
    """
    Создать нового пользователя и вернуть его user_id.
    """
    user_id = uuid.uuid4()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, username, hashed_password, email)
            VALUES ($1, $2, $3, $4)
        """, user_id, username, hashed_password, email)

        role_id = await get_role_id_by_name(pool, "User")
        await conn.execute("""
            INSERT INTO user_roles (user_id, role_id)
            VALUES ($1, $2)
        """, user_id, role_id)
    return user_id

async def get_user_by_email(pool: asyncpg.pool.Pool, email: str):
    """
    Получить пользователя по email.
    """
    async with pool.acquire() as conn:
        return await conn.fetchrow("""
            SELECT * FROM users WHERE email = $1
        """, email)

async def get_product_by_id(pool: asyncpg.pool.Pool, product_id: str):
    """
    Получить информацию о продукте по его ID.
    """
    async with pool.acquire() as conn:
        return await conn.fetchrow("""
            SELECT * FROM products WHERE product_id = $1
        """, product_id)

async def add_to_cart(pool: asyncpg.pool.Pool, user_id: str, product_id: str, quantity: int):
    """
    Добавить товар в корзину пользователя.
    """
    async with pool.acquire() as conn:
        # Проверяем, есть ли уже этот товар в корзине пользователя
        existing = await conn.fetchrow("""
            SELECT quantity FROM cart WHERE user_id = $1 AND product_id = $2
        """, user_id, product_id)

        if existing:
            # Обновляем количество товара в корзине
            await conn.execute("""
                UPDATE cart SET quantity = quantity + $1 WHERE user_id = $2 AND product_id = $3
            """, quantity, user_id, product_id)
        else:
            # Добавляем новый товар в корзину
            await conn.execute("""
                INSERT INTO cart (user_id, product_id, quantity)
                VALUES ($1, $2, $3)
            """, user_id, product_id, quantity)

async def get_cart_items(pool: asyncpg.pool.Pool, user_id: str):
    """
    Получить все товары в корзине пользователя.
    """
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT c.product_id, p.name, p.description, p.price, p.stock, c.quantity, (p.price * c.quantity) AS total_cost
            FROM cart c
            JOIN products p ON c.product_id = p.product_id
            WHERE c.user_id = $1
        """, user_id)


async def remove_from_cart(pool: asyncpg.pool.Pool, user_id: str, product_id: str):
    """
    Удалить товар из корзины пользователя.
    """
    async with pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM cart WHERE user_id = $1 AND product_id = $2
        """, user_id, product_id)

async def update_cart_quantities(pool: asyncpg.pool.Pool, user_id: str, quantities: dict):
    """
    Обновить количество товаров в корзине пользователя.
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            for product_id, quantity in quantities.items():
                quantity = int(quantity)
                if quantity <= 0:
                    # Удаляем товар из корзины, если количество <= 0
                    await conn.execute("""
                        DELETE FROM cart WHERE user_id = $1 AND product_id = $2
                    """, user_id, product_id)
                else:
                    # Проверяем доступность товара на складе
                    stock = await conn.fetchval("""
                        SELECT stock FROM products WHERE product_id = $1
                    """, product_id)
                    if quantity > stock:
                        raise ValueError(f"Недостаточно товара на складе для продукта {product_id}")
                    await conn.execute("""
                        UPDATE cart SET quantity = $1 WHERE user_id = $2 AND product_id = $3
                    """, quantity, user_id, product_id)

async def get_last_orders(pool: asyncpg.pool.Pool, user_id: str):
    """
    Получить последние пять заказов пользователя.
    """
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT o.order_id, o.order_date, o.total_cost, ARRAY(
                SELECT p.name
                FROM order_items oi
                JOIN products p ON oi.product_id = p.product_id
                WHERE oi.order_id = o.order_id
            ) AS products
            FROM orders o
            WHERE o.user_id = $1
            ORDER BY o.order_date DESC
            LIMIT 5
        """, user_id)


async def process_order(pool: asyncpg.pool.Pool, user_id: str):
    """
    Обработать заказ пользователя.
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Получаем товары из корзины
            cart_items = await conn.fetch("""
                SELECT c.product_id, c.quantity, p.price, p.stock
                FROM cart c
                JOIN products p ON c.product_id = p.product_id
                WHERE c.user_id = $1
            """, user_id)

            if not cart_items:
                raise ValueError("Корзина пуста.")

            # Проверяем доступность товаров и собираем данные для заказа
            total_cost = 0
            order_items = []
            for item in cart_items:
                if item['quantity'] > item['stock']:
                    raise ValueError(f"Недостаточно товара на складе для продукта {item['product_id']}")
                total_cost += item['price'] * item['quantity']
                order_items.append({
                    'product_id': item['product_id'],
                    'quantity': item['quantity'],
                    'price': item['price']
                })

            # Создаем новый заказ
            order_id = uuid.uuid4()
            await conn.execute("""
                INSERT INTO orders (order_id, user_id, total_cost, order_date, status)
                VALUES ($1, $2, $3, NOW(), $4)
            """, order_id, user_id, total_cost, 'Pending')

            # Добавляем записи в order_items
            for item in order_items:
                await conn.execute("""
                    INSERT INTO order_items (order_id, product_id, quantity, price)
                    VALUES ($1, $2, $3, $4)
                """, order_id, item['product_id'], item['quantity'], item['price'])

                # Обновляем запас продукта
                await conn.execute("""
                    UPDATE products SET stock = stock - $1 WHERE product_id = $2
                """, item['quantity'], item['product_id'])

            # Добавляем запись в order_history
            history_id = uuid.uuid4()
            await conn.execute("""
                INSERT INTO order_history (history_id, order_id, status, change_date)
                VALUES ($1, $2, $3, NOW())
            """, history_id, order_id, 'Pending')

            # Очищаем корзину пользователя
            await conn.execute("""
                DELETE FROM cart WHERE user_id = $1
            """, user_id)

async def add_product(pool, name, description, price, stock, manufacturer, category_id=None):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO products (product_id, name, description, price, stock, manufacturer, category_id)
            VALUES (uuid_generate_v4(), $1, $2, $3, $4, $5, $6)
        """, name, description, price, stock, manufacturer, category_id)

async def update_product(pool, product_id, name, description, price, stock, manufacturer, category_id=None):
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE products
            SET name = $1, description = $2, price = $3, stock = $4, manufacturer = $5, category_id = $6
            WHERE product_id = $7
        """, name, description, price, stock, manufacturer, category_id, product_id)

async def delete_product(pool, product_id):
    async with pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM products WHERE product_id = $1
        """, product_id)

async def get_all_products_with_categories(pool):
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT p.*, c.name AS category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.category_id
            ORDER BY p.name
        """)

async def get_all_orders(pool):
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT o.order_id, o.user_id, u.username, o.total_cost, o.order_date, o.status
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            ORDER BY o.order_date DESC
        """)

async def update_order_status(pool, order_id, new_status):
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE orders SET status = $1 WHERE order_id = $2
        """, new_status, order_id)
        # Добавляем запись в историю заказов
        history_id = uuid.uuid4()
        await conn.execute("""
            INSERT INTO order_history (history_id, order_id, status, change_date)
            VALUES ($1, $2, $3, NOW())
        """, history_id, order_id, new_status)

async def get_product_by_id(pool: asyncpg.pool.Pool, product_id: str):
    """
    Получить информацию о продукте по его ID.
    """
    async with pool.acquire() as conn:
        return await conn.fetchrow("""
            SELECT * FROM products WHERE product_id = $1
        """, product_id)

async def add_review(pool: asyncpg.pool.Pool, product_id: str, user_id: str, rating: int, comment: str):
    """
    Добавить отзыв к товару.
    """
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO reviews (product_id, user_id, rating, comment)
            VALUES ($1, $2, $3, $4)
        """, product_id, user_id, rating, comment)

async def get_reviews_by_product_id(pool: asyncpg.pool.Pool, product_id: str):
    """
    Получить все отзывы для данного товара.
    """
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT r.*, u.username
            FROM reviews r
            JOIN users u ON r.user_id = u.user_id
            WHERE r.product_id = $1
            ORDER BY r.review_date DESC
        """, product_id)

async def get_average_rating(pool: asyncpg.pool.Pool, product_id: str):
    async with pool.acquire() as conn:
        return await conn.fetchval("""
            SELECT AVG(rating) FROM reviews WHERE product_id = $1
        """, product_id)

async def search_products(pool: asyncpg.pool.Pool, query: str = '', category_id: str = '', manufacturer: str = ''):
    """
    Поиск товаров по названию, описанию, категории и производителю.
    """
    async with pool.acquire() as conn:
        sql = """
            SELECT p.product_id, p.name, p.description, p.price, p.stock, p.manufacturer, c.name AS category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.category_id
            WHERE TRUE
        """
        params = []
        param_index = 1

        if query:
            sql += f" AND (p.name ILIKE '%' || ${param_index} || '%' OR p.description ILIKE '%' || ${param_index} || '%')"
            params.append(query)
            param_index += 1

        if category_id:
            sql += f" AND p.category_id = ${param_index}"
            params.append(category_id)
            param_index += 1

        if manufacturer:
            sql += f" AND p.manufacturer = ${param_index}"
            params.append(manufacturer)
            param_index += 1

        sql += " ORDER BY p.name"

        return await conn.fetch(sql, *params)

async def get_all_categories(pool: asyncpg.pool.Pool):
    """
    Получить список всех категорий.
    """
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT category_id, name
            FROM categories
            ORDER BY name
        """)

async def get_all_manufacturers(pool: asyncpg.pool.Pool):
    """
    Получить список всех производителей.
    """
    async with pool.acquire() as conn:
        records = await conn.fetch("""
            SELECT DISTINCT manufacturer
            FROM products
            WHERE manufacturer IS NOT NULL AND manufacturer != ''
            ORDER BY manufacturer
        """)
        # Преобразуем список записей в список строк
        return [record['manufacturer'] for record in records]


async def add_category(pool: asyncpg.pool.Pool, name: str):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO categories (category_id, name)
            VALUES (uuid_generate_v4(), $1)
        """, name)

async def update_category(pool: asyncpg.pool.Pool, category_id: str, name: str):
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE categories
            SET name = $1
            WHERE category_id = $2
        """, name, category_id)

async def delete_category(pool: asyncpg.pool.Pool, category_id: str):
    async with pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM categories WHERE category_id = $1
        """, category_id)