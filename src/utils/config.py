import configparser


class Config:
    def __init__(self, path: str = "config.ini"):
        self.config = configparser.ConfigParser()
        self.config.read(path)

    def bot_token(self) -> str:
        return self.config["BOT"]["token"]
    def postgresql_user(self) -> str:
        return self.config["POSTGRESQL"]["user"]
    def postgresql_password(self) -> str:
        return self.config["POSTGRESQL"]["password"]
    def postgresql_host(self) -> str:
        return self.config["POSTGRESQL"]["host"]
    def postgresql_port(self) -> str:
        return self.config["POSTGRESQL"]["port"]
    def postgresql_database(self) -> str:
        return self.config["POSTGRESQL"]["database"]