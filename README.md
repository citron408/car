# Car Control (Simple)

This project is a tiny web-controlled car app.

- Web server: Flask app in `app.py`
- Frontend: HTML in `templates/index.html`
- Browser logic: JavaScript in `static/main.js`
- Backend handlers:
	- Motor actions (`forward`, `backward`, `left`, `turnRight`, `stop`)
	- LED toggle (`/api/led`)

## How It Works

1. You open the web page (`/`).
2. Buttons in the page call JavaScript functions.
3. JavaScript sends `POST` requests to backend API routes.
4. Flask routes call motor/LED GPIO logic.

## ASCII Architecture

```text
+-------------------------------------------+
| Laptop / Mobile                           |
| IP: 192.168.50.x                          |
| Browser UI                                |
| - templates/index.html                    |
| - static/main.js                          |
+--------------------+----------------------+
							|
							| Wi-Fi / LAN
							v
			  [Local Network 192.168.50.0/24]
							|
							| HTTP http://192.169.50.20:5000/
							| POST /api/... (forward/backward/left/turnRight/stop/led)
							v
+-------------------------------------------+
| Raspberry Pi                              |
| IP: 192.169.50.20:[port]                  |
| Flask app: app.py                         |
|    /api/<action>   /api/stop   /api/led   |
|    /api/status     /camera/stream         |
+-------------------+-----------------------+
						  |
						  v
			 +---------+----------+
			 |                    |
			 v                    v
	 [Motor handlers]      [LED handler]
		 motor.py              led.py
			 |                    |
			 +------ GPIO --------+
						  |
					 [Hardware]
```

## API Endpoints

- `POST /api/forward`
- `POST /api/backward`
- `POST /api/left`
- `POST /api/turnRight`
- `POST /api/stop`
- `POST /api/led`
- `GET /api/status`

## Autostart (systemd)

The app runs at boot via systemd. Unit file: `/etc/systemd/system/car-app.service`.

### Useful commands

```bash
sudo systemctl status car-app          # is it running?
sudo systemctl restart car-app         # restart it
sudo systemctl stop car-app            # stop without disabling
sudo systemctl disable --now car-app   # stop and remove from boot
sudo journalctl -u car-app -f          # follow logs live
```

### To completely remove the autostart

```bash
sudo systemctl disable --now car-app
sudo rm /etc/systemd/system/car-app.service
sudo systemctl daemon-reload
```
