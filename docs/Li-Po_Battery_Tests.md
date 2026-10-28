**Battery Tests**

In order to measure the difference in readings among the **INAV** configurator in the Status tab, the **charger** (SkyRC B6 Neo 200W DC) and the **multimeter** reading, done with one needle in each connector, and reading one pin at a time. Test \#1 and \#2 were done to ascertain a necessity to change the virtual battery scale, `vbat_scale` in INAV, from its 1100 default value. It is a percent correction that can be adjusted by comparing readings from other sources:

**VBAT Scale 1100**  
Test	INAV		Charger	Multimeter	Average (non INAV)	1100 × Av ÷ INAV  
1	16.41 V	16.43 V	16.49 V	16.46 V		≈ 1103  
2	16.39 V	16.42 V	16.46 V	16.44 V		≈ 1103

Given the similarity in differences, set vbat\_scale \= 1103, was tested to minimize the already small discrepancy between readings on different machines.

**VBAT Scale 1103**  
Test	INAV		Charger	Multimeter	Average (non INAV)	  
3	16.28 V	16.26 V	16.29 V	16.27.5 V			  
4	16.85 V	16.81 V	16.87 V	16.84 V			

The battery reading calibration was done so it sits in the middle of the multimeter and charger readings, and it seems to have come about as close as the precision of the various instruments will allow.  
The cells are apparently well-balanced too, as their voltage never strays far from each other.  
The default values for voltage warning in INAV match those in our original planning. vbat\_warning\_cell\_voltage \= 350 (3.50 V per cell, 14.0 V total)  
vbat\_min\_cell\_voltage \= 330 (3.30 V per cell, 13.2 V total)  
The only battery-related settings changed from the defaults were `bat_cells = 4` (instead of auto-detect) and the aforementioned `vbat_scale = 1103`

**TEST \#1**

**INAV**  
Battery detected cell count: 4  
Battery voltage: 16.41 V  
Battery left: 89 %  
Battery remaining capacity NA  
Assume full battery on connect true  
Battery use cap thresholds false  
Current draw: 0.59 A  
Power draw: 9.68 W  
Capacity drawn: 11 mAh  
Capacity drawn: 0.168 Wh  
RSSI: 0 %

**Charger** (cell 1-4 and total)  
4.109 4.108 4.108 4.109  
16.43

**Multimeter** **readings** (with individual readings)  
16.49 (4.13)  
12.36 (4.12)  
8.24 (4.12)  
4.12 (4.12)

**TEST \#2**

**INAV**  
Battery detected cell count: 4  
Battery voltage: 16.39 V  
Battery left: 100 %  
Battery remaining capacity NA  
Assume full battery on connect false  
Battery use cap thresholds false  
Current draw: 0.57 A  
Power draw: 9.34 W  
Capacity drawn: 41 mAh  
Capacity drawn: 0.088 Wh  
RSSI: 0 %

**Charger** (cell 1-4 and total)  
4.105 4.101 4.104 4.107  
16.42

**Multimeter** readings (totals )  
16.46 (4.12)  
12.34 (4.11)  
8.23 (4.12)  
4.11

**TEST \#3**

**INAV**  
Battery detected cell count:	4  
Battery voltage:	16.28 V  
Battery left:	85 %  
Battery remaining capacity	NA  
Assume full battery on connect	false  
Battery use cap thresholds	false  
Current draw:	0.57 A  
Power draw:	 9.27 W  
Capacity drawn: 	1 mAh  
Capacity drawn: 	0.018 Wh  
RSSI:	0 %

**Charger** (cell 1-4 and total)  
4.064 4.060 4.066 4.066  
16.26  
   
**Multimeter** **readings** (with individual readings)  
16.29 (4.07)  
12.22 (4.08)  
8.14 (4.07)  
4.07

**TEST \#4**

**INAV**  
Battery detected cell count:	4  
Battery voltage:	16.85 V  
Battery left:	100 %  
Battery remaining capacity	NA  
Assume full battery on connect	true  
Battery use cap thresholds	false  
Current draw:	0.57 A  
Power draw:	9.60 W  
Capacity drawn:	1 mAh  
Capacity drawn:	0.018 Wh  
RSSI:	0 %

**Charger** (cell 1-4 and total)  
4.199 4.200 4.200 4.201  
16.81  
   
**Multimeter** **readings** (with individual readings)  
16.87 (4.22)  
12.65 (4.22)  
8.43 (4.22)  
4.21  
