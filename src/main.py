from threading import Thread
import bot, websocket.app

worker = Thread(target=bot.run, daemon=True)
worker.start()
websocket.app.start()