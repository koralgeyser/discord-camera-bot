from threading import Thread
import bot
import websocket.app

Thread(target=websocket.app.start, daemon=True).start()

try:
    bot.run()
except KeyboardInterrupt:
    exit(0)
