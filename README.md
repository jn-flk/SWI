# Nazev tymu

## HAH 
**Members:** Honza Adam Honza

**Repository:** https://github.com/jn-flk/SWI


## Reservation domain
Co konkrétně rezervujeme?

- Resource - Divadlo
- Reservation - sedadlo v divadle, předstaení
- User - návštěvník divadla
- States - RESERVED, CANCELED, DONE
- Operations - create, confirm/approve, cancel, check availability
- Common rule - dvě potvrzené rezervace stejného resource se nesmí překrývat
- Boundary - Notification Service

See `docs/intent-and-change.md` for the full domain description.

## Setup & run

```bash
python3 -m venv venv
source venv/bin/activate
pip install django
python manage.py test
```

## CP1 walking skeleton

#### Functionality
A spectator can reserve a specific seat for a specific performance.

#### End-to-end flow
**POST /reservations**
- validate Performance exists
- validate Seat exists
- validate Seat belongs to Performance's Hall
- check Seat is available for this Performance
- create Reservation
- persist Reservation
- return reservation ID

