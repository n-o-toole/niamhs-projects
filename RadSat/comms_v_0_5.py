from machine import UART, Pin, SPI
import machine, onewire, ds18x20, time
from Housekeeping import housekeeping
from ucollections import namedtuple
from tuppersat.radio import TupperSatRadio
import sdcard
import uos
import Radiation as r




def setup_antenna(pin_nums):
    """
    Initialise the antenna.
    """
    # extract tx and rx pins and define constants
    UART_ID = 0
    TX_PIN = pin_nums[-2]
    RX_PIN = pin_nums[-1]
    T3_BAUDRATE = 38400

    ADDRESS = 0xfe
    CALLSIGN = 'RADSAT'
    
    # create the UART interface
    uart = UART(UART_ID, baudrate=T3_BAUDRATE, tx=Pin(TX_PIN), rx=Pin(RX_PIN))
    # create a TupperSatRadio object
    radio = TupperSatRadio(uart, ADDRESS, CALLSIGN)
    
    return radio


def chunk(string, n):
    """Break a string into chunks of length n."""
    return (string[i:i+n] for i in range(0, len(string), n))


def parse_time(time_str):
    """Parse a time string HHMMSS.SSS into a Time object."""
    
    Time = namedtuple('Time', 'hour minute second microsecond')

    # split out the second and sub-second times
    _hhmmss, _milliseconds = time_str.split('.')

    # compute the sub-second time in microseconds
    _us = int(_milliseconds) * 1000

    # compute the hours, minutes and seconds
    _hh, _mm, _ss = (int(x) for x in chunk(_hhmmss, 2))

    return Time(_hh, _mm, _ss, _us)

def get_default_time():
    year, month, date, hour, minutes, seconds, *_ = time.localtime()
    
    time_string = str(hour)+str(minutes)+str(seconds) + ".00"
    return time_string

def fetch_raw_data(sensors):
    """
    Fetch the output from Housekeeping.py
    
    Parameters:
    -----------
    None
    
    Returns:
    --------
    temp_int: float
    temp_ext: float
    pressure: float
    latitude: float
    longitude: float
    altitude: float
    radiation: float
    """
    
    try:
        temp_int, temp_ext, press, GPS_data = housekeeping(sensors)
    except Exception as e:
        print(e)
        print("Failed at reading housekeeping")
        #temp_int, temp_ext, press, GPS_data = None, None, None, None

    if temp_int is not None:
        int_temp = temp_int
    else:
        int_temp = None
        
    if temp_ext is not None:
        ext_temp = temp_ext
    else:
        ext_temp = None
        
    if press is not None:
        pressure = press
    else:
        pressure = None
        
    if GPS_data is not None:
        gps_data = GPS_data
    else:
        gps_data = None
        
    return int_temp, ext_temp, pressure, gps_data

def init_sd():
    """
    Take the CSV file from fetch_clean_data() and send it to the local SD
    file for storage.
    
    Parameters:
    -----------
    transfer_data: file
        CSV file of clean data
        
    Returns:
    --------
    None
    """
    cs = Pin(9, Pin.OUT)
    spi = SPI(1,
              baudrate=1000000,
              polarity=0,
              phase=0,
              bits=8,
              firstbit=machine.SPI.MSB,
              sck=machine.Pin(10),
              mosi=machine.Pin(11),
              miso=machine.Pin(8))
    
    try:
        sd = sdcard.SDCard(spi, cs)
    except Exception as e:
        print(f"Error mounting SD: {e}")
        
    vfs = uos.VfsFat(sd)
    try:
        uos.umount("/sd")
    except OSError as e:
        print(f"Unmount error: {e}")
    
    try:
        uos.mount(vfs, "/sd")
    except OSError as e:
        print(f"Mount error: {e}")
    
    header = "int_temp, ext_temp, pressure, longitude, latitude, altitude, timestamp, hdop"
    try:
        file = open("/sd/housekeeping.csv", "a")
        file.write(header + "\n")
#         file.write(str(time.time()))
#         file.write(",")
#         for val in data:
#             file.write(val)
#             file.write(",")
#         file.write("\n")
        file.close()
    except OSError as e:
        print(f"SD Error - Write , {e}")
        
    return

def send_to_sd(data):
    
    try:
        file = open("/sd/housekeeping.csv", "a")
        file.write(str(time.time()))
        file.write(",")
        for val in data:
            file.write(val)
            file.write(",")
        file.write("\n")
        file.close()
    except OSError as e:
        print("SD Error - Append, {e}")        

    return

def send_to_ground(radio, data, timestamp, kind=str):
    """
    Take the CSV file from fetch_clean_data() and send it to the ground
    station.
    
    Parameters:
    -----------
    transfer_data: file
        CSV file of clean data
        
    Returns:
    --------
    None
    """
    
    print("Attempting to transmit to ground...")
    
    if "House" in kind:
        if data is not None:
        
            t_int = data[0]
            t_ext = data[1]
            p = data[2]
            long = data[3]
            lat = data[4]
            alt = data[5]
            t = data[6]
            hd = data[-1]

            
            radio.send_telemetry(
                hhmmss     = t,
                latitude   = lat,
                longitude  = long,
                hdop       = hd,
                altitude   = alt,
                t_internal = t_int,
                t_external = t_ext,
                pressure   = p,
            )
            
        else:
            t_sys = parse_time(get_default_time())
            
            radio.send_telemetry(
                hhmmss     = t_sys,
                latitude   = 99999,
                longitude  = 99999,
                hdop       = 99999,
                altitude   = 99999,
                t_internal = 99999,
                t_external = 99999,
                pressure   = 99999
            )
            
    if "Rad" in kind:
        if data is not None:
            # Format as a compact CSV string, encode to bytes
            if data[1] is not None:
                try:
                    rad_string = "{},{:.2f},{:.2f}".format(timestamp[0], data[0], data[1])
                except:
                    rad_string = "{},{:.2f},{:.2f}".format(timestamp, data[0], data[1])
            else:
                try:
                    rad_string = "{},{:.2f},{:.2f}".format(timestamp[0], data[0], 999999)
                except:
                    rad_string = "{},{:.2f},{:.2f}".format(timestamp, data[0], 999999)
            rad_bytes = rad_string.encode('utf-8')
            
            radio.send_data(rad_bytes)
            print("Rad packet ({} bytes): {}".format(len(rad_bytes), rad_string))
            
        else:
            rad_string = "99999,99999,99999"
            radio.send_data(rad_string.encode('utf-8'))
            print("No radiation data")
    
    return

def comms(sensors):
    pin_nums = [6, 14, 15, 4, 5, 0, 1]

    
    # initialise antenna
    #radio = setup_antenna(pin_nums)    
    
    Exceptions = []
    
    try:
        int_temp, ext_temp, pressure, GPS_data = fetch_raw_data(sensors)
    except Exception as e:
        Exceptions.append(e)
        print("Comms: Couldn't fetch data")
        
    # extract data
    if GPS_data is not None:
        try:
            raw_sentence = GPS_data['sentence'][-1]
        except Exception as e:
            raw_sentence = None
        try:
            latitude = round(float(GPS_data['latitude'][0]), 4)
        except Exception as e:
            latitude = None
        try:
            longitude = round(float(GPS_data['longitude'][0]), 4)
        except Exception as e:
            longitude = None
        try:
            altitude = round(float(GPS_data['altitude'][0]), 2)
        except Exception as e:
            altitude = None
        try:
            timestamp = GPS_data['timestamp']
        except Exception as e:
            timestamp = None
            
        try:
            checksum = GPS_data['checksum'][0]
        except Exception as e:
            checksum = None
        try:
            hdop = round(float(GPS_data["hdop"][0]), 2)
        except Exception as e:
            hdop = None
    else:
        raw_sentence = None
        latitude = None
        longitude = None
        altitude = None
        timestamp = None
        checksum = None
        hdop = None
        
    # parse time to correct format for sending telemetry
    try:
        data_time = parse_time(timestamp[0])
    except Exception as e:#IndexError:
        data_time = None
        print("Comms: Couldn't parse time")
        
    housekeeping_data = [int_temp, ext_temp, pressure, longitude, latitude, altitude, data_time, hdop]
    
    total_count, loop_count = r.count_fetch()
    radiation_data = [loop_count,altitude]
    #r.Radiation.write_sd()
#     if timestamp is not None:
#         time_now = timestamp[0]
#     else:
#         time_now = 99999
    
    #send_to_ground(radio, radiation_data, "Rad") 
    
    return housekeeping_data, radiation_data, timestamp

     
if __name__ == '__comms__':
    comms()
