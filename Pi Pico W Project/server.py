import network
from utime import sleep
import socket
import random

def web_page(sensorValue):
    html=f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta http-equiv="refresh" content="5">
    <meta name="viewport" content="width=device-width, initial-scale=1"></head>
    <body>

    <h1 style="text-align: center;">Hello World</h1>
    <h2><u>Simulating real-time data</u></h2>
    <br>
    <br>
    <h3>Random sensor data: {sensorValue} units</h3>
    </body>
    <script>console.log("Hello world!")</script>
    </html>
    """
    return html

def write_sensor_data(conn):
    print("Writing sensor data")
    
    sensorValue = random.randint(100, 900)
    print(sensorValue)
    response = web_page(sensorValue)

    try:
        conn.send(b'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')  # Use bytes for the header
        conn.send(response.encode('utf-8'))  # Ensure response is sent as bytes
    except Exception as e:
        print("Failed to send response:", e)
    finally:
        sleep(3)
        conn.close()  # Ensure the connection is closed

def ap_mode(ssid, password):
    ap = network.WLAN(network.AP_IF)
    ap.config(essid=ssid, password=password)
    ap.active(True)

    while not ap.active():
        sleep(1)  # Wait until the access point is active

    print("AP mode is active! You may now connect")
    print("IP address to connect to: " + ap.ifconfig()[0])

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 80))
    s.listen(5)

    def main_program():
        while True:
            try:
                print("waiting for next connection...")
                conn, addr = s.accept()
                print("Got a connection from %s" % str(addr))
                write_sensor_data(conn)
                print("connection closed!")
            except OSError as e:
                print("Connection error:", e)
                # If there's an error, we can close the connection
                conn.close()

    main_program()

ap_mode("PiPico", "pass1234")
