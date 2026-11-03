

**DRONE BEFORE CHANGE FROM BETAFLIGHT TO INAV**

**\# diff all**

\# version  
\# Betaflight / STM32F7X2 (S7X2) 4.5.1 Oct 17 2024 / 19:49:44 (326ecdcf2) MSP API: 1.46

\# start the command batch  
batch start

\# reset configuration to default settings  
defaults nosave

board\_name ODDITYRCF7AIO  
manufacturer\_id ODTY  
mcu\_id 003f00263233511133363430  
signature 

\# name: Pilotix-Brook

\# resources  
resource LED\_STRIP 1 NONE  
resource PINIO 1 A08

\# feature  
feature TELEMETRY  
feature OSD

\# serial  
serial 1 64 115200 57600 0 115200  
serial 2 8192 115200 57600 0 115200

\# beacon  
beacon RX\_LOST  
beacon RX\_SET

\# aux  
aux 0 0 0 1700 2100 0 0  
aux 1 1 1 1700 2100 0 0  
aux 2 2 1 1300 1700 0 0  
aux 3 13 2 1700 2100 0 0  
aux 4 36 1 1700 2100 0 0  
aux 5 40 4 1300 1700 0 0

\# vtxtable  
vtxtable bands 5  
vtxtable channels 8  
vtxtable band 1 BOSCAM\_A A CUSTOM  5865 5845 5825 5805 5785 5765 5745 5725  
vtxtable band 2 BOSCAM\_B B CUSTOM  5733 5752 5771 5790 5809 5828 5847 5866  
vtxtable band 3 BOSCAM\_E E CUSTOM  5705 5685 5665    0 5885 5905    0    0  
vtxtable band 4 FATSHARK F CUSTOM  5740 5760 5780 5800 5820 5840 5860 5880  
vtxtable band 5 RACEBAND R CUSTOM  5658 5695 5732 5769 5806 5843 5880 5917  
vtxtable powerlevels 5  
vtxtable powervalues 25 100 200 400 600  
vtxtable powerlabels 25 200 400 800 1.3

\# master  
set gyro\_lpf1\_static\_hz \= 362  
set gyro\_lpf2\_type \= PT2  
set gyro\_lpf2\_static\_hz \= 725  
set dyn\_notch\_count \= 1  
set dyn\_notch\_q \= 500  
set gyro\_lpf1\_dyn\_min\_hz \= 362  
set gyro\_lpf1\_dyn\_max\_hz \= 725  
set acc\_calibration \= \-51,-22,-37,1  
set blackbox\_sample\_rate \= 1/16  
set blackbox\_disable\_alt \= ON  
set blackbox\_disable\_debug \= ON  
set blackbox\_disable\_rpm \= ON  
set blackbox\_disable\_gps \= ON  
set motor\_pwm\_protocol \= DSHOT300  
set motor\_poles \= 12  
set motor\_output\_reordering \= 2,3,0,1,4,5,6,7  
set align\_board\_yaw \= 135  
set vbat\_max\_cell\_voltage \= 435  
set beeper\_dshot\_beacon\_tone \= 5  
set yaw\_motors\_reversed \= ON  
set pid\_process\_denom \= 2  
set simplified\_gyro\_filter \= OFF  
set simplified\_gyro\_filter\_multiplier \= 145  
set osd\_vbat\_pos \= 2432  
set osd\_rssi\_pos \= 2425  
set osd\_link\_quality\_pos \= 2392  
set osd\_rssi\_dbm\_pos \= 2457  
set osd\_flymode\_pos \= 2080  
set osd\_throttle\_pos \= 2445  
set osd\_vtx\_channel\_pos \= 2099  
set osd\_craft\_name\_pos \= 2048  
set osd\_warnings\_pos \= 14633  
set osd\_avg\_cell\_voltage\_pos \= 2400  
set osd\_disarmed\_pos \= 2315  
set osd\_esc\_rpm\_pos \= 192  
set osd\_flip\_arrow\_pos \= 2285  
set osd\_displayport\_device \= MAX7456  
set osd\_canvas\_width \= 30  
set osd\_canvas\_height \= 13  
set vtx\_band \= 1  
set vtx\_channel \= 1  
set vtx\_power \= 5  
set vtx\_freq \= 5865  
set pinio\_config \= 1,129,129,129  
set pinio\_box \= 40,255,255,255  
set craft\_name \= Pilotix-Brook

profile 0

\# profile 0  
set dterm\_lpf1\_dyn\_min\_hz \= 93  
set dterm\_lpf1\_dyn\_max\_hz \= 187  
set dterm\_lpf1\_dyn\_expo \= 4  
set dterm\_lpf1\_type \= PT2  
set dterm\_lpf1\_static\_hz \= 93  
set dterm\_lpf2\_type \= PT2  
set dterm\_lpf2\_static\_hz \= 187  
set vbat\_sag\_compensation \= 100  
set anti\_gravity\_gain \= 60  
set yaw\_lowpass\_hz \= 0  
set p\_pitch \= 59  
set i\_pitch \= 100  
set d\_pitch \= 57  
set f\_pitch \= 122  
set p\_roll \= 56  
set i\_roll \= 95  
set d\_roll \= 49  
set f\_roll \= 117  
set p\_yaw \= 56  
set i\_yaw \= 95  
set f\_yaw \= 117  
set d\_min\_roll \= 44  
set d\_min\_pitch \= 49  
set thrust\_linear \= 30  
set feedforward\_jitter\_factor \= 12  
set simplified\_pids\_mode \= OFF  
set simplified\_master\_multiplier \= 140  
set simplified\_i\_gain \= 95  
set simplified\_d\_gain \= 105  
set simplified\_pi\_gain \= 90  
set simplified\_dmax\_gain \= 40  
set simplified\_feedforward\_gain \= 70  
set simplified\_dterm\_filter \= OFF  
set simplified\_dterm\_filter\_multiplier \= 125

profile 1

profile 2

profile 3

\# restore original profile selection  
profile 0

rateprofile 0

rateprofile 1

rateprofile 2

rateprofile 3

\# restore original rateprofile selection  
rateprofile 0

\# save configuration  
Save

**\# version**  
\# Betaflight / STM32F7X2 (S7X2) 4.5.1 Oct 17 2024 / 19:49:44 (326ecdcf2) MSP API: 1.46  
\# board: manufacturer\_id: ODTY, board\_name: ODDITYRCF7AIO

**\# status**  
MCU F722 Clock=216MHz, Vref=3.28V, Core temp=48degC  
Stack size: 2048, Stack address: 0x20010000  
Configuration: CONFIGURED, size: 3800, max available: 16384  
Devices detected: SPI:1, I2C:1  
Gyros detected: gyro 1 locked dma  
GYRO=ICM42688P, ACC=ICM42688P, BARO=DPS310  
OSD: MAX7456 (30 x 13\)  
BUILD KEY: a72a9e7809ef36ab0db31291e4b21362 (4.5.1)  
System Uptime: 613 seconds, Current Time: 2026-10-13T09:43:24.736+00:00  
CPU:29%, cycle time: 125, GYRO rate: 8000, RX rate: 15, System rate: 9  
Voltage: 2 \* 0.01V (0S battery \- NOT PRESENT)  
I2C Errors: 0  
FLASH: JEDEC ID=0x00ef4018 16M  
GPS: NOT ENABLED  
Arming disable flags: RXLOSS NOPREARM CLI MSP DSHOT\_TELEM

**\# get failsafe**  
msp\_override\_failsafe \= OFF  
Allowed values: OFF, ON

failsafe\_delay \= 15  
Allowed range: 1 \- 200

failsafe\_off\_delay \= 10  
Allowed range: 0 \- 200

failsafe\_throttle \= 1000  
Allowed range: 750 \- 2250

failsafe\_switch\_mode \= STAGE1  
Allowed values: STAGE1, KILL, STAGE2

failsafe\_throttle\_low\_delay \= 100  
Allowed range: 0 \- 300

failsafe\_procedure \= DROP  
Allowed values: AUTO-LAND, DROP, GPS-RESCUE

failsafe\_recovery\_delay \= 5  
Allowed range: 1 \- 200

failsafe\_stick\_threshold \= 30  
Allowed range: 0 \- 50

**\# get pinio**  
pinio\_config \= 1,129,129,129  
Array length: 4  
Default value: 1,1,1,1

pinio\_box \= 40,255,255,255  
Array length: 4  
Default value: 255,255,255,255

**\# get msp\_override**  
msp\_override\_channels\_mask \= 0  
Allowed range: 0 \- 262143

msp\_override\_failsafe \= OFF  
Allowed values: OFF, ON

**\# resource show**  
Currently active IO resource assignments:  
(reboot to update)  
\--------------------  
A00: FREE  
A01: FREE  
A02: SERIAL\_TX 2  
A03: SERIAL\_RX 2  
A04: FREE  
A05: SPI\_SCK 1  
A06: SPI\_SDI 1  
A07: SPI\_SDO 1  
A08: PINIO 1  
A09: FREE  
A10: FREE  
A11: USB  
A12: USB  
A13: LED 2  
A14: LED 1  
A15: FREE  
B00: MOTOR 1  
B01: MOTOR 2  
B02: GYRO\_CS 1  
B03: FREE  
B04: MOTOR 3  
B05: MOTOR 4  
B06: FREE  
B07: FREE  
B08: I2C\_SCL 1  
B09: I2C\_SDA 1  
B10: SERIAL\_TX 3  
B11: FREE  
B12: OSD\_CS  
B13: SPI\_SCK 2  
B14: SPI\_SDI 2  
B15: SPI\_SDO 2  
C00: FREE  
C01: ADC\_CURR  
C02: ADC\_BATT  
C03: FREE  
C04: GYRO\_EXTI  
C05: FREE  
C06: FREE  
C07: FREE  
C08: FREE  
C09: FREE  
C10: SPI\_SCK 3  
C11: SPI\_SDI 3  
C12: SPI\_SDO 3  
C13: BEEPER  
C14: FREE  
C15: FREE  
D00: FREE  
D01: FREE  
D02: FLASH\_CS  
D03: FREE  
D04: FREE  
D05: FREE  
D06: FREE  
D07: FREE  
D08: FREE  
D09: FREE  
D10: FREE  
D11: FREE  
D12: FREE  
D13: FREE  
D14: FREE  
D15: FREE  
E00: FREE  
E01: FREE  
E02: FREE  
E03: FREE  
E04: FREE  
E05: FREE  
E06: FREE  
E07: FREE  
E08: FREE  
E09: FREE  
E10: FREE  
E11: FREE  
E12: FREE  
E13: FREE  
E14: FREE  
E15: FREE  
F00: FREE  
F01: FREE  
F02: FREE  
F03: FREE  
F04: FREE  
F05: FREE  
F06: FREE  
F07: FREE  
F08: FREE  
F09: FREE  
F10: FREE  
F11: FREE  
F12: FREE  
F13: FREE  
F14: FREE  
F15: FREE

**\# get vbat**  
vbat\_max\_cell\_voltage \= 435  
Allowed range: 100 \- 500  
Default value: 430

vbat\_full\_cell\_voltage \= 410  
Allowed range: 100 \- 500

vbat\_min\_cell\_voltage \= 330  
Allowed range: 100 \- 500

vbat\_warning\_cell\_voltage \= 350  
Allowed range: 100 \- 500

vbat\_hysteresis \= 1  
Allowed range: 0 \- 250

vbat\_detect\_cell\_voltage \= 300  
Allowed range: 0 \- 2000

use\_vbat\_alerts \= ON  
Allowed values: OFF, ON

vbat\_cutoff\_percent \= 100  
Allowed range: 0 \- 100

vbat\_display\_lpf\_period \= 30  
Allowed range: 1 \- 255

vbat\_sag\_lpf\_period \= 2  
Allowed range: 1 \- 255

vbat\_duration\_for\_warning \= 0  
Allowed range: 0 \- 150

vbat\_duration\_for\_critical \= 0  
Allowed range: 0 \- 150

vbat\_scale \= 110  
Allowed range: 0 \- 255

vbat\_divider \= 10  
Allowed range: 1 \- 255

vbat\_multiplier \= 1  
Allowed range: 1 \- 255

vbat\_sag\_compensation \= 100  
profile 0  
Allowed range: 0 \- 150  
Default value: 0

osd\_vbat\_pos \= 2432  
Allowed range: 0 \- 65535  
Default value: 341

**\# serial**  
serial 20 1 115200 57600 0 115200  
serial 0 0 115200 57600 0 115200  
serial 1 64 115200 57600 0 115200  
serial 2 8192 115200 57600 0 115200  
serial 3 0 115200 57600 0 115200  
serial 5 0 115200 57600 0 115200

**\# resource**  
resource BEEPER 1 C13  
resource MOTOR 1 B04  
resource MOTOR 2 B05  
resource MOTOR 3 B00  
resource MOTOR 4 B01  
resource SERIAL\_TX 1 A09  
resource SERIAL\_TX 2 A02  
resource SERIAL\_TX 3 B10  
resource SERIAL\_TX 4 A00  
resource SERIAL\_TX 6 C06  
resource SERIAL\_RX 1 A10  
resource SERIAL\_RX 2 A03  
resource SERIAL\_RX 3 B11  
resource SERIAL\_RX 4 A01  
resource SERIAL\_RX 6 C07  
resource I2C\_SCL 1 B08  
resource I2C\_SDA 1 B09  
resource LED 1 A14  
resource LED 2 A13  
resource SPI\_SCK 1 A05  
resource SPI\_SCK 2 B13  
resource SPI\_SCK 3 C10  
resource SPI\_SDI 1 A06  
resource SPI\_SDI 2 B14  
resource SPI\_SDI 3 C11  
resource SPI\_SDO 1 A07  
resource SPI\_SDO 2 B15  
resource SPI\_SDO 3 C12  
resource ADC\_BATT 1 C02  
resource ADC\_CURR 1 C01  
resource PINIO 1 A08  
resource FLASH\_CS 1 D02  
resource OSD\_CS 1 B12  
resource GYRO\_EXTI 1 C04  
resource GYRO\_CS 1 B02

**\# aux**  
aux 0 0 0 1700 2100 0 0  
aux 1 1 1 1700 2100 0 0  
aux 2 2 1 1300 1700 0 0  
aux 3 13 2 1700 2100 0 0  
aux 4 36 1 1700 2100 0 0  
aux 5 40 4 1300 1700 0 0  
aux 6 0 0 900 900 0 0  
aux 7 0 0 900 900 0 0  
aux 8 0 0 900 900 0 0  
aux 9 0 0 900 900 0 0  
aux 10 0 0 900 900 0 0  
aux 11 0 0 900 900 0 0  
aux 12 0 0 900 900 0 0  
aux 13 0 0 900 900 0 0  
aux 14 0 0 900 900 0 0  
aux 15 0 0 900 900 0 0  
aux 16 0 0 900 900 0 0  
aux 17 0 0 900 900 0 0  
aux 18 0 0 900 900 0 0  
aux 19 0 0 900 900 0 0

**\# Drone\_backup\_before\_any\_setup**

\# diff all

\# version  
\# Betaflight / STM32F7X2 (S7X2) 4.5.1 Oct 17 2024 / 19:49:44 (326ecdcf2) MSP API: 1.46

\# start the command batch  
batch start

\# reset configuration to default settings  
defaults nosave

board\_name ODDITYRCF7AIO  
manufacturer\_id ODTY  
mcu\_id 003f00263233511133363430  
signature 

\# name: Pilotix-Brook

\# resources  
resource LED\_STRIP 1 NONE  
resource PINIO 1 A08

\# feature  
feature TELEMETRY  
feature OSD

\# serial  
serial 1 64 115200 57600 0 115200  
serial 2 8192 115200 57600 0 115200

\# beacon  
beacon RX\_LOST  
beacon RX\_SET

\# aux  
aux 0 0 0 1700 2100 0 0  
aux 1 1 1 1700 2100 0 0  
aux 2 2 1 1300 1700 0 0  
aux 3 13 2 1700 2100 0 0  
aux 4 40 4 1300 1700 0 0

\# vtxtable  
vtxtable bands 5  
vtxtable channels 8  
vtxtable band 1 BOSCAM\_A A CUSTOM  5865 5845 5825 5805 5785 5765 5745 5725  
vtxtable band 2 BOSCAM\_B B CUSTOM  5733 5752 5771 5790 5809 5828 5847 5866  
vtxtable band 3 BOSCAM\_E E CUSTOM  5705 5685 5665    0 5885 5905    0    0  
vtxtable band 4 FATSHARK F CUSTOM  5740 5760 5780 5800 5820 5840 5860 5880  
vtxtable band 5 RACEBAND R CUSTOM  5658 5695 5732 5769 5806 5843 5880 5917  
vtxtable powerlevels 5  
vtxtable powervalues 25 100 200 400 600  
vtxtable powerlabels 25 200 400 800 1.3

\# master  
set gyro\_lpf1\_static\_hz \= 362  
set gyro\_lpf2\_type \= PT2  
set gyro\_lpf2\_static\_hz \= 725  
set dyn\_notch\_count \= 1  
set dyn\_notch\_q \= 500  
set gyro\_lpf1\_dyn\_min\_hz \= 362  
set gyro\_lpf1\_dyn\_max\_hz \= 725  
set acc\_calibration \= \-51,-22,-37,1  
set baro\_hardware \= NONE  
set blackbox\_sample\_rate \= 1/16  
set blackbox\_disable\_alt \= ON  
set blackbox\_disable\_debug \= ON  
set blackbox\_disable\_rpm \= ON  
set blackbox\_disable\_gps \= ON  
set motor\_pwm\_protocol \= DSHOT300  
set motor\_poles \= 12  
set motor\_output\_reordering \= 2,3,0,1,4,5,6,7  
set align\_board\_yaw \= \-45  
set vbat\_max\_cell\_voltage \= 435  
set beeper\_dshot\_beacon\_tone \= 5  
set yaw\_motors\_reversed \= ON  
set pid\_process\_denom \= 2  
set simplified\_gyro\_filter \= OFF  
set simplified\_gyro\_filter\_multiplier \= 145  
set osd\_vbat\_pos \= 2432  
set osd\_rssi\_pos \= 2425  
set osd\_link\_quality\_pos \= 2392  
set osd\_rssi\_dbm\_pos \= 2457  
set osd\_flymode\_pos \= 2080  
set osd\_throttle\_pos \= 2445  
set osd\_vtx\_channel\_pos \= 2099  
set osd\_craft\_name\_pos \= 2048  
set osd\_warnings\_pos \= 14633  
set osd\_avg\_cell\_voltage\_pos \= 2400  
set osd\_disarmed\_pos \= 2315  
set osd\_esc\_rpm\_pos \= 192  
set osd\_flip\_arrow\_pos \= 2285  
set osd\_displayport\_device \= MAX7456  
set osd\_canvas\_width \= 30  
set osd\_canvas\_height \= 13  
set vtx\_band \= 1  
set vtx\_channel \= 1  
set vtx\_power \= 5  
set vtx\_freq \= 5865  
set pinio\_config \= 1,129,129,129  
set pinio\_box \= 40,255,255,255  
set craft\_name \= Pilotix-Brook

profile 0

\# profile 0  
set dterm\_lpf1\_dyn\_min\_hz \= 93  
set dterm\_lpf1\_dyn\_max\_hz \= 187  
set dterm\_lpf1\_dyn\_expo \= 4  
set dterm\_lpf1\_type \= PT2  
set dterm\_lpf1\_static\_hz \= 93  
set dterm\_lpf2\_type \= PT2  
set dterm\_lpf2\_static\_hz \= 187  
set vbat\_sag\_compensation \= 100  
set anti\_gravity\_gain \= 60  
set yaw\_lowpass\_hz \= 0  
set p\_pitch \= 59  
set i\_pitch \= 100  
set d\_pitch \= 57  
set f\_pitch \= 122  
set p\_roll \= 56  
set i\_roll \= 95  
set d\_roll \= 49  
set f\_roll \= 117  
set p\_yaw \= 56  
set i\_yaw \= 95  
set f\_yaw \= 117  
set d\_min\_roll \= 44  
set d\_min\_pitch \= 49  
set thrust\_linear \= 30  
set feedforward\_jitter\_factor \= 12  
set simplified\_pids\_mode \= OFF  
set simplified\_master\_multiplier \= 140  
set simplified\_i\_gain \= 95  
set simplified\_d\_gain \= 105  
set simplified\_pi\_gain \= 90  
set simplified\_dmax\_gain \= 40  
set simplified\_feedforward\_gain \= 70  
set simplified\_dterm\_filter \= OFF  
set simplified\_dterm\_filter\_multiplier \= 125

profile 1

profile 2

profile 3

\# restore original profile selection  
profile 0

rateprofile 0

rateprofile 1

rateprofile 2

rateprofile 3

\# restore original rateprofile selection  
rateprofile 0

\# save configuration  
save  
\# 

