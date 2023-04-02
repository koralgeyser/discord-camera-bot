from threading import Thread
import bot
import websocket.app

Thread(target=websocket.app.start, daemon=True).start()

try:
    bot.run()
except KeyboardInterrupt:
    print("exiting")
    exit(0)
