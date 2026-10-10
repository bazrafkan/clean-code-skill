Add a "gold" customer tier (customer type `3`) to `shop/pricing.py`:
- Gold gets a 15% discount on items.
- Standard shipping is always free for gold. The express surcharge still applies.
- VAT (22%) is computed on the discounted amount, as for the other tiers.
- In `describe`, gold orders show a line `Gold discount: -<amount>` in the same place where silver orders show their discount line.

Requirements:
- Regular (`1`) and silver (`2`) results must stay exactly as they are today, for both `calc` and `describe`.
- Both functions must keep their current signatures, because other code calls them positionally.
