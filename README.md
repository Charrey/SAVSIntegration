## Purpose

This is a Home Assistant integration for SAVS smoke detectors sold by Brandpreventiewinkel.nl. I've specifically aimed this at the SAVS G-10 gateway and the SAVS S10-W LinkSmart. These are whitelabel  products that you may recognize under other names like the WisuAlarm products WisuLink DHI-HY-GW01A (gateway) and WisuLink S05-R8-B (smoke alarm). The integration aims to allow you to make your smoke alarms sound/test on demand, and to run automations when a fire is detected.

## Methodology

This integration functions two-fold:

- It uses cloud polling to obtain information about your devices, like connectivity status and battery level.
- It uses Firebase to be immediately notified when an alarm event takes place (WORK IN PROGRESS)

## Sensors and services

- Sensor: gateway internet connectivity status
- Sensor: Smoke alarm connectivity status
- Sensor: Smoke alarm battery level
- Sensor: Smoke alarm alarm status polled (CAN BE DELAYED)
- Sensor: Most recent firebase alarm notification (IMMEDIATE) (WORK IN PROGRESS)

## Setup

1. Setup your gateway and smoke alarms with the official app using an account.
2. Add the component in this repository to custom_components 
3. In Home Assistant search for the SAVS integration
4. Enter the e-mail address and password of your SAVS account.
5. The gateway and smoke alarms devices should be detected, and you can assign rooms to them.

## How to help

I'd appreciate it if you [reach out to me](mailto:savsintegration@proton.me) if you own other devices like this to experiment with or if you have experience with firebase notifications in home assistant. Issues and contributions are also welcome.