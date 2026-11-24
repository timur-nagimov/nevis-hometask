# existing-clients-fixture-42

Автор: Claude subagent (client-search research; the same author tuned the SQL), 2026-11-19.

Client-search fixture from research/client-search. Written by the author of the reference SQL, so it is not independent of that design.

Корпус: 42 клиентов, 0 документов (полный текст — в `suites/existing-clients-fixture-42.json`).

| id | Запрос | Уровень | Категория | Правильный ответ | Почему |
|---|---|---|---|---|---|
| can-1 | `NevisWealth` | обязательно | canonical (только клиенты) | John Doe <john.doe@neviswealth.com>; Peter Grant <p.grant@yahoo.com>; Sarah Connor <sarah.connor@neviswealth.com><br>первые 2: John Doe <john.doe@neviswealth.com>; Sarah Connor <sarah.connor@neviswealth.com> | Research fixture, group 'canonical'. |
| can-2 | `neviswealth` | обязательно | canonical (только клиенты) | John Doe <john.doe@neviswealth.com>; Peter Grant <p.grant@yahoo.com>; Sarah Connor <sarah.connor@neviswealth.com><br>первые 2: John Doe <john.doe@neviswealth.com>; Sarah Connor <sarah.connor@neviswealth.com> | Research fixture, group 'canonical'. |
| can-3 | `NEVISWEALTH` | обязательно | canonical (только клиенты) | John Doe <john.doe@neviswealth.com>; Peter Grant <p.grant@yahoo.com>; Sarah Connor <sarah.connor@neviswealth.com><br>первые 2: John Doe <john.doe@neviswealth.com>; Sarah Connor <sarah.connor@neviswealth.com> | Research fixture, group 'canonical'. |
| can-4 | `nevis` | обязательно | canonical (только клиенты) | Charlotte Nevis <charlotte@outlook.com>; John Doe <john.doe@neviswealth.com>; Peter Grant <p.grant@yahoo.com>; Sarah Connor <sarah.connor@neviswealth.com><br>первые 1: Charlotte Nevis <charlotte@outlook.com> | Research fixture, group 'canonical'. |
| can-5 | `wealth` | обязательно | canonical (только клиенты) | Anna-Maria Schmidt <anna-maria.schmidt+wealth@mail.example.co.uk>; John Doe <john.doe@neviswealth.com>; Peter Grant <p.grant@yahoo.com>; Sarah Connor <sarah.connor@neviswealth.com> | Research fixture, group 'canonical'. |
| can-6 | `nevis wealth` | обязательно | canonical (только клиенты) | John Doe <john.doe@neviswealth.com>; Peter Grant <p.grant@yahoo.com>; Sarah Connor <sarah.connor@neviswealth.com><br>не должно быть: Anna-Maria Schmidt <anna-maria.schmidt+wealth@mail.example.co.uk>; Charlotte Nevis <charlotte@outlook.com><br>прочие результаты не оцениваются | Research fixture, group 'canonical'. |
| name-1 | `joh` | обязательно | name substring (только клиенты) | Emily Johnson <emily.johnson@proton.me>; Johan Berg <johan.berg@telia.se>; John Doe <john.doe@neviswealth.com>; John Smith <john.smith@gmail.com>; Johnny Walker <johnny.walker@example.org><br>не должно быть: Jane Doe <jane.doe@gmail.com><br>прочие результаты не оцениваются | Research fixture, group 'name substring'. |
| name-2 | `john` | обязательно | name substring (только клиенты) | Emily Johnson <emily.johnson@proton.me>; John Doe <john.doe@neviswealth.com>; John Smith <john.smith@gmail.com>; Johnny Walker <johnny.walker@example.org><br>первые 2: John Doe <john.doe@neviswealth.com>; John Smith <john.smith@gmail.com><br>не должно быть: Jane Doe <jane.doe@gmail.com><br>прочие результаты не оцениваются | Research fixture, group 'name substring'. |
| name-3 | `doe` | обязательно | name substring (только клиенты) | Jane Doe <jane.doe@gmail.com>; John Doe <john.doe@neviswealth.com>; Kurt Doerr <kurt.doerr@kleinerperkins.com><br>первые 2: Jane Doe <jane.doe@gmail.com>; John Doe <john.doe@neviswealth.com><br>не должно быть: John Smith <john.smith@gmail.com><br>прочие результаты не оцениваются | Research fixture, group 'name substring'. |
| name-4 | `Doe` | обязательно | name substring (только клиенты) | Jane Doe <jane.doe@gmail.com>; John Doe <john.doe@neviswealth.com>; Kurt Doerr <kurt.doerr@kleinerperkins.com><br>первые 2: Jane Doe <jane.doe@gmail.com>; John Doe <john.doe@neviswealth.com><br>прочие результаты не оцениваются | Research fixture, group 'name substring'. |
| name-5 | `walker` | обязательно | name substring (только клиенты) | Johnny Walker <johnny.walker@example.org> | Research fixture, group 'name substring'. |
| name-6 | `smith` | обязательно | name substring (только клиенты) | John Smith <john.smith@gmail.com> | Research fixture, group 'name substring'. |
| name-7 | `olivia` | обязательно | name substring (только клиенты) | Olivia Stone <olivia.stone@icloud.com> | Research fixture, group 'name substring'. |
| name-8 | `michael` | обязательно | name substring (только клиенты) | Michael Scott <michael.scott@dundermifflin.com>; Michaela Novak <m.novak@seznam.cz><br>первые 1: Michael Scott <michael.scott@dundermifflin.com><br>прочие результаты не оцениваются | Research fixture, group 'name substring'. |
| full-1 | `john doe` | обязательно | full name (только клиенты) | John Doe <john.doe@neviswealth.com><br>первые 1: John Doe <john.doe@neviswealth.com><br>не должно быть: Jane Doe <jane.doe@gmail.com>; John Smith <john.smith@gmail.com><br>прочие результаты не оцениваются | Research fixture, group 'full name'. |
| full-2 | `doe john` | обязательно | full name (только клиенты) | John Doe <john.doe@neviswealth.com><br>первые 1: John Doe <john.doe@neviswealth.com><br>не должно быть: Jane Doe <jane.doe@gmail.com>; John Smith <john.smith@gmail.com><br>прочие результаты не оцениваются | Research fixture, group 'full name'. |
| full-3 | `John    Doe` | обязательно | full name (только клиенты) | John Doe <john.doe@neviswealth.com><br>первые 1: John Doe <john.doe@neviswealth.com><br>не должно быть: Jane Doe <jane.doe@gmail.com>; John Smith <john.smith@gmail.com><br>прочие результаты не оцениваются | Research fixture, group 'full name'. |
| full-4 | `  john doe  ` | обязательно | full name (только клиенты) | John Doe <john.doe@neviswealth.com><br>первые 1: John Doe <john.doe@neviswealth.com><br>не должно быть: Jane Doe <jane.doe@gmail.com>; John Smith <john.smith@gmail.com><br>прочие результаты не оцениваются | Research fixture, group 'full name'. |
| full-5 | `JOHN DOE` | обязательно | full name (только клиенты) | John Doe <john.doe@neviswealth.com><br>первые 1: John Doe <john.doe@neviswealth.com><br>не должно быть: Jane Doe <jane.doe@gmail.com>; John Smith <john.smith@gmail.com><br>прочие результаты не оцениваются | Research fixture, group 'full name'. |
| full-6 | `jane doe` | обязательно | full name (только клиенты) | Jane Doe <jane.doe@gmail.com><br>первые 1: Jane Doe <jane.doe@gmail.com><br>не должно быть: John Doe <john.doe@neviswealth.com><br>прочие результаты не оцениваются | Research fixture, group 'full name'. |
| full-7 | `doe, john` | обязательно | full name (только клиенты) | John Doe <john.doe@neviswealth.com><br>первые 1: John Doe <john.doe@neviswealth.com><br>не должно быть: Jane Doe <jane.doe@gmail.com>; John Smith <john.smith@gmail.com><br>прочие результаты не оцениваются | Research fixture, group 'full name'. |
| full-8 | `mary-jane watson` | обязательно | full name (только клиенты) | Mary-Jane Watson <mary_jane.watson@dailybugle.com> | Research fixture, group 'full name'. |
| comp-1 | `john nevis` | ожидаемо | name + company (только клиенты) | John Doe <john.doe@neviswealth.com> | Research fixture, group 'name + company'. |
| comp-2 | `sarah neviswealth` | ожидаемо | name + company (только клиенты) | Sarah Connor <sarah.connor@neviswealth.com> | Research fixture, group 'name + company'. |
| comp-3 | `doe gmail` | ожидаемо | name + company (только клиенты) | Jane Doe <jane.doe@gmail.com> | Research fixture, group 'name + company'. |
| comp-4 | `smith gmail.com` | ожидаемо | name + company (только клиенты) | John Smith <john.smith@gmail.com> | Research fixture, group 'name + company'. |
| mail-1 | `john.doe` | обязательно | e-mail (только клиенты) | John Doe <john.doe@neviswealth.com><br>первые 1: John Doe <john.doe@neviswealth.com><br>не должно быть: Jane Doe <jane.doe@gmail.com>; John Smith <john.smith@gmail.com><br>прочие результаты не оцениваются | Research fixture, group 'e-mail'. |
| mail-2 | `john.doe@neviswealth.com` | обязательно | e-mail (только клиенты) | John Doe <john.doe@neviswealth.com><br>первые 1: John Doe <john.doe@neviswealth.com><br>не должно быть: Jane Doe <jane.doe@gmail.com>; Sarah Connor <sarah.connor@neviswealth.com><br>прочие результаты не оцениваются | Research fixture, group 'e-mail'. |
| mail-3 | `JOHN.DOE@NEVISWEALTH.COM` | обязательно | e-mail (только клиенты) | John Doe <john.doe@neviswealth.com><br>первые 1: John Doe <john.doe@neviswealth.com><br>не должно быть: Jane Doe <jane.doe@gmail.com>; Sarah Connor <sarah.connor@neviswealth.com><br>прочие результаты не оцениваются | Research fixture, group 'e-mail'. |
| mail-4 | `neviswealth.com` | обязательно | e-mail (только клиенты) | John Doe <john.doe@neviswealth.com>; Sarah Connor <sarah.connor@neviswealth.com><br>первые 2: John Doe <john.doe@neviswealth.com>; Sarah Connor <sarah.connor@neviswealth.com><br>прочие результаты не оцениваются | Research fixture, group 'e-mail'. |
| mail-5 | `@neviswealth` | обязательно | e-mail (только клиенты) | John Doe <john.doe@neviswealth.com>; Sarah Connor <sarah.connor@neviswealth.com><br>первые 2: John Doe <john.doe@neviswealth.com>; Sarah Connor <sarah.connor@neviswealth.com><br>прочие результаты не оцениваются | Research fixture, group 'e-mail'. |
| mail-6 | `@gmail.com` | обязательно | e-mail (только клиенты) | Jane Doe <jane.doe@gmail.com>; John Smith <john.smith@gmail.com> | Research fixture, group 'e-mail'. |
| mail-7 | `co.uk` | обязательно | e-mail (только клиенты) | Anna-Maria Schmidt <anna-maria.schmidt+wealth@mail.example.co.uk> | Research fixture, group 'e-mail'. |
| mail-8 | `+wealth` | обязательно | e-mail (только клиенты) | Anna-Maria Schmidt <anna-maria.schmidt+wealth@mail.example.co.uk><br>первые 1: Anna-Maria Schmidt <anna-maria.schmidt+wealth@mail.example.co.uk><br>прочие результаты не оцениваются | Research fixture, group 'e-mail'. |
| mail-9 | `robert.brown@example.com` | обязательно | e-mail (только клиенты) | Robert BROWN <Robert.BROWN@Example.COM><br>первые 1: Robert BROWN <Robert.BROWN@Example.COM><br>прочие результаты не оцениваются | Research fixture, group 'e-mail'. |
| mail-10 | `mary_jane` | обязательно | e-mail (только клиенты) | Mary-Jane Watson <mary_jane.watson@dailybugle.com> | Research fixture, group 'e-mail'. |
| desc-1 | `retired teacher` | обязательно | description (только клиенты) | Jane Doe <jane.doe@gmail.com>; Laura Bennett <laura.bennett@schools.example.edu><br>первые 1: Jane Doe <jane.doe@gmail.com><br>не должно быть: George Hill <george.hill@navy.example.mil><br>прочие результаты не оцениваются | Research fixture, group 'description'. |
| desc-2 | `teacher` | обязательно | description (только клиенты) | Jane Doe <jane.doe@gmail.com>; Laura Bennett <laura.bennett@schools.example.edu><br>не должно быть: George Hill <george.hill@navy.example.mil><br>прочие результаты не оцениваются | Research fixture, group 'description'. |
| desc-3 | `municipal bonds` | обязательно | description (только клиенты) | Jane Doe <jane.doe@gmail.com> | Research fixture, group 'description'. |
| desc-4 | `sustainable investing` | обязательно | description (только клиенты) | John Doe <john.doe@neviswealth.com> | Research fixture, group 'description'. |
| desc-5 | `paper company` | обязательно | description (только клиенты) | Michael Scott <michael.scott@dundermifflin.com> | Research fixture, group 'description'. |
| desc-6 | `crypto` | обязательно | description (только клиенты) | Jon Snow <jon.snow@nightswatch.org>; Mia Rossi <mia.rossi@libero.it> | Research fixture, group 'description'. |
| desc-7 | `estate planning` | обязательно | description (только клиенты) | Seán O'Brien <sean.obrien@eircom.ie><br>не должно быть: Henry Longfellow <h.longfellow@example.com><br>прочие результаты не оцениваются | Research fixture, group 'description'. |
| desc-8 | `discretionary trust` | обязательно | description (только клиенты) | Henry Longfellow <h.longfellow@example.com> | Research fixture, group 'description'. |
| soc-1 | `linkedin` | желательно | social links (только клиенты) | John Doe <john.doe@neviswealth.com>; Michael Scott <michael.scott@dundermifflin.com>; Sarah Connor <sarah.connor@neviswealth.com><br>прочие результаты не оцениваются | Matches only social_links; the assignment lists e-mails, name and description, so this is a nice-to-have. |
| soc-2 | `jdoe_invest` | желательно | social links (только клиенты) | John Doe <john.doe@neviswealth.com><br>прочие результаты не оцениваются | Matches only social_links; the assignment lists e-mails, name and description, so this is a nice-to-have. |
| soc-3 | `johndoe` | желательно | social links (только клиенты) | John Doe <john.doe@neviswealth.com><br>прочие результаты не оцениваются | Matches only social_links; the assignment lists e-mails, name and description, so this is a nice-to-have. |
| soc-4 | `github.com/jsmith` | желательно | social links (только клиенты) | John Smith <john.smith@gmail.com><br>прочие результаты не оцениваются | Matches only social_links; the assignment lists e-mails, name and description, so this is a nice-to-have. |
| soc-5 | `https` | желательно | social links (только клиенты) | John Doe <john.doe@neviswealth.com>; John Smith <john.smith@gmail.com>; Johnny Walker <johnny.walker@example.org>; Mary-Jane Watson <mary_jane.watson@dailybugle.com>; Mia Rossi <mia.rossi@libero.it>; Michael Scott <michael.scott@dundermifflin.com>; Sarah Connor <sarah.connor@neviswealth.com><br>прочие результаты не оцениваются | Matches only social_links; the assignment lists e-mails, name and description, so this is a nice-to-have. |
| typo-1 | `jhon` | желательно | typos (только клиенты) | John Doe <john.doe@neviswealth.com>; John Smith <john.smith@gmail.com><br>прочие результаты не оцениваются | Research fixture, group 'typos'. |
| typo-2 | `neviswelth` | желательно | typos (только клиенты) | John Doe <john.doe@neviswealth.com>; Sarah Connor <sarah.connor@neviswealth.com><br>прочие результаты не оцениваются | Research fixture, group 'typos'. |
| typo-3 | `micheal` | желательно | typos (только клиенты) | Michael Scott <michael.scott@dundermifflin.com><br>первые 1: Michael Scott <michael.scott@dundermifflin.com><br>прочие результаты не оцениваются | Research fixture, group 'typos'. |
| typo-4 | `neviswealht` | желательно | typos (только клиенты) | John Doe <john.doe@neviswealth.com>; Sarah Connor <sarah.connor@neviswealth.com><br>прочие результаты не оцениваются | Research fixture, group 'typos'. |
| typo-5 | `jonh doe` | желательно | typos (только клиенты) | John Doe <john.doe@neviswealth.com><br>прочие результаты не оцениваются | Research fixture, group 'typos'. |
| typo-6 | `retired techer` | желательно | typos (только клиенты) | Jane Doe <jane.doe@gmail.com><br>прочие результаты не оцениваются | Research fixture, group 'typos'. |
| typo-7 | `garsia` | желательно | typos (только клиенты) | José García <jose.garcia@bancosol.es><br>прочие результаты не оцениваются | Research fixture, group 'typos'. |
| typo-8 | `jhon.doe@neviswealth.com` | желательно | typos (только клиенты) | John Doe <john.doe@neviswealth.com><br>прочие результаты не оцениваются | Research fixture, group 'typos'. |
| typo-9 | `sarah conor` | желательно | typos (только клиенты) | Sarah Connor <sarah.connor@neviswealth.com><br>прочие результаты не оцениваются | Research fixture, group 'typos'. |
| typo-10 | `sustainble investing` | желательно | typos (только клиенты) | John Doe <john.doe@neviswealth.com><br>прочие результаты не оцениваются | Research fixture, group 'typos'. |
| dia-1 | `jose` | ожидаемо | diacritics (только клиенты) | José García <jose.garcia@bancosol.es><br>первые 1: José García <jose.garcia@bancosol.es><br>прочие результаты не оцениваются | Research fixture, group 'diacritics'. |
| dia-2 | `José` | ожидаемо | diacritics (только клиенты) | José García <jose.garcia@bancosol.es><br>первые 1: José García <jose.garcia@bancosol.es><br>прочие результаты не оцениваются | Research fixture, group 'diacritics'. |
| dia-3 | `JOSÉ GARCÍA` | ожидаемо | diacritics (только клиенты) | José García <jose.garcia@bancosol.es> | Research fixture, group 'diacritics'. |
| dia-4 | `muller` | ожидаемо | diacritics (только клиенты) | Jürgen Müller <juergen.mueller@deutschebank.de> | Research fixture, group 'diacritics'. |
| dia-5 | `Müller` | ожидаемо | diacritics (только клиенты) | Jürgen Müller <juergen.mueller@deutschebank.de> | Research fixture, group 'diacritics'. |
| dia-6 | `mueller` | ожидаемо | diacritics (только клиенты) | Jürgen Müller <juergen.mueller@deutschebank.de> | Research fixture, group 'diacritics'. |
| dia-7 | `sean obrien` | ожидаемо | diacritics (только клиенты) | Seán O'Brien <sean.obrien@eircom.ie> | Research fixture, group 'diacritics'. |
| dia-8 | `lukasz wojcik` | ожидаемо | diacritics (только клиенты) | Łukasz Wójcik <lukasz.wojcik@wp.pl> | Research fixture, group 'diacritics'. |
| dia-9 | `soren` | ожидаемо | diacritics (только клиенты) | Søren Østergaard <soren.ostergaard@mail.dk> | Research fixture, group 'diacritics'. |
| dia-10 | `francois lefevre` | ожидаемо | diacritics (только клиенты) | François Lefèvre <francois.lefevre@orange.fr> | Research fixture, group 'diacritics'. |
| dia-11 | `Zoë Brontë` | ожидаемо | diacritics (только клиенты) | Zoe Bronte <zoe.bronte@example.com> | Research fixture, group 'diacritics'. |
| dia-12 | `weiss` | ожидаемо | diacritics (только клиенты) | Jörg Weiß <joerg.weiss@gmx.de> | Research fixture, group 'diacritics'. |
| dia-13 | `Weiß` | ожидаемо | diacritics (только клиенты) | Jörg Weiß <joerg.weiss@gmx.de> | Research fixture, group 'diacritics'. |
| dia-14 | `hauptstrasse` | ожидаемо | diacritics (только клиенты) | Jörg Weiß <joerg.weiss@gmx.de> | Research fixture, group 'diacritics'. |
| dia-15 | `munchen` | ожидаемо | diacritics (только клиенты) | Jürgen Müller <juergen.mueller@deutschebank.de> | Research fixture, group 'diacritics'. |
| dia-16 | `José` | ожидаемо | diacritics (только клиенты) | José García <jose.garcia@bancosol.es><br>первые 1: José García <jose.garcia@bancosol.es><br>прочие результаты не оцениваются | Research fixture, group 'diacritics'. |
| dia-17 | `İBRAHİM` | ожидаемо | diacritics (только клиенты) | İbrahim Yıldız <ibrahim.yildiz@turk.example.tr> | Research fixture, group 'diacritics'. |
| dia-18 | `yildiz istanbul` | ожидаемо | diacritics (только клиенты) | İbrahim Yıldız <ibrahim.yildiz@turk.example.tr> | Research fixture, group 'diacritics'. |
| uni-1 | `петров` | ожидаемо | unicode / emoji (только клиенты) | Иван Петров <ivan.petrov@yandex.ru> | Research fixture, group 'unicode / emoji'. |
| uni-2 | `ПЕТРОВ` | ожидаемо | unicode / emoji (только клиенты) | Иван Петров <ivan.petrov@yandex.ru> | Research fixture, group 'unicode / emoji'. |
| uni-3 | `иван облигациями` | ожидаемо | unicode / emoji (только клиенты) | Иван Петров <ivan.petrov@yandex.ru> | Research fixture, group 'unicode / emoji'. |
| uni-4 | `上海` | ожидаемо | unicode / emoji (только клиенты) | Wei Li <li.wei@alibaba.example.cn> | Research fixture, group 'unicode / emoji'. |
| uni-5 | `李` | ожидаемо | unicode / emoji (только клиенты) | 伟 李 <liwei88@qq.com> | Research fixture, group 'unicode / emoji'. |
| uni-6 | `退休教师` | ожидаемо | unicode / emoji (только клиенты) | 伟 李 <liwei88@qq.com> | Research fixture, group 'unicode / emoji'. |
| uni-7 | `🚀` | ожидаемо | unicode / emoji (только клиенты) | Mia Rossi <mia.rossi@libero.it> | Research fixture, group 'unicode / emoji'. |
| uni-8 | `crypto 🚀` | ожидаемо | unicode / emoji (только клиенты) | Mia Rossi <mia.rossi@libero.it> | Research fixture, group 'unicode / emoji'. |
| uni-9 | `ｊｏｈｎ` | ожидаемо | unicode / emoji (только клиенты) | John Doe <john.doe@neviswealth.com>; John Smith <john.smith@gmail.com><br>прочие результаты не оцениваются | Research fixture, group 'unicode / emoji'. |
| uni-10 | `john\xa0doe` | ожидаемо | unicode / emoji (только клиенты) | John Doe <john.doe@neviswealth.com><br>не должно быть: Jane Doe <jane.doe@gmail.com><br>прочие результаты не оцениваются | Research fixture, group 'unicode / emoji'. |
| uni-11 | `💩` | ожидаемо | unicode / emoji (только клиенты) | пустой список | Research fixture, group 'unicode / emoji': nothing matches. |
| short-1 | `j` | ожидаемо | short (1-2 chars) (только клиенты) | не меньше 1 результатов<br>прочие результаты не оцениваются | Research fixture, group 'short (1-2 chars)'. |
| short-2 | `jo` | ожидаемо | short (1-2 chars) (только клиенты) | Emily Johnson <emily.johnson@proton.me>; Johan Berg <johan.berg@telia.se>; John Doe <john.doe@neviswealth.com>; John Smith <john.smith@gmail.com>; Johnny Walker <johnny.walker@example.org>; Jon Snow <jon.snow@nightswatch.org>; Jörg Weiß <joerg.weiss@gmx.de>; José García <jose.garcia@bancosol.es><br>прочие результаты не оцениваются | Research fixture, group 'short (1-2 chars)'. |
| short-3 | `li` | ожидаемо | short (1-2 chars) (только клиенты) | Wei Li <li.wei@alibaba.example.cn><br>первые 1: Wei Li <li.wei@alibaba.example.cn><br>прочие результаты не оцениваются | Research fixture, group 'short (1-2 chars)'. |
| short-4 | `ng` | ожидаемо | short (1-2 chars) (только клиенты) | Mai Ng <mai.ng@fpt.vn><br>первые 1: Mai Ng <mai.ng@fpt.vn><br>прочие результаты не оцениваются | Research fixture, group 'short (1-2 chars)'. |
| short-5 | `al` | ожидаемо | short (1-2 chars) (только клиенты) | Al Baker <al.baker@example.com><br>первые 1: Al Baker <al.baker@example.com><br>прочие результаты не оцениваются | Research fixture, group 'short (1-2 chars)'. |
| short-6 | `a` | ожидаемо | short (1-2 chars) (только клиенты) | не меньше 20 результатов<br>прочие результаты не оцениваются | Research fixture, group 'short (1-2 chars)'. |
| long-1 | `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa…` | ожидаемо | long (1,000 chars) (только клиенты) | пустой список | Research fixture, group 'long (1,000 chars)': nothing matches. The query is 1,000 characters long; an API that caps the length may answer 422 instead. |
| long-2 | `portfolio review meeting quarterly statement portfolio review meeting quarter…` | ожидаемо | long (1,000 chars) (только клиенты) | пустой список | Research fixture, group 'long (1,000 chars)': nothing matches. The query is 1,000 characters long; an API that caps the length may answer 422 instead. |
| long-3 | `john john john john john john john john john john john john john john john jo…` | ожидаемо | long (1,000 chars) (только клиенты) | John Doe <john.doe@neviswealth.com>; John Smith <john.smith@gmail.com><br>прочие результаты не оцениваются | Research fixture, group 'long (1,000 chars)'. The query is 1,000 characters long; an API that caps the length may answer 422 instead. |
| meta-1 | `%` | ожидаемо | metacharacters (только клиенты) | Mary-Jane Watson <mary_jane.watson@dailybugle.com>; Robert BROWN <Robert.BROWN@Example.COM> | Research fixture, group 'metacharacters'. |
| meta-2 | `_` | ожидаемо | metacharacters (только клиенты) | David Slash <d.slash@corp.example.com>; Mary-Jane Watson <mary_jane.watson@dailybugle.com> | Research fixture, group 'metacharacters'. |
| meta-3 | `\` | ожидаемо | metacharacters (только клиенты) | David Slash <d.slash@corp.example.com> | Research fixture, group 'metacharacters'. |
| meta-4 | `100%` | ожидаемо | metacharacters (только клиенты) | Robert BROWN <Robert.BROWN@Example.COM> | Research fixture, group 'metacharacters'. |
| meta-5 | `%doe%` | ожидаемо | metacharacters (только клиенты) | пустой список | Research fixture, group 'metacharacters': nothing matches. |
| meta-6 | `j_hn` | ожидаемо | metacharacters (только клиенты) | пустой список | Research fixture, group 'metacharacters': nothing matches. |
| meta-7 | `jo%n` | ожидаемо | metacharacters (только клиенты) | пустой список | Research fixture, group 'metacharacters': nothing matches. |
| meta-8 | `c:\clients` | ожидаемо | metacharacters (только клиенты) | David Slash <d.slash@corp.example.com> | Research fixture, group 'metacharacters'. |
| meta-9 | `\\` | ожидаемо | metacharacters (только клиенты) | пустой список | Research fixture, group 'metacharacters': nothing matches. |
| meta-10 | `discount_rate` | ожидаемо | metacharacters (только клиенты) | Mary-Jane Watson <mary_jane.watson@dailybugle.com> | Research fixture, group 'metacharacters'. |
| meta-11 | `(john\|jane)` | ожидаемо | metacharacters (только клиенты) | пустой список | Research fixture, group 'metacharacters': nothing matches. |
| meta-12 | `.*` | ожидаемо | metacharacters (только клиенты) | пустой список | Research fixture, group 'metacharacters': nothing matches. |
| meta-13 | `％` | ожидаемо | metacharacters (только клиенты) | Mary-Jane Watson <mary_jane.watson@dailybugle.com>; Robert BROWN <Robert.BROWN@Example.COM> | Research fixture, group 'metacharacters'. |
| meta-14 | `j＿hn` | ожидаемо | metacharacters (только клиенты) | пустой список | Research fixture, group 'metacharacters': nothing matches. |
| inj-1 | `o'brien` | ожидаемо | quotes / injection (только клиенты) | Seán O'Brien <sean.obrien@eircom.ie> | Research fixture, group 'quotes / injection'. |
| inj-2 | `O’Brien` | ожидаемо | quotes / injection (только клиенты) | Seán O'Brien <sean.obrien@eircom.ie> | Research fixture, group 'quotes / injection'. |
| inj-3 | `'; DROP TABLE clients; --` | ожидаемо | quotes / injection (только клиенты) | Bobby Tables <bobby.tables@xkcd.com> | Research fixture, group 'quotes / injection'. |
| inj-4 | `" OR 1=1 --` | ожидаемо | quotes / injection (только клиенты) | пустой список | Research fixture, group 'quotes / injection': nothing matches. |
| inj-5 | `john' OR '1'='1` | ожидаемо | quotes / injection (только клиенты) | пустой список | Research fixture, group 'quotes / injection': nothing matches. |
| inj-6 | `$$; SELECT pg_sleep(10); $$` | ожидаемо | quotes / injection (только клиенты) | пустой список | Research fixture, group 'quotes / injection': nothing matches. |
| inj-7 | `--` | ожидаемо | quotes / injection (только клиенты) | Bobby Tables <bobby.tables@xkcd.com> | Research fixture, group 'quotes / injection'. |
| inj-8 | `john & doe \| !smith:*` | ожидаемо | quotes / injection (только клиенты) | пустой список | Research fixture, group 'quotes / injection': nothing matches. |
| none-1 | `zzzzqqq` | ожидаемо | no match (только клиенты) | пустой список | Research fixture, group 'no match': nothing matches. |
| none-2 | `xylophone` | ожидаемо | no match (только клиенты) | пустой список | Research fixture, group 'no match': nothing matches. |
| none-3 | `nobody@nowhere.test` | ожидаемо | no match (только клиенты) | пустой список | Research fixture, group 'no match': nothing matches. |
| none-4 | `john xyzzy` | ожидаемо | no match (только клиенты) | пустой список | Research fixture, group 'no match': nothing matches. |
| none-5 | `qwertyuiop` | ожидаемо | no match (только клиенты) | пустой список | Research fixture, group 'no match': nothing matches. |
| none-6 | `0123456789` | ожидаемо | no match (только клиенты) | пустой список | Research fixture, group 'no match': nothing matches. |
| common-1 | `com` | ожидаемо | common substring (только клиенты) | первые 1: Tom Compton <t.compton@sky.net><br>не меньше 14 результатов<br>прочие результаты не оцениваются | Research fixture, group 'common substring'. |
| common-2 | `gmail` | ожидаемо | common substring (только клиенты) | Jane Doe <jane.doe@gmail.com>; John Smith <john.smith@gmail.com> | Research fixture, group 'common substring'. |
| common-3 | `e` | ожидаемо | common substring (только клиенты) | не меньше 20 результатов<br>прочие результаты не оцениваются | Research fixture, group 'common substring'. |
| common-4 | `example` | ожидаемо | common substring (только клиенты) | не меньше 9 результатов<br>прочие результаты не оцениваются | Research fixture, group 'common substring'. |

## Проверки HTTP-контракта

| id | Запрос | Ожидаемый код | Почему |
|---|---|---|---|
| h-blank-1 | `GET /search ?q=` | 400 или 422 | blank query '': q is required (an empty 200 [] is also defensible) |
| h-blank-2 | `GET /search ?q=   ` | 400 или 422 | blank query '   ': q is required (an empty 200 [] is also defensible) |
| h-blank-3 | `GET /search ?q=\t\n ` | 400 или 422 | blank query '\t\n ': q is required (an empty 200 [] is also defensible) |
| h-blank-4 | `GET /search ?q=\xa0\u3000` | 400 или 422 | blank query '\xa0\u3000': q is required (an empty 200 [] is also defensible) |
