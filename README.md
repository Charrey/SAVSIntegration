# IMPORTANT PART
### Smoke alarms are very important for safety. This is a project that can fail at any time if the cloud API changes. Since it uses undocumented APIs, it could have adverse effects on the safety functions of your smoke alarms.
### Do not depend on this integration for your safety. If you use smoke alarms that are connected to the internet, always combine them with dumb ones.
### The owner of this repository takes no responsibility for harm caused by fires.
# END OF IMPORTANT PART



## Purpose

This is a Home Assistant integration for SAVS smoke detectors sold by [Brandpreventiewinkel.nl](https://www.brandpreventiewinkel.nl/). I've specifically aimed this at the [SAVS G-10 gateway](https://www.brandpreventiewinkel.nl/product/smart-home/savs-g10-base-station-gateway/) and the [SAVS S10-W LinkSmart](https://www.brandpreventiewinkel.nl/product/rookmelders/savs-s10-w-slimme-rookmelder-linksmart/). These are whitelabel  products that you may recognize under other names like the WisuAlarm products [WisuLink DHI-HY-GW01A](https://eu.wisualarm.com/products/wireless-gateway?_pos=2&_sid=18f444d24&_ss=r) (gateway) and [WisuLink S05-R8-B](https://eu.wisualarm.com/products/smoke-alarm-new-version) (smoke alarm). The integration aims to allow you to make your smoke alarms sound/test on demand, and to run automations when a fire is detected.

## Methodology

This integration uses cloud polling to obtain information about your devices, like connectivity status and battery level and fire alarm state.

This means that (contrary to the official app which will immediately trigger a notification/alarm on your phone) it can take up to 30 seconds for an update to be propagated to Home Assistant.  Unfortunately, it seems unlikely this desireable, immediate notification behavior can be reproduced without either soldering to the device and somehow obtaining root, or by having Home Assistant itself emulate an Android device capable of receiving notifications. 

## Sensors and services

- Sensor: gateway internet connectivity status
- Sensor: Smoke alarm connectivity status
- Sensor: Smoke alarm battery level
- Sensor: Smoke alarm alarm status polled (CAN BE DELAYED)

## Prerequisites

- You have one of the SAVS gateways (i.e., SAVS G-10 gateway)
- You have used the official SAVS app to create an account
- You have added the device to your account using the SAVS app

## Setup

1. Add the component in this repository to custom_components 
2. In Home Assistant search for the SAVS integration
3. Enter the e-mail address and password of your SAVS account.
4. The gateway and smoke alarms devices should be detected, and you can assign rooms to them.

## Removing the integration

This integration follows standard integration removal. No extra steps are required.

## How to help

I'd appreciate it if you [reach out to me](mailto:savsintegration@proton.me) if you own other devices like this to experiment with. Issues and contributions are also welcome.