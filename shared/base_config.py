from pydantic_settings import BaseSettings


class BaseServiceConfig(BaseSettings):
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str = "admin"
    mqtt_password: str = "password"
