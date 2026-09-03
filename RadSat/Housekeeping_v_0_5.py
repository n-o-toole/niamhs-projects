#!/usr/bin/env python 3
"""
Description:
Performs housekeeping.

"""

import machine, onewire, ds18x20, time
from machine import UART, Pin
from gps_airborne import set_airborne_mode

class Setup:
    def __init__(self, pin_nums):
        """
        Initialise DS18B20 temperature sensors, MCP3008 pressure
        sensor, LEA-G6 GPS module for connection to the Pico.
        
        Parameters:
        -----------
        pin_nums: list
            List of pin numbers for each sensor
            
        Returns:
        --------
        temp_sensors:
            connected temperature sensors
        temp_roms: list
            addresses of the sensors
        pressure_i2c: i2c
            i2c interface for pressure sensor
        gps: uart
            uart port for gps sensor
        
        """
        # Initialise DS18B20 temperature sensors
        # extract signal pin number for temp sensors
        self.temp_pin = pin_nums[0]
        # define one wire pin
        self.one_wire_pin = machine.Pin(self.temp_pin)
        # scan for all connected temp sensors
        self.temp_sensors = ds18x20.DS18X20(onewire.OneWire(self.one_wire_pin))
        # find the addresses of the sensors
        self.temp_roms = self.temp_sensors.scan()
        #print(self.temp_sensors.scan())
        
        
        # Intialise MCP3008 pressure sensor
        # extract sda and scl pin numbers
        self.pressure_sda = pin_nums[1]
        self.pressure_scl = pin_nums[2]
        
        # set up the i2c interface
        self.pressure_i2c = machine.I2C(1, scl = machine.Pin(self.pressure_scl), sda = machine.Pin(self.pressure_sda))
        
        
        # Initialise LEA-G6 GPS module
        # extract rx and tx pin numbers
        self.gps_rx = pin_nums[4]
        self.gps_tx = pin_nums[3]
        # set up uart port
        self.gps = UART(1, baudrate=9600, tx=Pin(self.gps_tx), rx=Pin(self.gps_rx),timeout=10, timeout_char = 10)
        #set_airborne_mode(self.gps)
        self.gps.init(9600, bits=8, parity=None, stop=1)
        print('GPS in Airborne Mode :)')

def temperature(sensors, roms):
    """
    Reads temperatures from all connected sensors and prints to the screen
    
    Parameters:
    -----------
    sensors: connected temp sensors
    roms: addresses of sensors
    
    Returns:
    --------
    inter: float
        internal temperature
    ext: float
        external temperature
    """
    # tell the sensor you want to make a measurement
    sensors.convert_temp()
    
    # set time in between reading
    time.sleep_ms(750)

    
    # extract the temperatures for each sensor
    for rom in roms:
        #print(rom)
        if unpack(rom) == 2890613028871471277:
            inter = sensors.read_temp(rom)
        if unpack(rom) == 2954110846270637218:
            ext = sensors.read_temp(rom)

    print(inter,ext)
    return inter, ext

def unpack(buffer):
    _buffer = reversed(bytearray(buffer))
    return sum(_byte << (_i * 8) for _i, _byte in enumerate(_buffer))

def calibration(bus, addr):
    """
    Reads the 6 calibration constants for the provided bus and address
    and returns them in a list.
    
    Parameters:
    -----------
    bus: i2c
        bus being used
    addr: int
        address of bus
        
    Returns:
    --------
    C: list
        list of calibration constants
    """
    # the 6 calibration constants are stored in the following registry positions:
    # 0xA2, 0xA4, 0xA6, 0xA8, 0xAA, 0xAC
    
    # read each calibration constant
    # use the unpack function to reassemmble the constant into a single integer
    c1bytes = bus.readfrom_mem(addr, 0xA2, 2)
    c1 = unpack(c1bytes)

    c2bytes = bus.readfrom_mem(addr, 0xA4, 2)
    c2 = unpack(c2bytes)

    c3bytes = bus.readfrom_mem(addr, 0xA6, 2)
    c3 = unpack(c3bytes)

    c4bytes = bus.readfrom_mem(addr, 0xA8, 2)
    c4 = unpack(c4bytes)

    c5bytes = bus.readfrom_mem(addr, 0xAA, 2)
    c5 = unpack(c5bytes)

    c6bytes = bus.readfrom_mem(addr, 0xAC, 2)
    c6 = unpack(c6bytes)
    
    # create a list to store the calibration constants
    C = [None, c1, c2, c3, c4, c5, c6]
    
    return C

def read_adc(bus, addr, cmd):
    """
    Returns the pressure and or temperature ADC value as an integer
    depending on the value of cmd; b'\x48' to request the temperature
    ADC value or b'\x58' to request the pressure ADC value.
    
    Parameters:
    -----------
    bus: i2c
        bus being used
    addr: int
        address of bus
    cmd: str
        b'\x48' or b'\x58'
        
    Returns:
    --------
    adc: int
        integer ADC value of temp or pressure
    """
    # send temperature ADC command and pause for response
    bus.writeto(addr, cmd)
    time.sleep_ms(50)
    # read the temperature ADC values
    adc_bytes = bus.readfrom_mem(addr, 0x00, 3)
    # unpack value as integer
    adc = unpack(adc_bytes)
    
    return adc

def compute_pressure(D1, D2, C):
    """
    The uncalibrated temperature and pressure ADC values are taken
    along with the calibration constants and the calibrated pressure
    and temperature values are calculated and returned.
    
    Parameters:
    -----------
    D1: int
        pressure ADC value
    D2: int
        temp ADC value
    C: list
        calibration constants
        
    Returns:
    --------
    P: int
        calibrated pressure
    TEMP: int
        calibrated temp
    """
    # find temperature difference
    dT = D2 - C[5] * 2**8
    
    # find actual temp
    TEMP = 2000 + dT * C[6] / 2**23
    
    # offset
    OFF = C[2] * 2**16 + (C[4]*dT) / 2**7
    
    # sensitivity
    SENS = C[1] * 2**15 + (C[3]*dT) / 2**8
    
    # find actual pressure
    P = (D1 * SENS/2**21 - OFF) / 2**15
    
    return P, TEMP

def read_pressure(bus, addr):
    """
    Returns the pressure and temperature.
    
    Parameters:
    -----------
    bus: i2c
        bus being used
    addr: int
        address of bus
        
    Returns:
    --------
    P: float
        pressure value
    """
    # find calibration constants
    C = calibration(bus, addr)
    
    # find pressure and temp ADC values
    t_adc = read_adc(bus, addr, b'\x48')
    p_adc = read_adc(bus, addr, b'\x58')

    # find calibrated temperature and pressure
    pressure, t = compute_pressure(t_adc, p_adc, C)
    
    p = pressure/100
    
    return p

def ddmm_to_decimal(ddmm_str):
    """Convert DDMM.MMMMMM or DDDMM.MMMMMM format to decimal degrees.

    Parameters:
    -----------
    ddmm_str: str
        DDMM.MMMMMM string
        
    Returns:
    --------
    decimal_degrees: float
         decimal degrees
    """
    # check if the string is empty
    if not ddmm_str or ddmm_str == '':
        return None
    
    # convert to decimal degrees
    ddmm = float(ddmm_str)
    degrees = int(ddmm / 100)
    minutes = ddmm - (degrees * 100)
    decimal_degrees = degrees + (minutes / 60.0)
    
    return decimal_degrees

def to_signed_angle(decimal_degrees, direction):
    """
    Convert to signed angle based on direction (N/S/E/W).

    Parameters:
    -----------
    decimal_degrees: float
        decimal degrees
    direction: str
        'N', 'S', 'E', or 'W'
        
    Returns:
    --------
    decimal_degrees: float
        neg or pos decimal degrees depending on direction
        
    """
    # check if decimal degrees or direction are empty strings
    if decimal_degrees is None or not direction:
        return None
    
    # if direction is S/W, decimal_degrees is neg, else pos
    if direction in ['S', 'W']:
        return -decimal_degrees
    else:
        return decimal_degrees

def parse_nmea(sentence):
    """
    Parse NMEA sentence and extract latitude, longitude, altitude, timestamp.
    
    Parameters:
    -----------
    sentence: str
        NMEA sentence
        
    Returns:
    --------
    result: dict
        dictionary with latitude, longitude, altitude, and timestamp data
    """
    # create a dictionary to store the results
    result = {
    'longitude': [],
    'latitude': [],
    'altitude': [],
    'timestamp': [],
    'sentence': [],
    'checksum': [],
    'fields': [],
    'hdop': []
    }
    
    # clean the sentence
    sentence = sentence.strip()
    
    # extract the checksum 
    if '*' in sentence:
        sentence_part, checksum = sentence.split('*')
        result['checksum'].append(checksum)
    else:
        sentence_part = sentence
    
    # split the sentence at commas
    parts = sentence_part.split(',')
    # find the sentence type
    sentence_type = parts[0][1:]
    # the fields are the rest of the sentence
    fields = parts[1:]
    
    # add the sentence_type and fields to the dictionary
    result['fields'] = {
        'sentence_type': sentence_type,
        'data': fields
    }
    
    # check for GGA sentences
    if 'GGA' in sentence_type:
        result['sentence'].append(sentence)
        # if the length is not greater/equal to 9, there is data missing
        if len(fields) >= 9 and fields[1]:
            # extract the timestamp
            if fields[0]:
                time_str = fields[0]
                if time_str == "":
                    # add N/A to dictionary is timestamp is empty
                    result['timestamp'].append("N/A")
                else:
                    # format the timestamp and add to the dictionary
                    result['timestamp'].append(time_str)
                    #f"{time_str[0:2]}:{time_str[2:4]}:{time_str[4:6]}"
            
            # extract the latitude and longitude and add to the dictionary
            result['latitude'].append(to_signed_angle(ddmm_to_decimal(fields[1]), fields[2]))
            result['longitude'].append(to_signed_angle(ddmm_to_decimal(fields[3]), fields[4]))
            
                                        
            # extract and add the altitude to the dictionary
            if fields[8]:
                result['altitude'].append(float(fields[8]))
                
            # extract and add hdop
            if fields[7]:
                result['hdop'].append(float(fields[7]))
    
    return result

def listen_for_GGA(port, sentence_type):
    """
    Listen for NMEA GGA on GPS serial port.
    
    Parameters:
    -----------
    port : uart
        the (open) serial port connection to the GPS unit
    sentence_type: str
        the 3 character sentence identifier (eg GGA, etc.)
        
    Returns:
    --------
    sentence: str
        GGA sentence
    
    """
    # use a while loop to listen for sentences
    while True:
        # check for data in the buffer
        if port.any():
            #print(port.any())
            # try to decode the sentence
            try:
                sentence = port.read().decode('ascii').strip()
                sentences = sentence.split("$")
                for line in sentences:
                    #print(f"Lines: {line}")
                    
                    if len(line) >= 6 and sentence_type in line:
                        #print(f"GGA line: {line}")
                        return line
                    else:
                        continue
                return None
            except Exception as e:
                print(f"Listen for sentence - Exception found: {e}")
                #print(f"Raw sentence: {port.readline()}")
                return None
        else:
            time.sleep(1)
    #return

def housekeeping(sensors):
    # create a list of all the pin numbers being used for housekeeping
    #pin_nums = [6, 14, 15, 4, 5]
    
    # initialise the sensors
    #sensors = Setup(pin_nums)
    temperature_sensors = sensors.temp_sensors
    #print(temperature_sensors)
    temperature_roms = sensors.temp_roms
    #print(temperature_roms)
    pressure_sensor = sensors.pressure_i2c
    gps_sensor = sensors.gps
    
    # measure internal and external temperature
    try:
        temp_int, temp_ext = temperature(temperature_sensors, temperature_roms)
    except Exception as e:
        print(f"HK: Couldn't measure temp: {e}")
        temp_int, temp_ext = None, None

    int_temp = temp_int if temp_int is not None else None
    ext_temp = temp_ext if temp_ext is not None else None
    
    # measure pressure
    try:
        pressure = read_pressure(pressure_sensor, 119)
    except Exception as e:
        print(f"HK: Couldn't measure pressure: {e}")
        pressure = None
        
    if pressure is not None:
        press = pressure
    else:
        press = None
    
    #print(int_temp)
    #print(ext_temp)
    #print(pressure)

    time.sleep(1)
    count = 0
    while count <10:
        try:
            sentence = listen_for_GGA(gps_sensor, 'GGA')
            #print(sentence)
            if sentence is not None:
                GPS_data = parse_nmea(sentence)
                #print(f"Raw sentence: {GPS_data['sentence'][-1]}")
                #print(f"Latitude:  {GPS_data['latitude']} Degrees")
                #print(f"Longitude: {GPS_data['longitude']} Degrees")
                #print(f"Altitude:  {GPS_data['altitude']} Meters")
                #print(f"Timestamp: {GPS_data['timestamp']} HH:MM:SS")
                #print(f"Checksum:  {GPS_data['checksum'][-1]}")
                #print(f"HDOP: {GPS_data['hdop']}")
            else:
                GPS_data = None
                
        except Exception as e:
            print(f"Hang on, we got an error in housekeeping(): {e}")
            GPS_data = None
            
        count += 1
        
    
    return int_temp, ext_temp, press, GPS_data
    
if __name__ == '__housekeeping__':
#while True:
    housekeeping()
