"""
CanSat Groundstation Server
Team Rooted_in_Data
2024/25


Developed by TheOfficialMr_LOL


Notes:
-- I should probably remove all the LED control commands due to redundancy

-- Achieved full asynchronous server performance (and I also haven't noticed a random connection error since this
implementation)

-- Each time this server is first executed, a new CSV file is generated, which is used to ensure
no data is lost. This means that unused, redundant files will need to be deleted regulary to circumvent
memory overload

"""


import network
import socket
import random
import ujson
import uasyncio as asyncio
from machine import Pin, SPI
import rfm9x

#initializing pins
pin = Pin("LED", Pin.OUT)

SCK=0
MOSI=0
MISO=0
CS=0
RESET=0

#lora module initialization
spi=SPI(1, baudrate=5000000, polarity=0, phase=0, sck=Pin(SCK), mosi=Pin(MOSI), miso=Pin(MISO))

# Initialize RFM9x module (frequency in MHz)
rfm9x = rfm9x.RFM9x(spi, CS, RESET, frequency=433.0)



#storing data
data=[
    ['Pressure','Temperature','Altitude','Acceleration', 'x-axis', 'y-axis', 'z-axis', 'Displacement', 'Time'],
]


#function to read image files
def get_image(image_name):
    try:
        with open(image_name, "rb") as image_file:
            return image_file.read()
    except OSError as e:
        print(f"Error reading image {image_name}: {e}")
        return None

#asynchronous function to serve images
async def serve_image(writer, image_name):
    image_data = get_image(image_name)
    if image_data:
        await writer.awrite(b'HTTP/1.0 200 OK\r\nContent-type: image/png\r\n\r\n')
        chunk_size = 1024
        for i in range(0, len(image_data), chunk_size):
            await writer.awrite(image_data[i:i+chunk_size])
    else:
        await writer.awrite(b'HTTP/1.0 404 Not Found\r\nContent-type: text/html\r\n\r\n')
        await writer.awrite(b'<html><body><h1>404 Not Found</h1></body></html>')

    await writer.aclose()

#function to read HTML files
def web_page():
    try:
        with open("code.txt", "r") as file:
            return file.read()
    except OSError:
        return "<html><body><h1>Error: File Not Found</h1></body></html>"

time=0

#handling client requests
async def handle_client(reader, writer):
    try:
        request = await reader.read(1024)
        request = request.decode("utf-8")

        if not request:
            await writer.aclose()
            return

        #print("Received request:", request)

        #handling image requests
        if "GET /Pressure&Temperature.png" in request:
            await serve_image(writer, "images/Pressure&Temperature.png")
        elif "GET /NDVI.png" in request:
            await serve_image(writer, "images/NDVI.png")
        elif "GET /CanMotion.png" in request:
            await serve_image(writer, "images/CanMotion.png")

        #handling JavaScript file requests
        elif "GET /chart.umd.js" in request:
            await serve_js(writer, "javascript_libraries/chart.umd.js")
        elif "GET /regression.min.js" in request:
            await serve_js(writer, "javascript_libraries/regression.min.js")

        #handling LED control
        elif "Switch-On" in request:
            print("Turning LED ON")
            pin.on()
            await writer.awrite(b"LED is ON")
            await writer.aclose()
        elif "Switch-Off" in request:
            print("Turning LED OFF")
            pin.off()
            await writer.awrite(b"LED is OFF")
            await writer.aclose()

        #handling sensor data request
        elif "Write-Data" in request:
            print("Sending sensor data")
            """
            pressure, temperature, altitude, time, velocity, acceleration = get_sensor_data()
            data = f"1.0,{pressure},{temperature},{altitude},{time},{velocity},{acceleration}"
            """
            localResponse=ujson.dumps({'data': data}) #convert data to JSON
            
            await writer.awrite(b'HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n')
            await writer.awrite(localResponse.encode('utf-8'))
            await writer.aclose()

        #default: Serve the HTML page
        else:
            response = web_page()
            await writer.awrite(b'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
            await writer.awrite(response.encode('utf-8'))
            await writer.aclose()

    except Exception as e:
        print("Error handling request:", e)
        await writer.aclose()

#serve JavaScript files properly (read and send in chunks)
async def serve_js(writer, filename):
    try:
        print(f"Attempting to serve {filename}...")  #debugging log

        #checking if file exists
        try:
            with open(filename, "rb") as file:
                content = file.read(1024)  # Read the file in chunks (1024 bytes)
                while content:
                    await writer.awrite(content)
                    content = file.read(1024)  # Read next chunk
        except OSError:
            print(f"File {filename} not found.")  # Debugging log
            await writer.awrite(b'HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\n')
            await writer.awrite(b'File not found')
            return

        #send the correct response headers for JS file (how about I don't send this?) -- yep, didn't need to send it LOL
        #await writer.awrite(b'HTTP/1.1 200 OK\r\nContent-Type: application/javascript\r\n\r\n')

    except OSError as e:
        print(f"Error serving file {filename}: {e}")
        await writer.awrite(b'HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\n')
        await writer.awrite(b'File not found')

    finally:
        await writer.aclose()  # Always close the connection


#start the Access Point mode
async def ap_mode(ssid, password):
    ap = network.WLAN(network.AP_IF)
    ap.config(essid=ssid, password=password)
    ap.active(True)

    while not ap.active():
        await asyncio.sleep(1)

    print("AP mode active at:", ap.ifconfig()[0])

    #web server initiation
    server = await asyncio.start_server(handle_client, "0.0.0.0", 80)

    while True:
        await asyncio.sleep(1)  # Keep the server running

#data logging from lora module function
async def gather_data(filename):
    while True:

        packet=rfm9x.receive(timeout=1.0) #wait up to 1 second for a packet
        if packet is not None:
            try:
                rawData=packet.decode('utf-8').split(',')

                #extracting data from the packet
                heading_z_axis=int(rawData[0])
                roll_x_axis=int(rawData[1])
                pitch_y_axis=int(rawData[2])
                accx=float(rawData[3]) #not using this
                verticalAcceleration=float(rawData[4]) 
                accz=float(rawData[5])  #not using this
                temperature=float(rawData[6])
                pressure=float(rawData[7])
                altitude=float(rawData[8])
                displacement=float(rawData[9])
                time=int(rawData[10])

                #updating the data list
                data.append([pressure, temperature, altitude, verticalAcceleration, roll_x_axis, pitch_y_axis, heading_z_axis, displacement,time])

                #writing data to file
                update_file(filename, pressure, temperature, altitude, verticalAcceleration, roll_x_axis, pitch_y_axis, heading_z_axis, displacement, time)
            
            except Exception as e:
                print('Error decoding packet:', e)

        await asyncio.sleep(0.1) #wait 0.1 seconds before next cycle


#creating a new CSV file for data logging
def create_new_csv_file():
    count = 1
    while True:
        try:
            file = open(f'data{count}.csv', 'x')
            break
        except OSError:
            count += 1
    file.close()

    #writing headers
    with open(f'data{count}.csv', 'w') as file:
        file.write('Pressure,Temperature,Altitude,Time,Velocity,Acceleration\n')

    return f'data{count}.csv'

#appending new sensor data to the file
def update_file(filename, pressure, temperature, altitude, acceleration, roll_x_axis, pitch_y_axis, heading_z_axis, displacement, time):
    with open(filename, 'a') as file:

        file.write(f"{pressure},{temperature},{altitude},{acceleration},{roll_x_axis},{pitch_y_axis},{heading_z_axis},{displacement},{time}\n")
    #print('Updated file:', filename)

#main function
async def main():
    filename = create_new_csv_file()
    print('Logging data to:', filename)
    await asyncio.gather(ap_mode("PiPico", "pass1234"), gather_data(filename))

#main loop
asyncio.run(main())
