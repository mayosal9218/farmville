PRAGMA foreign_keys = ON;
CREATE TABLE farms (id INTEGER PRIMARY KEY, name TEXT NOT NULL, owner_name TEXT NOT NULL);
CREATE TABLE fields (id INTEGER PRIMARY KEY, farm_id INTEGER NOT NULL REFERENCES farms(id), name TEXT NOT NULL, area_acres REAL);
CREATE TABLE activity_types (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE daily_activities (id INTEGER PRIMARY KEY, farm_id INTEGER NOT NULL REFERENCES farms(id), activity_type_id INTEGER REFERENCES activity_types(id), field_id INTEGER REFERENCES fields(id), activity_date TEXT NOT NULL, duration_minutes INTEGER, description TEXT NOT NULL, worker_name TEXT, weather_notes TEXT);
CREATE TABLE expenses (id INTEGER PRIMARY KEY, farm_id INTEGER NOT NULL REFERENCES farms(id), expense_date TEXT NOT NULL, category TEXT NOT NULL, description TEXT NOT NULL, amount REAL NOT NULL, vendor TEXT);
CREATE TABLE sales (id INTEGER PRIMARY KEY, farm_id INTEGER NOT NULL REFERENCES farms(id), sale_date TEXT NOT NULL, product_name TEXT NOT NULL, quantity REAL NOT NULL, unit TEXT NOT NULL, total_amount REAL NOT NULL, buyer TEXT);
CREATE TABLE crops (id INTEGER PRIMARY KEY, field_id INTEGER NOT NULL REFERENCES fields(id), crop_name TEXT NOT NULL, variety TEXT, planted_on TEXT, expected_harvest_on TEXT);
CREATE TABLE livestock (id INTEGER PRIMARY KEY, farm_id INTEGER NOT NULL REFERENCES farms(id), tag_number TEXT UNIQUE, species TEXT NOT NULL, breed TEXT, born_on TEXT);
