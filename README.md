Instrucciones para la ejecución del ambiente.

En este mismo directorio requieres ejecutar los siguientes comandos:
1. source flaskenv/bin/activate 
2. gunicorn -w 4 .b 0.0.0.0:5000 app:app

El primero prepara el ambiente de Python usando Flask.
El segundo utiliza el servicio gunicorn para servir la aplicación usando 4 hilos y el puerto 5000.

Este servicio está agregado a systemd como un demonio de ejecución automática, con el parámetro Restart: Always, esto significa que no se ejecuta
automáticamente en el momento en el que el servidor se enciende.

Para detenerlo en algún momento debemos ejecutar:
1. sudo systemctl stop media_server
2. sudo systemctl disable media_server
3. sudo rm /etc/systemd/system/media_server.service
4. sudo systemctl daemon reload
5. sudo systemctl reset-failed
