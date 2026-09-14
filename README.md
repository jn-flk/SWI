# Nazev tymu

HAH - Honza Adam Honza

## Reservation domain
Co konkrétně rezervujeme?

Resource - Divadlo
Reservation - sedadlo v divadle, předstaení
User - návštěvník divadla
States 	např. DRAFT / CONFIRMED / CANCELLED
Operations 	create, confirm/approve, cancel, check availability
Common rule 	dvě potvrzené rezervace stejného resource se nesmí překrývat
Boundary 	alespoň jedna dependency; defaultně Notification Service