import subprocess
import unittest
import docker
import time
import os
import pymysql

SQL_FILE = "badrage-migration.sql"
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_USER = "user"
DB_PASSWORD = "password"
DB_NAME = "badrage_database"

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

if __name__ == "__main__":
    unittest.main()
