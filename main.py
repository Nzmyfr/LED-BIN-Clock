from micropython import const
from machine import Timer, Pin, I2C
import ssd1306

import secrets
import network
import socket
import struct
import time

NTP_DELTA = const(2208988800)
host = const("pool.ntp.org")

def connect_to_network(wlan):
    wlan.active(True)
    wlan.config(pm = 0xa11140)  # Disable power-save mode
    wlan.connect(secrets.SSID, secrets.PASSWORD)

    max_wait = 1000
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print('waiting for connection...')
        time.sleep(1)

    if wlan.status() != 3:
        raise RuntimeError('network connection failed')
    else:
        status = wlan.ifconfig()
        print(f'ip = {status[0]}')
# End of connect_to_network

# Get time from Internet - https://gist.github.com/aallan/581ecf4dc92cd53e3a415b7c33a1147c
def set_time():
    NTP_QUERY = bytearray(48)
    NTP_QUERY[0] = 0x1B

    # Open socket to the DNS address of the NTP server
    addr = socket.getaddrinfo(host, 123)[0][-1]

    # Create an UDP socket for communication with the NTP server
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(1)                  # Set a timeout of 1 second for the socket operations
        res = s.sendto(NTP_QUERY, addr)  # Send the NTP query to the server
        msg = s.recv(48)                 # Receive the response (48 bytes) from the server
    finally:
        s.close()                        # Ensure the socket is closed after communication
    val = struct.unpack("!I", msg[40:44])[0]
    t = val - NTP_DELTA + 3*3600         # Bulgarian summer time
    tm = time.gmtime(t)                  # Convert the timestamp to a time tuple

    # Update the Real-Time Clock (RTC) with the new time
    machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
# End of set_time()

def update_time(rtc,led_hours,led_dot,led_minutes,led_seconds,oled):
    print(rtc.datetime())
    timestamp = rtc.datetime()
    seconds = timestamp[6]
    binary_seconds = f"{seconds:06b}"
    minutes = timestamp[5]
    binary_minutes = f"{minutes:06b}"
    hours = timestamp[4]
    
    if hours < 12:
        hours_12 = hours
        led_dot.off()
    elif hours == 12:
        hours_12 = 12
        led_dot.on()
    else:
        hours_12 = hours - 12
        led_dot.on()
    binary_hours = f"{hours_12:04b}"
    
    for i in range(6):
        led_seconds[5-i].value(int(binary_seconds[i]))
        led_minutes[5-i].value(int(binary_minutes[i]))
        if i < 4:
            led_hours[3-i].value(int(binary_hours[i]))
    
    oled.fill(0)
    if hours < 12:
        ampm="AM"
    else:
        ampm="PM"
    oled.text(f"{hours_12:02}:{minutes:02}:{seconds:02} {ampm}", 20, 12)
    oled.show()
# End of update_time()

def main():
    # display initialization
    i2c = I2C(1, scl=Pin(3), sda=Pin(2))
    oled_width = const(128)
    oled_height = const(32)
    oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)

    # clock initialization
    rtc = machine.RTC()

    # LED pins initialization
    led_hours = [Pin(pin, Pin.OUT) for pin in [18, 20, 12, 13]]
    led_dot = Pin(11, Pin.OUT)
    led_minutes = [Pin(pin, Pin.OUT) for pin in [21, 22, 9, 8, 10, 19]]
    led_seconds = [Pin(pin, Pin.OUT) for pin in [27, 28, 5, 6, 7, 26]]
    internal_led = Pin('LED',Pin.OUT)
    
    # Get current time from intenet
    wlan = network.WLAN(network.STA_IF)
    try:
        connect_to_network(wlan)
        set_time()
        #print(time.localtime())
    except Exception as ex:
        print(f"Can't get time from Internet: {ex}")

    # Start update timer 
    Timer().init(period=1000, mode=Timer.PERIODIC, callback=lambda t: update_time(rtc,led_hours,led_dot,led_minutes,led_seconds,oled))
    
    #Start internal led
    Timer().init(period=500, mode=Timer.PERIODIC, callback=lambda t1: internal_led.toggle())
    
# Run the program
main()