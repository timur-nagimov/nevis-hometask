"""Documents of the search behaviour tests.

UTILITY_BILL, PASSPORT, TAX_RETURN, ELECTRICITY_BILL, WILL and SCAN_0042 are texts the search behaviour was
measured with: change them only together with a new measurement. The rest are written for these tests; the
comment above each says what it is for.
"""

UTILITY_BILL = (
    'Utility bill',
    'British Gas utility bill for March 2025. Account holder John Doe, 14 Larkspur Close, Harrogate. '
    'Amount due £84.20.',
)
PASSPORT = (
    'Passport',
    'Copy of the passport of John Doe, United Kingdom. Passport number 533401372, expires 12 May 2031.',
)
TAX_RETURN = (
    'Tax return',
    'Self Assessment tax return for the tax year 2023-24, submitted to HMRC on 14 January 2025. '
    'Total income £86,400, tax due £21,930.',
)
ELECTRICITY_BILL = (
    'Electricity bill',
    'Electricity bill from EDF Energy for January 2025, 7 Mill Lane, Leeds. Amount due £96.10.',
)
WILL = (
    'Will',
    'Last will and testament of Jane Smith, signed 12 May 2021. Appoints her brother as executor and '
    'leaves the estate to her two children in equal shares.',
)
# A bill that says "utility bill" only in its text; 123 words, so its concepts still get the tags chunk.
SCAN_0042 = (
    'Scan 0042',
    'Scan: utility bill (electricity), 2 pages.\n\n'
    'NORTHMOOR ENERGY\n'
    'Mr Tobias Hallworth\n'
    '14 Larkspur Close, Harrogate HG2 7QD\n'
    'Customer number 8830 5512 07. Bill date 14 March 2025.\n\n'
    'Your electricity bill for 11 December 2024 to 10 March 2025 (90 days).\n'
    'Meter 21E4470913: previous reading 41,208, latest reading 42,371 (smart meter). '
    'Electricity used: 1,163 kWh.\n'
    'Unit charges 1,163 kWh at 24.86p: £289.12\n'
    'Standing charge 90 days at 60.97p: £54.87\n'
    'VAT at 5%: £17.20\n'
    'Total charges this period: £361.19\n'
    'Payments received, thank you (3 direct debits of £95.47): £286.41\n'
    'Balance carried forward: £74.78 debit\n\n'
    'Your monthly direct debit stays at £95.47 and is collected on the 3rd of each month. '
    'Tariff: Fixed Saver 18, ends 30 September 2025. Estimated annual cost on this tariff: £1,210.',
)
# Over 200 words and mentions "utility bill" once: tagged "proof of address", but its tags are not embedded,
# so it must rank below the real bills. It contains neither "address" nor "proof".
LONG_LETTER = (
    'Annual review letter 2025',
    'Dear John,\n\n'
    'Thank you for meeting us on 4 March to review your portfolio. This letter records what we '
    'discussed and what we agreed.\n\n'
    'Over the last twelve months your portfolio returned 6.8% after charges, against 7.4% for its '
    'benchmark. The difference comes mainly from the cautious bond allocation, which held back returns '
    'when markets rose in the autumn but protected the portfolio during the sharp fall in January. Your '
    'equity funds performed in line with their markets, and the global smaller companies fund was the '
    'strongest contributor.\n\n'
    'You told us that your plans have not changed: you still intend to stop full-time work at 60 and to '
    'help both children through university. Your income needs and your attitude to investment risk are '
    'the same as last year, so we recommend keeping the current balanced model portfolio.\n\n'
    "We agreed three actions. First, we will use this year's ISA allowance by moving 20,000 GBP from "
    'your general investment account before 5 April. Second, you will raise your workplace pension '
    'contribution by 2% from May, which lowers your income tax. Third, we will rebalance the portfolio '
    'in June, when the new fund range becomes available on the platform.\n\n'
    'For our records we have filed the copy of the utility bill that you sent with your updated account '
    'forms; nothing further is needed from you.\n\n'
    'Our ongoing fee remains 0.75% a year. Your next review meeting will be in September.\n\n'
    'Yours sincerely,\nDaniel Finch',
)
# A title with a stop word ("of"): the queries "of" and "a" must not find it.
LETTER_OF_WISHES = (
    'Letter of wishes',
    'Letter of wishes from Jane Smith to the trustees of the Smith Family Trust, dated 12 May 2021. '
    'She asks them to consider the education of her grandchildren when they make distributions.',
)
# An identifier inside the text, found whole and by its fragment 7734.
POLICY = (
    'Insurance policy schedule',
    'Home insurance policy schedule for John Doe. Policy number LV-7734-0921-KX. Cover from 1 April '
    '2025 to 31 March 2026; annual premium £412.60.',
)
# A title with an accented letter, found by "zürich".
ZURICH = (
    'Zürich Versicherung',
    'Hausratversicherung der Zürich Versicherung für die Wohnung an der Seestrasse 12, 8002 Zürich. '
    'Jahresprämie CHF 420.',
)
