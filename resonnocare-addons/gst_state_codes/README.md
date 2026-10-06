# GST State Codes India — Odoo 18

This module adds GST information to `res.country.state`:

- GST State Code (2-letter code such as DL, HR, KA)
- GSTIN
- GST State Name
- GST State HQ / Address

On installation, the supplied GST State Code List is applied to Indian states. Existing Odoo states are updated by name; missing entries such as **Andhra Pradesh (New)** are created only when they do not already exist.

## Installation

1. Copy `gst_state_codes` into your Odoo 18 custom addons directory.
2. Restart Odoo.
3. Update Apps List.
4. Install **GST State Codes India**.
5. Open **GST State Codes** from the Administration menu.

## Notes

The source workbook contains 37 state-code rows. GSTIN/address information is populated only for rows where it was present in the workbook.
