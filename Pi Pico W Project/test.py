with open("code.txt", "r") as file:
    html=""
    for line in file:
        html+=str(line)
    html=html.replace("sensorValue", "LOL")
    print(html)