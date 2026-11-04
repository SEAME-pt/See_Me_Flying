Drone X Y Z Calibration in INAV

**\# get acc**   
acc\_notch\_hz \= 0  
Allowed range: 0 \- 255

acc\_notch\_cutoff \= 1  
Allowed range: 1 \- 255

acc\_hardware \= ICM42605  
Allowed values: NONE, AUTO, MPU6000, MPU6500, MPU9250, BMI160, ICM20689, BMI088, ICM42605, BMI270, LSM6DXX, ICM45686, FAKE

acc\_lpf\_hz \= 15  
Allowed range: 0 \- 200

acc\_lpf\_type \= BIQUAD  
Allowed values: PT1, BIQUAD

acc\_temp\_correction \=  0.000  
Allowed range: \-50 \- 51

acczero\_x \= \-4  
Allowed range: \-32768 \- 32767

acczero\_y \= 2  
Allowed range: \-32768 \- 32767

acczero\_z \= 37  
Allowed range: \-32768 \- 32767

accgain\_x \= 4096  
Allowed range: 1 \- 8192

accgain\_y \= 4098  
Allowed range: 1 \- 8192

accgain\_z \= 4095  
Allowed range: 1 \- 8192

ahrs\_acc\_ignore\_rate \= 15  
Allowed range: 0 \- 30

ahrs\_acc\_ignore\_slope \= 5  
Allowed range: 0 \- 10

rate\_accel\_limit\_roll\_pitch \= 0  
Allowed range: 0 \- 500000

rate\_accel\_limit\_yaw \= 10000  
Allowed range: 0 \- 500000

d\_boost\_max\_at\_acceleration \=  7500.000  
Allowed range: 1000 \- 16000

antigravity\_accelerator \=  5.000  
Allowed range: 1 \- 20

inav\_w\_acc\_bias \=  0.010  
Allowed range: 0 \- 1

nav\_fw\_wp\_tracking\_accuracy \= 0  
Allowed range: 0 \- 10

nav\_fw\_launch\_accel \= 1863  
Allowed range: 1350 \- 20000

acc\_event\_threshold\_high \= 0  
Allowed range: 0 \- 65535

acc\_event\_threshold\_low \= 0  
Allowed range: 0 \- 900

acc\_event\_threshold\_neg\_x \= 0  
Allowed range: 0 \- 65535

**\# set align\_board\_roll \= 1800**  
align\_board\_roll set to 1800  
**\# set align\_board\_yaw \= 3150**  
align\_board\_yaw set to 3150  
