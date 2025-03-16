import subprocess
import unittest
import docker
import time
import os
import pymysql
from faker import Faker

SQL_FILE = "badrage-migration.sql"
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_USER = "user"
DB_PASSWORD = "password"
DB_NAME = "badrage_database"

fake = Faker()

class TestDockerCompose(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docker_client = docker.from_env()
        cls.containers = {}

        print("\n🔄 Stopping existing containers...")
        try:
            subprocess.run("docker compose down -v".split(), check=True)
        except subprocess.CalledProcessError:
            pass
        
        print("🚀 Starting Docker Compose...")
        subprocess.run("docker compose up --no-build -d".split(), check=True)

        cls.wait_for_containers(["mysql_server", "phpmyadmin"])
        cls.wait_for_mysql_ready()
        cls.import_sql_file()


    @classmethod
    def wait_for_containers(cls, services, timeout=30):
        print("⏳ Waiting for containers to start...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            cls.containers = {s: None for s in services}
            running_containers = {c.name: c for c in cls.docker_client.containers.list()}
            
            all_ready = True
            for service in services:
                if service in running_containers:
                    cls.containers[service] = running_containers[service]
                else:
                    all_ready = False
            
            if all_ready:
                print("✅ All containers are up!")
                return
            time.sleep(3)

        raise TimeoutError("⛔ Timeout: Containers failed to start within the time limit.")

    @classmethod
    def wait_for_mysql_ready(cls, timeout=30):
        print("⏳ Waiting for MySQL to be ready...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                connection = pymysql.connect(
                    host=DB_HOST,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    database=DB_NAME,
                    port=DB_PORT,
                    cursorclass=pymysql.cursors.Cursor
                )
                connection.close()
                print("✅ MySQL is ready!")
                return
            except pymysql.MySQLError:
                time.sleep(3)

        raise TimeoutError("⛔ Timeout: MySQL did not become ready in time.")

    @classmethod
    def import_sql_file(cls):
        if os.path.exists(SQL_FILE):
            print(f"📥 Importing SQL file: {SQL_FILE}")
            try:
                connection = pymysql.connect(
                    host=DB_HOST,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    database=DB_NAME,
                    port=DB_PORT,
                    autocommit=True,
                    cursorclass=pymysql.cursors.Cursor
                )

                with connection.cursor() as cursor:
                    with open(SQL_FILE, "r") as f:
                        sql_commands = f.read().strip().split(";")

                    for command in sql_commands:
                        if command.strip():
                            cursor.execute(command.strip())

                print("✅ SQL file imported successfully.")
                connection.close()
            except pymysql.MySQLError as e:
                print(f"⛔ Error importing SQL file: {e}")
        else:
            print(f"⚠️ SQL file {SQL_FILE} not found, skipping import.")

    def test_containers_up(self):
        for service in ["mysql_server", "phpmyadmin"]:
            self.assertIn(service, self.containers, f"❌ Container {service} not found")

    def test_insert_and_retrieve_multiple_users(self):
        users_data = []
        user_test_num = 100

        for _ in range(user_test_num):
            user_data = {
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "email": fake.unique.email(),
                "phone": fake.unique.numerify(text="###############"),
                "password": fake.password(),
                "country": fake.country(),
                "state": fake.state(),
                "city": fake.city(),
                "address": fake.address(),
                "zip_code": fake.zipcode(),
                "date_of_birth": fake.date_of_birth(minimum_age=18, maximum_age=80).isoformat(),
                "gender": fake.random_element(["male", "female", "other"]),
                "profile_picture_url": fake.image_url(),
                "status": fake.boolean(),
                "is_verified": fake.boolean(),
                "bio": fake.text(),
                "preferences": '{}'
            }
            users_data.append(user_data)

        insert_query = """
        INSERT INTO users (first_name, last_name, email, phone, password, country, state, city, address, zip_code,
        date_of_birth, gender, profile_picture_url, status, is_verified, bio, preferences)
        VALUES (%(first_name)s, %(last_name)s, %(email)s, %(phone)s, %(password)s, %(country)s, %(state)s, %(city)s,
        %(address)s, %(zip_code)s, %(date_of_birth)s, %(gender)s, %(profile_picture_url)s, %(status)s, %(is_verified)s,
        %(bio)s, %(preferences)s)
        """

        connection = pymysql.connect(
                    host=DB_HOST,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    database=DB_NAME,
                    port=DB_PORT,
                    autocommit=True,
                    cursorclass=pymysql.cursors.DictCursor
                )

        with connection.cursor() as cursor:
            cursor.executemany(insert_query, users_data)

            for user_data in users_data:
                cursor.execute("SELECT * FROM users WHERE email = %s", (user_data["email"],))
                retrieved_user = cursor.fetchone()

                self.assertIsNotNone(retrieved_user, f"User with email {user_data['email']} was not inserted correctly")
                self.assertEqual(retrieved_user["email"], user_data["email"], "Retrieved email does not match")
                self.assertEqual(retrieved_user["first_name"], user_data["first_name"], "First name mismatch")
                self.assertEqual(retrieved_user["last_name"], user_data["last_name"], "Last name mismatch")

if __name__ == "__main__":
    unittest.main()
