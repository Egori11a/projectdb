-- Создание расширений
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Таблица roles
CREATE TABLE roles (
    role_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);

-- Таблица users
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) NOT NULL,
    hashed_password TEXT NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL
);

-- Таблица user_roles
CREATE TABLE user_roles (
    user_id UUID NOT NULL,
    role_id INT NOT NULL,
    PRIMARY KEY (user_id, role_id),
    CONSTRAINT fk_user_roles_users FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_user_roles_roles FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE CASCADE
);

-- Таблица categories
CREATE TABLE categories (
    category_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL
);

-- Таблица products
CREATE TABLE products (
    product_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(150) NOT NULL,
    description TEXT,
    category_id UUID,
    price NUMERIC(10, 2) NOT NULL,
    stock INT NOT NULL,
    manufacturer VARCHAR(150),
    CONSTRAINT fk_products_categories FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE SET NULL
);

-- Таблица cart
CREATE TABLE cart (
    user_id UUID NOT NULL,
    product_id UUID NOT NULL,
    quantity INT NOT NULL,
    PRIMARY KEY (user_id, product_id),
    CONSTRAINT cart_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT cart_product_id_fkey FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

-- Таблица orders
CREATE TABLE orders (
    order_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    order_date TIMESTAMP DEFAULT NOW(),
    status VARCHAR(50) NOT NULL,
    total_cost NUMERIC(10, 2) NOT NULL,
    CONSTRAINT fk_orders_users FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Таблица order_items
CREATE TABLE order_items (
    order_id UUID NOT NULL,
    product_id UUID NOT NULL,
    quantity INT NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    PRIMARY KEY (order_id, product_id),
    CONSTRAINT order_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    CONSTRAINT order_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

-- Таблица order_history
CREATE TABLE order_history (
    history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL,
    change_date TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_order_history_orders FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
);

-- Таблица reviews
CREATE TABLE reviews (
    review_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL,
    user_id UUID NOT NULL,
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    review_date TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_reviews_products FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    CONSTRAINT fk_reviews_users FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Заполнение таблиц тестовыми данными
INSERT INTO roles (name) VALUES ('User'), ('Admin');