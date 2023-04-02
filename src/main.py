from threading import Thread
import bot, websocket.app

x = Thread(target=websocket.app.start, daemon=True)
x.start()

try:
    bot.run()
except KeyboardInterrupt:
    print("exiting")
    exit(0)