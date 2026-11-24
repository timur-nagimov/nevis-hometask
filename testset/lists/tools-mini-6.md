# tools-mini-6

Автор: lead (Claude), 2026-11-20.

The shared mini set on which Elasticsearch, Meilisearch, Typesense, ParadeDB, PostgreSQL built-ins and vector stacks were compared (research/tools/).

Корпус: 3 клиентов, 6 документов (полный текст — в `suites/tools-mini-6.json`).

| id | Запрос | Уровень | Категория | Правильный ответ | Почему |
|---|---|---|---|---|---|
| q001 | `NevisWealth` | обязательно | email (только клиенты) | John Doe <john.doe@neviswealth.com><br>первым: John Doe <john.doe@neviswealth.com> | Assignment example 1. |
| q002 | `neviswealth` | обязательно | email (только клиенты) | John Doe <john.doe@neviswealth.com> | Case must not matter. |
| q003 | `nevis` | обязательно | email (только клиенты) | John Doe <john.doe@neviswealth.com> | Prefix of the e-mail domain. |
| q004 | `wealth` | обязательно | email (только клиенты) | John Doe <john.doe@neviswealth.com> | Substring in the middle of the e-mail domain. |
| q005 | `john.doe` | обязательно | email (только клиенты) | John Doe <john.doe@neviswealth.com> | Local part of the e-mail. |
| q006 | `doe@nevis` | обязательно | email (только клиенты) | John Doe <john.doe@neviswealth.com> | Fragment across the @ sign. |
| q007 | `Jon Doe` | желательно | typo (только клиенты) | John Doe <john.doe@neviswealth.com> | Typo in the first name. |
| q008 | `zoe muller` | ожидаемо | unicode (только клиенты) | Zoë Müller <zoe.mueller@alpenbank.ch> | Typed without the accents. |
| q009 | `pension` | обязательно | description (только клиенты) | Jane Smith <jane.smith@example.org> | Word from the description (pensions). |
| q010 | `address proof` | обязательно | concept (только документы) | «Utility bill»; «Scan 0042»<br>первым: «Utility bill» или «Scan 0042» | Assignment example 2; the courier proof of delivery (d04) shares both words but is not address evidence and must not be first. |
| q011 | `proof of address` | обязательно | concept (только документы) | «Utility bill»; «Scan 0042»<br>первым: «Utility bill» или «Scan 0042» | Common wording of the same need. |
| q012 | `utility bill` | обязательно | literal (только документы) | «Utility bill»; «Scan 0042» | Literal document type; d05 says it only in the text. |
| q013 | `utilty bill` | желательно | typo (только документы) | «Utility bill»; «Scan 0042» | Typo of the literal type. |
| q014 | `ID document` | ожидаемо | concept (только документы) | «Passport» | A passport is the identity document. |
| q015 | `proof of income` | желательно | concept (только документы) | «Meeting notes» | No real income evidence in the corpus; the meeting notes mention a payslip (debatable). |
| q016 | `chocolate cake recipe` | ожидаемо | negative (только документы) | пустой список | Off-domain: nothing should be returned. |
