from machine import UART, Pin, SPI, Timer
import machine, onewire, ds18x20, time
from Housekeeping import housekeeping, Setup
from comms import comms, send_to_ground, send_to_sd, setup_antenna, init_sd
from ucollections import namedtuple
from tuppersat.radio import TupperSatRadio
import sdcard
import uos
import Radiation as r

time.sleep(5)
#print(Setup.setup_check)
def configure(pin_nums):
    #pin_nums = [6, 14, 15, 4, 5]
    #s = Setup(pin_nums)
    
    # initialise the sensors
    try:
        sensors = Setup(pin_nums)
        
    except:
        time.sleep(5)
        configure()
    #temperature_sensors = sensors.temp_sensors
    #print(temperature_sensors)
    #temperature_roms = sensors.temp_roms
    #print(temperature_roms)
    #pressure_sensor = sensors.pressure_i2c
    #gps_sensor = sensors.gps
    
    return sensors



def main():
    
    # At the top of main(), initialise as None
    #housekeeping_data = None
    radiation_data = None
    timestamp = 99999
    
    pin_nums = [6, 14, 15, 4, 5, 0, 1]
    sensors = configure(pin_nums)
    try:
        init_sd()
    except Exception as e:
        print("SD init failed:", e)
    
    try:
        radio = setup_antenna(pin_nums)
    except Exception as e:
        print("Radio init failed:", e)
        radio = None
        
    #housekeeping_data, radiation_data, timestamp = comms()
    #send_to_ground(radio, radiation_data, timestamp, "Rad")
    
    time_store = Timer(-1)
    time_house1 = Timer(-1)
    time_house2 = Timer(-1)
    time_send_rad = Timer(-1)
    
    store_house = False
    send_house1 = False
    send_house2 = False
    send_rad = False
    
    def store(t):
        nonlocal store_house
        store_house = True
    
    def send1(t):
        nonlocal send_house1
        send_house1 = True
        delay0.deinit()
        
    def send2(t):
        nonlocal send_house2
        send_house2 = True
        
    def send_r(t):
        nonlocal send_rad
        send_rad = True
    
    def init_house(t):
        time_house2.init(mode=Timer.PERIODIC, period=60000, callback=send2)
        send2(None)
        delay1.deinit()
        
    def start_rad(t):
        time_send_rad.init(mode=Timer.PERIODIC, period=60000, callback=send_r)
        send_r(None)
        delay2.deinit()
    
    time_store.init(mode=Timer.PERIODIC, period=10000, callback=store)
    store(None)
    
    delay0 = Timer(-1)
    
    delay0.init(mode=Timer.ONE_SHOT, period=1000, callback=send1)
    time_house1.init(mode=Timer.PERIODIC, period=60000, callback=send1)
    send1(None)
    
    delay1 = Timer(-1)
    delay2 = Timer(-1)
    
    delay1.init(mode=Timer.ONE_SHOT, period=20000, callback=init_house)
    
    delay2.init(mode=Timer.ONE_SHOT, period=40000, callback=start_rad)

    # In the while loop:
    #try:
    while True:
        if store_house:
            store_house = False
            try:
                # Refresh all data every 10 seconds
                housekeeping_data, radiation_data, timestamp = comms(sensors)
            except Exception as e:
                print("comms FAILED:", e)
                
            hk_data = []
            for data in housekeeping_data:
                data_str = str(data)
                if "Time" in data_str:
                    continue
                else:
                    hk_data.append(data_str)
            send_to_sd(hk_data)
            print("Storing Housekeeping")

        if send_house1:
            send_house1 = False
            print("Attempting to transmit housekeeping")
            send_to_ground(radio, housekeeping_data, timestamp, "House")
            #print("Sending Housekeeping")

        if send_house2:
            send_house2 = False
            print("Attempting to transmit housekeeping")
            send_to_ground(radio, housekeeping_data, timestamp, "House")
            #print("Sending Housekeeping")

        if send_rad:
            housekeeping_data, radiation_data, timestamp = comms(sensors)
            send_rad = False
            print("Attempting to transmit radiation")
            send_to_ground(radio, radiation_data, timestamp, "Rad")
            #print(radiation_data)
            r.count_reset()
            
            #print("Sending Radiation")

        time.sleep_ms(10)
        
    return

if __name__ == '__main__':
    main()
