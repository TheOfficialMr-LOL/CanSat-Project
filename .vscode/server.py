import os
import network
from time import sleep
import socket
import random

from machine import Pin
global pin
pin=Pin("LED", Pin.OUT)




def get_image(image_name):
    try:
        with open(image_name, "rb") as image_file:
            return image_file.read()
    except OSError as e:
        print(f"Error reading image {image_name}: {e}")
        return None

def serve_image(conn, image_name):
    image_data = get_image(image_name)
    if image_data:
        conn.send(b'HTTP/1.0 200 OK\r\nContent-type: image/png\r\n\r\n')
        # Send the image data in chunks
        chunk_size = 1024
        for i in range(0, len(image_data), chunk_size):
            conn.sendall(image_data[i:i+chunk_size])
    else:
        conn.send(b'HTTP/1.0 404 Not Found\r\nContent-type: text/html\r\n\r\n')
        conn.send(b'<html><body><h1>404 Not Found</h1></body></html>')
    conn.close()






def web_page(pressure, NDVI_Index, acceleration, temperature):
    with open("code.txt", "r") as file:
        html=""
        for line in file:
            html+=str(line)

        """
        # updating web page with sensor value
        html=html.replace("P0.00", str(pressure))
        html=html.replace("T0.00", str(NDVI_Index))
        html=html.replace("N0.00", str(acceleration))
        html=html.replace("A0.00", str(temperature))
        """

    return html

def get_sensor_data():
    pressure=round(random.randint(0, 9999)/100, 2)
    temperature=round(random.randint(0, 9999)/100, 2)
    NDVI_Index=round(random.randint(0, 9999)/100, 2)
    acceleration=round(random.randint(0, 9999)/100, 2)

    return pressure, temperature, NDVI_Index, acceleration

def write_sensor_data(conn, connection_delay):
    print("Writing sensor data")
    
    # retrieving sensor values
    pressure, temperature, NDVI_Index, acceleration=get_sensor_data()

    # writing webpage
    response = web_page(pressure, temperature, NDVI_Index, acceleration)
    content_length = len(response.encode("utf-8"))

    try:
        conn.send(b'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')  # Use bytes for the header
        conn.send(f'Content-Length: {content_length}\r\n'.encode('utf-8'))
        conn.send(b'\r\n')  # End of headers
        conn.sendall(response.encode('utf-8'))  # Ensure response is sent as bytes

    except Exception as e:
        print("Failed to send response:", e)
    finally:
        sleep(connection_delay)
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
                request=conn.recv(1024).decode("utf-8")
                #print("Request:", request)
                #print(request[0])
                print("IP address to connect to: " + ap.ifconfig()[0])
                #performing tasks based on request headers



                #handling image requests
                if "GET /Pressure&Temperature.png" in request:
                    serve_image(conn, "images/Pressure&Temperature.png")
                elif "GET /NDVI.png" in request:
                    serve_image(conn, "images/NDVI.png")
                elif "GET /CanMotion.png" in request:
                    serve_image(conn, "images/CanMotion.png")



                #handling file requests (libraries)
                elif "GET /chart.umd.js" in request:
                    conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/javascript\r\n\r\n")
                    with open('javascript_libraries/chart.umd.js', 'r') as file:
                        while True:
                            chunk = file.read(2048)  # Read in 1KB chunks
                            if not chunk:
                                break

                            conn.send(chunk)

                elif "GET /regression.min.js" in request:
                    conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/javascript\r\n\r\n")
                    with open('javascript_libraries/regression.min.js', 'r') as file:
                        while True:
                            chunk = file.read(1024)  # Read in 1KB chunks
                            if not chunk:
                                break
                            conn.send(chunk)



                    

                #handling data requests
                elif("Switch-On" in request):
                    print("Request to switch on was recieved!")
                    pin.on()
                    conn.send("LOL")
                    conn.close()
                
                elif("Switch-Off" in request):
                    print("Request to switch off was recieved!")
                    pin.off()
                    conn.send("LOL")
                    conn.close()

                elif("Write-Data" in request):
                    print("Writing sensor data")

                    pressure, temperature, NDVI_Index, acceleration=get_sensor_data()
                    data=f"1.0,{pressure},{temperature},{NDVI_Index},{acceleration}"
                    conn.send(data)
                    conn.close()
                
                else:
                    print("Writing initial web page")
                    write_sensor_data(conn, 3)


                print("connection closed!")
            except OSError as e:
                print("Connection error:", e)
                # If there's an error, we can close the connection
                conn.close()

    main_program()

ap_mode("PiPico", "pass1234")
