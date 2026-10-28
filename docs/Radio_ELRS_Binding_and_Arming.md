# ExpressLRS Flashing, Bind, and ARM tests

Flashing the receiver that came soldered to the drone required figuring out its name. Quite a few tests were run, but the key one was a script created by Claude. Running it allowed us to assert that it had a version of **Crossfire firmware**, a proprietary Team BlackSheep firmware.

*david@seame-5:\~/Downloads\$ python3 crsf\_ping.py*  
*Pinging receiver on /dev/ttyACM0 for 5 seconds...*

*DEVICE INFO from 0xEC:*  
*Name: XF Nano RX V3*  
*Serial: 0003108f   Hardware ID: 00016001*  
*Software version bytes: 00000613  (ELRS usually: 00 major minor patch \-\> 0.6.19)*

After removing the original receiver and soldering the **BETAFPV**, a ELRS receiver, the script was run again:

*DEVICE INFO from 0xEC:*  
*Name: BFPV Nano 2G4RX*  
*Serial: 454c5253   Hardware ID: 00000000*  
*Software version bytes: 00040100  (ELRS usually: 00 major minor patch \-\> 4.1.0)*

Clearing this hurdle allowed us to proceed to flashing ELRS on both pieces of hardware and proceeding to the bind phase

## RadioMaster Pocket

**Radio Firmware**: The RadioMaster Pocket was updated to **EdgeTX 2.12.4** (“Queen Anne’s Revenge”), the Pocket build downloaded from RadioMaster’s firmware page ([https\://radiomasterrc.com/pages/firmware](https://radiomasterrc.com/pages/firmware)), and flashed with **EdgeTX Buddy** ([https\://buddy.edgetx.org](https://buddy.edgetx.org)). EdgeTX only changes the radio’s own software (models, mixes, switches, screens); the radio link itself is handled by the separate ELRS module. A backup of the original SD card contents was kept.

**Switch Warning After the Update**: After the firmware update, the radio warned about switch **SE** at startup, because the momentary SE button was treated as a regular two-position switch. Fixed by setting SE’s switch type in **SYS \-\> HARDWARE**.

**Channel Map**: Sticks on **CH1–CH4** in **AETR** order (roll, pitch, throttle, yaw), as INAV expects. The model’s **Internal RF** is set to **CRSF**.

## Radio setup

### Firmware Version

4.1.0

### Hardware Vendor

RadioMaster

### Radio Frequency

2.4GHz Transmitter

### Hardware Target

RadioMaster Pocket Internal 2.4GHz TX

### Bind phrase

*Seamefly*

### Region

LBT

### Flashing method

EdgeTX Passthrough

## Drone setup

### Firmware Version

4.1.0

### Hardware Vendor

BETAFPV

### Radio Frequency

2.4GHz Receiver

### Hardware Target

BETAFPV 2.4GHz Nano RX

### Bind phrase

*Seamefly*

### Region

LBT

### Flashing method

Local Download (ELRS-v4.1.0-betafpv.rx\_2400.nano-LBT-bindphrase.bin.gz)

## Bind

We accessed, on the Radio, **SYS \-\> ExpressLRS \-\> Bind** and gained a telemetry warning from it. The same **binding phrase**, as well as the same major version of ELRS allowed them to connect automatically.

## Arm / Prearm Setup

On **MDL \-\> Mixes \-\> CH5** (Aux1) for **ARM**, the **arming/killswitch** input Source was set as **SD**, the two state right shoulder button.  
**CH6** (Aux2) for the **PREARM** safety input that arming requires beforehand, Source was set as **SE**, the two state temporary back left shoulder button.

With SE being a momentary button, **SE** has to be held while **SD** is flipped. So, first the **PREARM**, then activating **ARM** within **3 seconds** (*set prearm\_timeout \= 10000*, on INAV CLI ) to allow the drone to activate its motors. Letting go of **SE** or holding it for over 10 seconds before flipping **SD** does not result in arming.

## Arming Only From the Radio

No other path can arm the drone. **MSP RC override**, which would let the ground computer send stick commands over Wi-Fi, is not enabled. When it is added in Module 1, it must never include the arm or mode channels.

## Motor setup

Before any arming test, the motor settings were checked in the INAV CLI and corrected where needed:

**ESC protocol**: DSHOT300  
**Motor direction**: motor\_direction\_inverted \= ON (props-out, as in the original Betaflight setup)  
**Motor poles**: 12 (INAV’s default was 14\)  
**Failsafe procedure**: DROP  
At first the motors didn’t respond to the **Outputs** tab sliders because of INAV’s motor output safety default: “Enable motor and servo output”. After that, the motors responded.  
Each motor was then spun on its own, with props off. Position and spin direction were checked against the INAV diagram and all four matched.

## VTX

UART3 was set to Peripherals: **IRC Tramp**. INAV then detected the VTX and set it to band A, channel 1, 5865 MHz, at 25 mW (power level 1). Idle current dropped from 0.72 A to 0.55 A, which suggests the VTX had still been on a high power setting from the automatic Betaflight configuration.

## Arming obstacles

The first attempts were refused. INAV’s Status tab (Arming Flags) and the CLI status command showed why:

**ANGLE**: drone not flat  
**ARMSW**: arm switch already on while another blocker was active; cleared by switching ARM off and on again  
**CLI**: the CLI itself blocks arming  
**NOPREARM**: PREARM not active at the moment of arming  
**RC\_LINK**: no radio link  
**DSHOTBEEPER**: INAV had recently beeped through the motors. The beeps were its “receiver lost” warning while the radio was off

With the radio linked, the drone flat, the CLI closed and **PREARM** active, the drone armed and the motors spun at idle (beginning at around **8%**, as shown on the Outputs tab).

## Radio-Loss Failsafe

If the radio link is lost for **0.5 s**, INAV runs its **DROP** procedure: the motors stop and the drone disarms. Once the link returns, it stays disarmed until **SD** is switched off and on again. The receiver’s failsafe was “**No Pulses**”, since INAV could detect the loss.

## Arming successful tests

**Kill switch**: motors stopped instantly when ARM goes off  
**PREARM timeout**: arming refused when its 3 seconds were exceeded  
**Arm switch on at power-up**: arming refused until it was turned off and on again  
**Radio loss**: motors stop (DROP) and the drone stayed disarmed when the link returned

## Telemetry

Link quality (**RQly**, **TQly**), signal strength (**1RSS**) and the drone’s battery voltage (**RxBt**) are shown on the radio’s Telemetry page. To do: add an EdgeTX alarm for **RxBt** below **14.0 V**, since the drone’s own battery beeper is inaudible while the motors spin.

## Issues found

One motor (left unscrewed so the USB-C cable could reach the port) began running visibly slower. Its wire sleeve was found to be damaged, and a single copper wire had been severed near the coils. Arming tests were put on hold for further inspection. A right-angle USB-C cable will be employed in the future to avoid the clash.  
A pack left connected to the drone discharged too far, and the charger’s safety procedure refused it. Battery-off-after-use was added to the checklist.