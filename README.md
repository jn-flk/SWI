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
