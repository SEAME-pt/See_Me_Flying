**\# diff all**

\# version  
\# INAV/ODDITYRCF7AIO 9.1.0 Oct 14 2026 / 15:05:56 (e519b69b)  
\# GCC-13.2.1 20231009

\# start the command batch  
batch start

\# reset configuration to default settings  
defaults noreboot

\# resources

\# Timer overrides

\# Outputs \[servo\]

\# safehome

\# Fixed Wing Approach

\# features  
feature PWM\_OUTPUT\_ENABLE

\# beeper

\# blackbox  
blackbox \-NAV\_ACC  
blackbox NAV\_POS  
blackbox NAV\_PID  
blackbox MAG  
blackbox ACC  
blackbox ATTI  
blackbox RC\_DATA  
blackbox RC\_COMMAND  
blackbox MOTORS  
blackbox \-GYRO\_RAW  
blackbox \-PEAKS\_R  
blackbox \-PEAKS\_P  
blackbox \-PEAKS\_Y  
blackbox SERVOS

\# Receiver: Channel map

\# Ports  
serial 2 4096 115200 115200 0 115200

\# LEDs

\# LED color

\# LED mode\_color

\# Modes \[aux\]  
aux 0 0 0 1700 2100  
aux 1 51 1 1700 2100  
aux 2 1 0 1700 2100

\# Adjustments \[adjrange\]

\# Receiver rxrange

\# temp\_sensor

\# Mission Control Waypoints \[wp\]  
\#wp 0 invalid

\# OSD \[osd\_layout\]

\# Programming: logic

\# Programming: global variables

\# Programming: PID controllers

\# OSD: custom elements

\# master  
set gyro\_main\_lpf\_hz \= 90  
set dynamic\_gyro\_notch\_q \= 250  
set dynamic\_gyro\_notch\_min\_hz \= 60  
set dynamic\_gyro\_notch\_mode \= 3D  
set setpoint\_kalman\_q \= 200  
set gyro\_zero\_x \= \-23  
set gyro\_zero\_y \= 10  
set gyro\_zero\_z \= 11  
set ins\_gravity\_cmss \=  984.025  
set acc\_hardware \= ICM42605  
set acczero\_x \= \-4  
set acczero\_y \= 2  
set acczero\_z \= 37  
set accgain\_y \= 4098  
set accgain\_z \= 4095  
set mag\_hardware \= NONE  
set baro\_hardware \= SPL06  
set blackbox\_rate\_denom \= 2  
set motor\_pwm\_protocol \= DSHOT300  
set motor\_poles \= 12  
set failsafe\_procedure \= DROP  
set align\_board\_roll \= 1800  
set align\_board\_yaw \= 3150  
set vbat\_scale \= 1103  
set prearm\_timeout \= 3000  
set applied\_defaults \= 6  
set airmode\_type \= THROTTLE\_THRESHOLD  
set osd\_video\_system \= PAL  
set name \= PILOTIX-BROOK

\# control\_profile  
control\_profile 1

set mc\_p\_pitch \= 32  
set mc\_i\_pitch \= 91  
set mc\_d\_pitch \= 27  
set mc\_cd\_pitch \= 116  
set mc\_p\_roll \= 28  
set mc\_i\_roll \= 78  
set mc\_cd\_roll \= 100  
set mc\_p\_yaw \= 38  
set mc\_i\_yaw \= 82  
set mc\_cd\_yaw \= 100  
set dterm\_lpf\_hz \= 85  
set d\_boost\_min \=  1.000  
set d\_boost\_max \=  1.000  
set antigravity\_gain \=  2.000  
set antigravity\_accelerator \=  5.000  
set smith\_predictor\_delay \=  1.768  
set tpa\_rate \= 20  
set tpa\_breakpoint \= 1200  
set rc\_expo \= 80  
set rc\_yaw\_expo \= 80  
set roll\_rate \= 70  
set pitch\_rate \= 70  
set yaw\_rate \= 60  
set ez\_enabled \= ON  
set ez\_filter\_hz \= 90  
set ez\_axis\_ratio \= 116  
set ez\_response \= 71  
set ez\_damping \= 103  
set ez\_stability \= 105  
set ez\_rate \= 134  
set ez\_expo \= 118

\# control\_profile  
control\_profile 2

set d\_boost\_min \=  1.000  
set d\_boost\_max \=  1.000  
set antigravity\_gain \=  2.000  
set antigravity\_accelerator \=  5.000  
set tpa\_rate \= 20  
set tpa\_breakpoint \= 1200

\# control\_profile  
control\_profile 3

set d\_boost\_min \=  1.000  
set d\_boost\_max \=  1.000  
set antigravity\_gain \=  2.000  
set antigravity\_accelerator \=  5.000  
set tpa\_rate \= 20  
set tpa\_breakpoint \= 1200

\# mixer\_profile  
mixer\_profile 1

set motor\_direction\_inverted \= ON  
set model\_preview\_type \= 3  
set motorstop\_on\_low \= OFF

\# Mixer: motor mixer

mmix reset

mmix 0  1.000 \-1.000  1.000 \-1.000  
mmix 1  1.000 \-1.000 \-1.000  1.000  
mmix 2  1.000  1.000  1.000  1.000  
mmix 3  1.000  1.000 \-1.000 \-1.000

\# Mixer: servo mixer

\# mixer\_profile  
mixer\_profile 2

\# Mixer: motor mixer

\# Mixer: servo mixer

\# battery\_profile  
battery\_profile 1

set bat\_cells \= 4

\# battery\_profile  
battery\_profile 2

\# battery\_profile  
battery\_profile 3

\# restore original profile selection  
control\_profile 1  
mixer\_profile 1  
battery\_profile 1

\# save configuration  
save

