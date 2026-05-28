from environs import Env

env = Env()
env.read_env()

BOT_TOKEN = env.str("BOT_TOKEN")
ADMINS = [int(admin_id) for admin_id in env.list("ADMINS")]
IP = env.str("ip")