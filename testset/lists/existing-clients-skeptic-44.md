# existing-clients-skeptic-44

Автор: Claude subagent (adversarial reviewer, wrote the cases before reading any fixture), 2026-11-20.

Independent adversarial client-search cases from research/_skeptic/client. Level 'nice' also holds the cases the author marked as debatable (strict reading of the requirement). Some queries deliberately contain invisible or invalid Unicode; they are stored as \u escapes.

Корпус: 44 клиентов, 0 документов (полный текст — в `suites/existing-clients-skeptic-44.json`).

| id | Запрос | Уровень | Категория | Правильный ответ | Почему |
|---|---|---|---|---|---|
| A01 | `NevisWealth` | обязательно | e-mail local parts and domains (только клиенты) | John Doe <john.doe@neviswealth.com>; Mary Major <M.Major@NEVISWEALTH.COM>; Peter Parker <pparker@dailybugle.com><br>John Doe <john.doe@neviswealth.com> выше, чем Peter Parker <pparker@dailybugle.com><br>Mary Major <M.Major@NEVISWEALTH.COM> выше, чем Peter Parker <pparker@dailybugle.com><br>не должно быть: Nevis Wealthy <nevis.w@gmail.com> | [req] canonical; e-mail hits should outrank the description-only hit |
| A02 | `neviswealth.com` | обязательно | e-mail local parts and domains (только клиенты) | John Doe <john.doe@neviswealth.com>; Mary Major <M.Major@NEVISWEALTH.COM>; Peter Parker <pparker@dailybugle.com> | [req] e-mail local parts and domains |
| A03 | `@neviswealth` | обязательно | e-mail local parts and domains (только клиенты) | John Doe <john.doe@neviswealth.com>; Mary Major <M.Major@NEVISWEALTH.COM> | [req] e-mail local parts and domains |
| A04 | `john.doe` | обязательно | e-mail local parts and domains (только клиенты) | John Doe <john.doe@neviswealth.com> | [req] e-mail local parts and domains |
| A05 | `doe@nevis` | обязательно | e-mail local parts and domains (только клиенты) | John Doe <john.doe@neviswealth.com> | [req] e-mail local parts and domains |
| A06 | `jon.doering@gmail.com` | обязательно | e-mail local parts and domains (только клиенты) | Jonathan Doering <jon.doering@gmail.com> | [req] e-mail local parts and domains |
| A07 | `JOHN.DOE@NEVISWEALTH.COM` | обязательно | e-mail local parts and domains (только клиенты) | John Doe <john.doe@neviswealth.com> | [req] e-mail local parts and domains |
| A08 | `wealth` | обязательно | e-mail local parts and domains (только клиенты) | John Doe <john.doe@neviswealth.com>; Mary Major <M.Major@NEVISWEALTH.COM>; Nevis Wealthy <nevis.w@gmail.com>; Peter Parker <pparker@dailybugle.com>; Sam Taylor <sam+wealth@proton.me> | [req] e-mail local parts and domains |
| A09 | `sam+wealth` | обязательно | e-mail local parts and domains (только клиенты) | Sam Taylor <sam+wealth@proton.me> | [req] e-mail local parts and domains |
| A10 | `zoe_sj` | обязательно | e-mail local parts and domains (только клиенты) | Zoë Smith-Jones <zoe_sj@outlook.com> | [req] e-mail local parts and domains |
| A11 | `.co.uk` | обязательно | e-mail local parts and domains (только клиенты) | Séverine O'Brien-Müller <severine.obrien@example.co.uk> | [req] e-mail local parts and domains |
| A12 | `hk-capital` | обязательно | e-mail local parts and domains (только клиенты) | Li Ng <li.ng@hk-capital.hk> | [req] e-mail local parts and domains |
| A13 | `m.major@neviswealth.com` | обязательно | e-mail local parts and domains (только клиенты) | Mary Major <M.Major@NEVISWEALTH.COM> | [req] stored e-mail is upper case |
| A14 | `emile.zola@example.fr` | обязательно | e-mail local parts and domains (только клиенты) | ÉMILE ZOLA <EMILE.ZOLA@EXAMPLE.FR> | [req] e-mail local parts and domains |
| A15 | `gmail` | обязательно | e-mail local parts and domains (только клиенты) | Jonathan Doering <jon.doering@gmail.com>; Nevis Wealthy <nevis.w@gmail.com> | [req] e-mail local parts and domains |
| A16 | `example` | обязательно | e-mail local parts and domains (только клиенты) | ÉMILE ZOLA <EMILE.ZOLA@EXAMPLE.FR>; Ｋｅｎｊｉ Tanaka <kenji.tanaka@example.jp>; محمد الفاسي <m.alfassi@example.ma>; Null None <null@example.com>; Séverine O'Brien-Müller <severine.obrien@example.co.uk>; 伟 王 <wang.wei@example.cn>; יעל כהן <yael.cohen@example.co.il> | [req] e-mail local parts and domains |
| B01 | `@` | обязательно | '@' and dots, stray punctuation (только клиенты) | John Doe <john.doe@neviswealth.com>; Jane Doe <jane@doe-family.org>; Jonathan Doering <jon.doering@gmail.com>; Mary Major <M.Major@NEVISWEALTH.COM>; Peter Parker <pparker@dailybugle.com>; Nevis Wealthy <nevis.w@gmail.com>; Séverine O'Brien-Müller <severine.obrien@example.co.uk>; Siobhán O’Connor <siobhan@greenfield.ie>; D’Angelo McDonald <dm@mcd-holdings.com>; José Ángel García Márquez <jgarcia@santander.es>; Zoë Smith-Jones <zoe_sj@outlook.com>; Li Ng <li.ng@hk-capital.hk>; 伟 王 <wang.wei@example.cn>; Алексей Смирнов <a.smirnov@yandex.ru>; Алёна Королёва <alena.k@mail.ru>; Παναγιώτης Παπαδόπουλος <p.papadopoulos@otenet.gr>; Mehmet Yıldırım <mehmet.y@turkcell.com.tr>; İbrahim Çelik <ibrahim.celik@koc.com.tr>; Łukasz Wójcik <lukasz.w@wp.pl>; Bjørn Ødegård <bjorn@fjordinvest.no>; Jürgen Groß <j.gross@web.de>; Hương Nguyễn Thị <huong.nt@fpt.vn>; محمد الفاسي <m.alfassi@example.ma>; יעל כהן <yael.cohen@example.co.il>; Renée Leclerc <renee@leclerc.fr>; Percy Cent <percy@100percent.io>; Robert Tables <bobby@xkcd.com>; Anna-Maria von der Heide <am.vdheide@t-online.de>; Jean-Luc Picard <jl.picard@starfleet.org>; John Smith <john.smith@acme.com>; John Smith <jsmith1975@yahoo.com>; Mike Johnson <mike.j@acme.com>; Bob Jones <bob@smithfield.com>; Null None <null@example.com>; A B <ab@c.de>; Olivia Stone <olivia@stonecap.com>; Sam Taylor <sam+wealth@proton.me>; ÉMILE ZOLA <EMILE.ZOLA@EXAMPLE.FR>; Ｋｅｎｊｉ Tanaka <kenji.tanaka@example.jp>; Marie Claire Dupont <mc.dupont@orange.fr>; Zero​Width Joiner <zw@invisible.dev>; Anne–Sophie Lefèvre <as.lefevre@laposte.net>; Lorem Ipsum <lorem@ipsum.io>; Val Entine <val@hearts.io> | [req] matches every client (every e-mail has an @) |
| B02 | `.` | обязательно | '@' and dots, stray punctuation (только клиенты) | John Doe <john.doe@neviswealth.com>; Jane Doe <jane@doe-family.org>; Jonathan Doering <jon.doering@gmail.com>; Mary Major <M.Major@NEVISWEALTH.COM>; Peter Parker <pparker@dailybugle.com>; Nevis Wealthy <nevis.w@gmail.com>; Séverine O'Brien-Müller <severine.obrien@example.co.uk>; Siobhán O’Connor <siobhan@greenfield.ie>; D’Angelo McDonald <dm@mcd-holdings.com>; José Ángel García Márquez <jgarcia@santander.es>; Zoë Smith-Jones <zoe_sj@outlook.com>; Li Ng <li.ng@hk-capital.hk>; 伟 王 <wang.wei@example.cn>; Алексей Смирнов <a.smirnov@yandex.ru>; Алёна Королёва <alena.k@mail.ru>; Παναγιώτης Παπαδόπουλος <p.papadopoulos@otenet.gr>; Mehmet Yıldırım <mehmet.y@turkcell.com.tr>; İbrahim Çelik <ibrahim.celik@koc.com.tr>; Łukasz Wójcik <lukasz.w@wp.pl>; Bjørn Ødegård <bjorn@fjordinvest.no>; Jürgen Groß <j.gross@web.de>; Hương Nguyễn Thị <huong.nt@fpt.vn>; محمد الفاسي <m.alfassi@example.ma>; יעל כהן <yael.cohen@example.co.il>; Renée Leclerc <renee@leclerc.fr>; Percy Cent <percy@100percent.io>; Robert Tables <bobby@xkcd.com>; Anna-Maria von der Heide <am.vdheide@t-online.de>; Jean-Luc Picard <jl.picard@starfleet.org>; John Smith <john.smith@acme.com>; John Smith <jsmith1975@yahoo.com>; Mike Johnson <mike.j@acme.com>; Bob Jones <bob@smithfield.com>; Null None <null@example.com>; A B <ab@c.de>; Olivia Stone <olivia@stonecap.com>; Sam Taylor <sam+wealth@proton.me>; ÉMILE ZOLA <EMILE.ZOLA@EXAMPLE.FR>; Ｋｅｎｊｉ Tanaka <kenji.tanaka@example.jp>; Marie Claire Dupont <mc.dupont@orange.fr>; Zero​Width Joiner <zw@invisible.dev>; Anne–Sophie Lefèvre <as.lefevre@laposte.net>; Lorem Ipsum <lorem@ipsum.io>; Val Entine <val@hearts.io> | [req] matches every client |
| B03 | `john.doe@` | обязательно | '@' and dots, stray punctuation (только клиенты) | John Doe <john.doe@neviswealth.com> | [req] '@' and dots, stray punctuation |
| B04 | `j.doe` | желательно | '@' and dots, stray punctuation (только клиенты) | пустой список | [debatable] initial + surname; literal substring says nothing |
| B05 | `doe.` | желательно | '@' and dots, stray punctuation (только клиенты) | Jane Doe <jane@doe-family.org>; John Doe <john.doe@neviswealth.com><br>прочие результаты не оцениваются | [nice] trailing full stop glued to the word |
| B06 | `<john.doe@neviswealth.com>` | желательно | '@' and dots, stray punctuation (только клиенты) | John Doe <john.doe@neviswealth.com> | [nice] pasted from a mail client |
| B07 | `John Doe <john.doe@neviswealth.com>` | желательно | '@' and dots, stray punctuation (только клиенты) | John Doe <john.doe@neviswealth.com> | [nice] pasted from a mail client |
| B08 | `"John Doe"` | желательно | '@' and dots, stray punctuation (только клиенты) | John Doe <john.doe@neviswealth.com><br>первым: John Doe <john.doe@neviswealth.com><br>прочие результаты не оцениваются | [nice] quoted name |
| B09 | `(john doe)` | желательно | '@' and dots, stray punctuation (только клиенты) | John Doe <john.doe@neviswealth.com><br>первым: John Doe <john.doe@neviswealth.com><br>прочие результаты не оцениваются | [nice] '@' and dots, stray punctuation |
| B10 | `john.doe@neviswealth.com,` | обязательно | '@' and dots, stray punctuation (только клиенты) | John Doe <john.doe@neviswealth.com> | [req] trailing comma is a separator |
| B11 | `mailto:john.doe@neviswealth.com` | желательно | '@' and dots, stray punctuation (только клиенты) | John Doe <john.doe@neviswealth.com> | [nice] '@' and dots, stray punctuation |
| B12 | `https://www.neviswealth.com` | желательно | '@' and dots, stray punctuation (только клиенты) | John Doe <john.doe@neviswealth.com>; Mary Major <M.Major@NEVISWEALTH.COM>; Peter Parker <pparker@dailybugle.com><br>прочие результаты не оцениваются | [nice] company URL pasted |
| C01 | `  nEvIsWeAlTh  ` | обязательно | case and whitespace (только клиенты) | John Doe <john.doe@neviswealth.com>; Mary Major <M.Major@NEVISWEALTH.COM>; Peter Parker <pparker@dailybugle.com> | [req] case and whitespace |
| C02 | `\tJohn\n Doe  ` | обязательно | case and whitespace (только клиенты) | John Doe <john.doe@neviswealth.com><br>первым: John Doe <john.doe@neviswealth.com><br>John Doe <john.doe@neviswealth.com> выше, чем John Smith <john.smith@acme.com><br>не должно быть: Jane Doe <jane@doe-family.org>; Jonathan Doering <jon.doering@gmail.com><br>прочие результаты не оцениваются | [req] smith1 (John Smith, 'Referred by Jane Doe') legitimately matches both tokens across fields |
| C03 | `John\xa0Doe` | ожидаемо | case and whitespace (только клиенты) | John Doe <john.doe@neviswealth.com><br>первым: John Doe <john.doe@neviswealth.com><br>не должно быть: Jane Doe <jane@doe-family.org><br>прочие результаты не оцениваются | [norm] NBSP separator |
| C04 | `marie claire` | ожидаемо | case and whitespace (только клиенты) | Marie Claire Dupont <mc.dupont@orange.fr> | [norm] stored name has an NBSP |
| C05 | `JOHN` | обязательно | case and whitespace (только клиенты) | John Doe <john.doe@neviswealth.com>; Mike Johnson <mike.j@acme.com>; John Smith <john.smith@acme.com>; John Smith <jsmith1975@yahoo.com><br>первым: John Doe <john.doe@neviswealth.com> или John Smith <john.smith@acme.com> или John Smith <jsmith1975@yahoo.com><br>John Smith <john.smith@acme.com> выше, чем Mike Johnson <mike.j@acme.com><br>John Doe <john.doe@neviswealth.com> выше, чем Mike Johnson <mike.j@acme.com><br>прочие результаты не оцениваются | [req] whole word John before prefix Johnson |
| C06 | `dOe` | обязательно | case and whitespace (только клиенты) | Jane Doe <jane@doe-family.org>; John Doe <john.doe@neviswealth.com>; Jonathan Doering <jon.doering@gmail.com>; John Smith <john.smith@acme.com><br>первым: Jane Doe <jane@doe-family.org> или John Doe <john.doe@neviswealth.com><br>Jane Doe <jane@doe-family.org> выше, чем Jonathan Doering <jon.doering@gmail.com><br>John Doe <john.doe@neviswealth.com> выше, чем John Smith <john.smith@acme.com><br>прочие результаты не оцениваются | [req] case and whitespace |
| D01 | `doe john` | обязательно | several words, any order (только клиенты) | John Doe <john.doe@neviswealth.com><br>первым: John Doe <john.doe@neviswealth.com><br>не должно быть: Jane Doe <jane@doe-family.org><br>прочие результаты не оцениваются | [req] several words, any order |
| D02 | `Doe, John` | обязательно | several words, any order (только клиенты) | John Doe <john.doe@neviswealth.com><br>первым: John Doe <john.doe@neviswealth.com><br>не должно быть: Jane Doe <jane@doe-family.org><br>прочие результаты не оцениваются | [req] several words, any order |
| D03 | `john;doe` | обязательно | several words, any order (только клиенты) | John Doe <john.doe@neviswealth.com><br>первым: John Doe <john.doe@neviswealth.com><br>не должно быть: Jane Doe <jane@doe-family.org><br>прочие результаты не оцениваются | [req] several words, any order |
| D04 | `garcia jose angel` | ожидаемо | several words, any order (только клиенты) | José Ángel García Márquez <jgarcia@santander.es> | [norm] several words, any order |
| D05 | `márquez GARCÍA` | ожидаемо | several words, any order (только клиенты) | José Ángel García Márquez <jgarcia@santander.es> | [norm] several words, any order |
| D06 | `esg engineer retired` | обязательно | several words, any order (только клиенты) | Jonathan Doering <jon.doering@gmail.com> | [req] several words, any order |
| D07 | `john john john` | обязательно | several words, any order (только клиенты) | John Doe <john.doe@neviswealth.com>; Mike Johnson <mike.j@acme.com>; John Smith <john.smith@acme.com>; John Smith <jsmith1975@yahoo.com> | [req] duplicate tokens |
| D08 | `john jane` | обязательно | several words, any order (только клиенты) | John Smith <john.smith@acme.com> | [req] AND across fields: John Smith, 'Referred by Jane Doe' |
| D09 | `von der heide anna` | обязательно | several words, any order (только клиенты) | Anna-Maria von der Heide <am.vdheide@t-online.de> | [req] several words, any order |
| D10 | `tanaka kenji` | ожидаемо | several words, any order (только клиенты) | Ｋｅｎｊｉ Tanaka <kenji.tanaka@example.jp> | [norm] stored first name is full-width |
| D11 | `nguyen thi huong` | ожидаемо | several words, any order (только клиенты) | Hương Nguyễn Thị <huong.nt@fpt.vn> | [norm] several words, any order |
| D12 | `tabbed line two one` | обязательно | several words, any order (только клиенты) | Sam Taylor <sam+wealth@proton.me> | [req] description contains newline and tab |
| D13 | `jane smith` | обязательно | several words, any order (только клиенты) | John Smith <john.smith@acme.com> | [req] AND across fields; surprising for a human |
| E01 | `john doe neviswealth` | обязательно | name + company (только клиенты) | John Doe <john.doe@neviswealth.com> | [req] name + company |
| E02 | `doe neviswealth` | обязательно | name + company (только клиенты) | John Doe <john.doe@neviswealth.com> | [req] name + company |
| E03 | `neviswealth mary` | обязательно | name + company (только клиенты) | Mary Major <M.Major@NEVISWEALTH.COM> | [req] name + company |
| E04 | `smith outlook` | обязательно | name + company (только клиенты) | Zoë Smith-Jones <zoe_sj@outlook.com> | [req] name + company |
| E05 | `picard starfleet` | обязательно | name + company (только клиенты) | Jean-Luc Picard <jl.picard@starfleet.org> | [req] name + company |
| E06 | `john acme` | обязательно | name + company (только клиенты) | Mike Johnson <mike.j@acme.com>; John Smith <john.smith@acme.com><br>первым: John Smith <john.smith@acme.com> | [req] 'john' is a prefix of Johnson |
| E07 | `smith yahoo` | обязательно | name + company (только клиенты) | John Smith <jsmith1975@yahoo.com> | [req] name + company |
| F01 | `smith-jones` | обязательно | hyphens and apostrophes (только клиенты) | Zoë Smith-Jones <zoe_sj@outlook.com> | [req] hyphens and apostrophes |
| F02 | `smith jones` | обязательно | hyphens and apostrophes (только клиенты) | Bob Jones <bob@smithfield.com>; Zoë Smith-Jones <zoe_sj@outlook.com><br>первым: Zoë Smith-Jones <zoe_sj@outlook.com> | [req] bob = Bob Jones @smithfield.com |
| F03 | `smithjones` | желательно | hyphens and apostrophes (только клиенты) | Zoë Smith-Jones <zoe_sj@outlook.com><br>прочие результаты не оцениваются | [nice] hyphens and apostrophes |
| F04 | `o'brien` | обязательно | hyphens and apostrophes (только клиенты) | Séverine O'Brien-Müller <severine.obrien@example.co.uk> | [req] hyphens and apostrophes |
| F05 | `obrien` | обязательно | hyphens and apostrophes (только клиенты) | Séverine O'Brien-Müller <severine.obrien@example.co.uk> | [req] substring of the e-mail local part |
| F06 | `o'connor` | ожидаемо | hyphens and apostrophes (только клиенты) | Siobhán O’Connor <siobhan@greenfield.ie> | [norm] stored with U+2019 |
| F07 | `oconnor` | желательно | hyphens and apostrophes (только клиенты) | Siobhán O’Connor <siobhan@greenfield.ie><br>прочие результаты не оцениваются | [nice] hyphens and apostrophes |
| F08 | `O’Brien` | ожидаемо | hyphens and apostrophes (только клиенты) | Séverine O'Brien-Müller <severine.obrien@example.co.uk> | [norm] query with U+2019, stored ASCII |
| F09 | `jean-luc` | обязательно | hyphens and apostrophes (только клиенты) | Jean-Luc Picard <jl.picard@starfleet.org> | [req] hyphens and apostrophes |
| F10 | `jean luc` | обязательно | hyphens and apostrophes (только клиенты) | Jean-Luc Picard <jl.picard@starfleet.org> | [req] hyphens and apostrophes |
| F11 | `jeanluc` | желательно | hyphens and apostrophes (только клиенты) | Jean-Luc Picard <jl.picard@starfleet.org><br>прочие результаты не оцениваются | [nice] hyphens and apostrophes |
| F12 | `anna maria` | обязательно | hyphens and apostrophes (только клиенты) | Anna-Maria von der Heide <am.vdheide@t-online.de> | [req] hyphens and apostrophes |
| F13 | `d'angelo` | ожидаемо | hyphens and apostrophes (только клиенты) | D’Angelo McDonald <dm@mcd-holdings.com> | [norm] stored with U+2019 |
| F14 | `anne-sophie` | ожидаемо | hyphens and apostrophes (только клиенты) | Anne–Sophie Lefèvre <as.lefevre@laposte.net> | [norm] stored with an en dash |
| F15 | `mcdonald` | обязательно | hyphens and apostrophes (только клиенты) | D’Angelo McDonald <dm@mcd-holdings.com> | [req] hyphens and apostrophes |
| G01 | `jose` | ожидаемо | diacritics (только клиенты) | José Ángel García Márquez <jgarcia@santander.es> | [norm] diacritics |
| G02 | `JOSÉ ÁNGEL` | ожидаемо | diacritics (только клиенты) | José Ángel García Márquez <jgarcia@santander.es> | [norm] diacritics |
| G03 | `severine` | ожидаемо | diacritics (только клиенты) | Séverine O'Brien-Müller <severine.obrien@example.co.uk> | [norm] diacritics |
| G04 | `zoe` | ожидаемо | diacritics (только клиенты) | Zoë Smith-Jones <zoe_sj@outlook.com> | [norm] diacritics |
| G05 | `zoë` | ожидаемо | diacritics (только клиенты) | Zoë Smith-Jones <zoe_sj@outlook.com> | [norm] diacritics |
| G06 | `muller` | ожидаемо | diacritics (только клиенты) | Séverine O'Brien-Müller <severine.obrien@example.co.uk> | [norm] diacritics |
| G07 | `mueller` | желательно | diacritics (только клиенты) | Séverine O'Brien-Müller <severine.obrien@example.co.uk><br>прочие результаты не оцениваются | [nice] German transliteration ue |
| G08 | `lukasz wojcik` | ожидаемо | diacritics (только клиенты) | Łukasz Wójcik <lukasz.w@wp.pl> | [norm] diacritics |
| G09 | `odegard` | ожидаемо | diacritics (только клиенты) | Bjørn Ødegård <bjorn@fjordinvest.no> | [norm] diacritics |
| G10 | `bjorn` | ожидаемо | diacritics (только клиенты) | Bjørn Ødegård <bjorn@fjordinvest.no> | [norm] diacritics |
| G11 | `bjørn ødegård` | ожидаемо | diacritics (только клиенты) | Bjørn Ødegård <bjorn@fjordinvest.no> | [norm] diacritics |
| G12 | `strasse` | ожидаемо | diacritics (только клиенты) | Bjørn Ødegård <bjorn@fjordinvest.no> | [norm] diacritics |
| G13 | `weissensee` | ожидаемо | diacritics (только клиенты) | Bjørn Ødegård <bjorn@fjordinvest.no> | [norm] diacritics |
| G14 | `aether` | ожидаемо | diacritics (только клиенты) | Bjørn Ødegård <bjorn@fjordinvest.no> | [norm] diacritics |
| G15 | `yildirim` | ожидаемо | diacritics (только клиенты) | Mehmet Yıldırım <mehmet.y@turkcell.com.tr> | [norm] diacritics |
| G16 | `YILDIRIM` | ожидаемо | diacritics (только клиенты) | Mehmet Yıldırım <mehmet.y@turkcell.com.tr> | [norm] diacritics |
| G17 | `istanbul` | ожидаемо | diacritics (только клиенты) | Mehmet Yıldırım <mehmet.y@turkcell.com.tr> | [norm] diacritics |
| G18 | `İSTANBUL` | ожидаемо | diacritics (только клиенты) | Mehmet Yıldırım <mehmet.y@turkcell.com.tr> | [norm] diacritics |
| G19 | `ibrahim celik` | ожидаемо | diacritics (только клиенты) | İbrahim Çelik <ibrahim.celik@koc.com.tr> | [norm] diacritics |
| G20 | `IBRAHIM` | ожидаемо | diacritics (только клиенты) | İbrahim Çelik <ibrahim.celik@koc.com.tr> | [norm] diacritics |
| G21 | `gross` | ожидаемо | diacritics (только клиенты) | Jürgen Groß <j.gross@web.de> | [norm] diacritics |
| G22 | `GROSS` | ожидаемо | diacritics (только клиенты) | Jürgen Groß <j.gross@web.de> | [norm] diacritics |
| G23 | `groß` | ожидаемо | diacritics (только клиенты) | Jürgen Groß <j.gross@web.de> | [norm] diacritics |
| G24 | `GROẞ` | ожидаемо | diacritics (только клиенты) | Jürgen Groß <j.gross@web.de> | [norm] capital sharp s U+1E9E |
| G25 | `José` | ожидаемо | diacritics (только клиенты) | José Ángel García Márquez <jgarcia@santander.es> | [norm] NFD input |
| G26 | `emile zola` | ожидаемо | diacritics (только клиенты) | ÉMILE ZOLA <EMILE.ZOLA@EXAMPLE.FR> | [norm] diacritics |
| G27 | `émile` | ожидаемо | diacritics (только клиенты) | ÉMILE ZOLA <EMILE.ZOLA@EXAMPLE.FR> | [norm] diacritics |
| G28 | `munchen` | ожидаемо | diacritics (только клиенты) | Anna-Maria von der Heide <am.vdheide@t-online.de> | [norm] diacritics |
| G29 | `cafe zurich` | ожидаемо | diacritics (только клиенты) | Séverine O'Brien-Müller <severine.obrien@example.co.uk> | [norm] diacritics |
| G30 | `lefevre` | ожидаемо | diacritics (только клиенты) | Anne–Sophie Lefèvre <as.lefevre@laposte.net> | [norm] diacritics |
| G31 | `dupont` | ожидаемо | diacritics (только клиенты) | Marie Claire Dupont <mc.dupont@orange.fr>; Séverine O'Brien-Müller <severine.obrien@example.co.uk> | [norm] diacritics |
| G32 | `siobhan` | ожидаемо | diacritics (только клиенты) | Siobhán O’Connor <siobhan@greenfield.ie> | [norm] NULL description + diacritic |
| H01 | `смирнов` | обязательно | non-Latin scripts (только клиенты) | Алексей Смирнов <a.smirnov@yandex.ru> | [req] non-Latin scripts |
| H02 | `СМИРНОВ` | ожидаемо | non-Latin scripts (только клиенты) | Алексей Смирнов <a.smirnov@yandex.ru> | [norm] non-Latin scripts |
| H03 | `алексей смирнов` | обязательно | non-Latin scripts (только клиенты) | Алексей Смирнов <a.smirnov@yandex.ru> | [req] non-Latin scripts |
| H04 | `облигац` | обязательно | non-Latin scripts (только клиенты) | Алексей Смирнов <a.smirnov@yandex.ru> | [req] non-Latin scripts |
| H05 | `алена королева` | ожидаемо | non-Latin scripts (только клиенты) | Алёна Королёва <alena.k@mail.ru> | [norm] e for yo |
| H06 | `Алёна` | обязательно | non-Latin scripts (только клиенты) | Алёна Королёва <alena.k@mail.ru> | [req] non-Latin scripts |
| H07 | `王` | обязательно | non-Latin scripts (только клиенты) | 伟 王 <wang.wei@example.cn> | [req] non-Latin scripts |
| H08 | `王伟` | желательно | non-Latin scripts (только клиенты) | 伟 王 <wang.wei@example.cn> | [nice] natural CJK order: family name first, no space |
| H09 | `伟 王` | обязательно | non-Latin scripts (только клиенты) | 伟 王 <wang.wei@example.cn> | [req] non-Latin scripts |
| H10 | `高净值` | обязательно | non-Latin scripts (только клиенты) | 伟 王 <wang.wei@example.cn> | [req] non-Latin scripts |
| H11 | `债券` | обязательно | non-Latin scripts (только клиенты) | 伟 王 <wang.wei@example.cn> | [req] non-Latin scripts |
| H12 | `παπαδοπουλος` | ожидаемо | non-Latin scripts (только клиенты) | Παναγιώτης Παπαδόπουλος <p.papadopoulos@otenet.gr> | [norm] non-Latin scripts |
| H13 | `ΠΑΠΑΔΟΠΟΥΛΟΣ` | ожидаемо | non-Latin scripts (только клиенты) | Παναγιώτης Παπαδόπουλος <p.papadopoulos@otenet.gr> | [norm] upper case: final sigma |
| H14 | `Παπαδόπουλος` | обязательно | non-Latin scripts (только клиенты) | Παναγιώτης Παπαδόπουλος <p.papadopoulos@otenet.gr> | [req] non-Latin scripts |
| H15 | `محمد` | обязательно | non-Latin scripts (только клиенты) | محمد الفاسي <m.alfassi@example.ma> | [req] non-Latin scripts |
| H16 | `مُحَمَّد` | желательно | non-Latin scripts (только клиенты) | محمد الفاسي <m.alfassi@example.ma> | [nice] Arabic with harakat |
| H17 | `כהן` | обязательно | non-Latin scripts (только клиенты) | יעל כהן <yael.cohen@example.co.il> | [req] non-Latin scripts |
| H18 | `ｋｅｎｊｉ` | ожидаемо | non-Latin scripts (только клиенты) | Ｋｅｎｊｉ Tanaka <kenji.tanaka@example.jp> | [norm] full-width query |
| H19 | `kenji` | ожидаемо | non-Latin scripts (только клиенты) | Ｋｅｎｊｉ Tanaka <kenji.tanaka@example.jp> | [norm] non-Latin scripts |
| H20 | `finance` | ожидаемо | non-Latin scripts (только клиенты) | Ｋｅｎｊｉ Tanaka <kenji.tanaka@example.jp> | [norm] stored with the fi ligature |
| H21 | `東京` | обязательно | non-Latin scripts (только клиенты) | Ｋｅｎｊｉ Tanaka <kenji.tanaka@example.jp> | [req] non-Latin scripts |
| H22 | `smirnov` | обязательно | non-Latin scripts (только клиенты) | Алексей Смирнов <a.smirnov@yandex.ru> | [req] Latin, matches the e-mail |
| H23 | `٢٠١٥` | обязательно | non-Latin scripts (только клиенты) | محمد الفاسي <m.alfassi@example.ma> | [req] non-Latin scripts |
| I01 | `🚀` | обязательно | emoji (только клиенты) | Renée Leclerc <renee@leclerc.fr> | [req] emoji |
| I02 | `👨‍👩‍👧` | обязательно | emoji (только клиенты) | Renée Leclerc <renee@leclerc.fr> | [req] ZWJ sequence |
| I03 | `😀` | обязательно | emoji (только клиенты) | Renée Leclerc <renee@leclerc.fr> | [req] emoji |
| I04 | `🚀 startups` | обязательно | emoji (только клиенты) | Renée Leclerc <renee@leclerc.fr> | [req] emoji |
| I05 | `❤` | обязательно | emoji (только клиенты) | Val Entine <val@hearts.io> | [req] query without the variation selector |
| I06 | `❤️` | обязательно | emoji (только клиенты) | Val Entine <val@hearts.io> | [req] emoji |
| I07 | `👩` | обязательно | emoji (только клиенты) | Renée Leclerc <renee@leclerc.fr> | [req] component of the ZWJ sequence |
| I08 | `🙂` | обязательно | emoji (только клиенты) | пустой список | [req] emoji |
| J01 | `a` | ожидаемо | one and two characters (только клиенты) | A B <ab@c.de>; Jane Doe <jane@doe-family.org>; Mary Major <M.Major@NEVISWEALTH.COM><br>первым: A B <ab@c.de><br>прочие результаты не оцениваются | [rank] client 'A B': whole-word name hit |
| J02 | `li` | ожидаемо | one and two characters (только клиенты) | Robert Tables <bobby@xkcd.com>; İbrahim Çelik <ibrahim.celik@koc.com.tr>; John Doe <john.doe@neviswealth.com>; Li Ng <li.ng@hk-capital.hk>; Mary Major <M.Major@NEVISWEALTH.COM>; Olivia Stone <olivia@stonecap.com>; Sam Taylor <sam+wealth@proton.me><br>первым: Li Ng <li.ng@hk-capital.hk><br>прочие результаты не оцениваются | [rank] one and two characters |
| J03 | `ng` | ожидаемо | one and two characters (только клиенты) | D’Angelo McDonald <dm@mcd-holdings.com>; John Doe <john.doe@neviswealth.com>; Jonathan Doering <jon.doering@gmail.com>; José Ángel García Márquez <jgarcia@santander.es>; Li Ng <li.ng@hk-capital.hk>; Hương Nguyễn Thị <huong.nt@fpt.vn><br>первым: Li Ng <li.ng@hk-capital.hk><br>прочие результаты не оцениваются | [rank] one and two characters |
| J04 | `ab` | ожидаемо | one and two characters (только клиенты) | A B <ab@c.de>; Robert Tables <bobby@xkcd.com>; Sam Taylor <sam+wealth@proton.me><br>первым: A B <ab@c.de><br>прочие результаты не оцениваются | [rank] one and two characters |
| J05 | `é` | ожидаемо | one and two characters (только клиенты) | John Doe <john.doe@neviswealth.com>; José Ángel García Márquez <jgarcia@santander.es>; Séverine O'Brien-Müller <severine.obrien@example.co.uk><br>прочие результаты не оцениваются | [robust] normalises to 'e' |
| J06 | `?` | обязательно | one and two characters (только клиенты) | пустой список | [req] one and two characters |
| J07 | `x` | обязательно | one and two characters (только клиенты) | Robert Tables <bobby@xkcd.com><br>прочие результаты не оцениваются | [req] one and two characters |
| J08 | `b` | ожидаемо | one and two characters (только клиенты) | A B <ab@c.de><br>первым: A B <ab@c.de><br>прочие результаты не оцениваются | [rank] one and two characters |
| J09 | `ß` | ожидаемо | one and two characters (только клиенты) | Bjørn Ødegård <bjorn@fjordinvest.no>; Jürgen Groß <j.gross@web.de>; محمد الفاسي <m.alfassi@example.ma> | [norm] normalises to 'ss' (alfassi) |
| J10 | `li ng` | обязательно | one and two characters (только клиенты) | Anna-Maria von der Heide <am.vdheide@t-online.de>; John Doe <john.doe@neviswealth.com>; José Ángel García Márquez <jgarcia@santander.es>; Li Ng <li.ng@hk-capital.hk><br>первым: Li Ng <li.ng@hk-capital.hk> | [req] 3 of the 4 hits are infix noise (client+long-term, t-online+stiftung, portfolio+angel) |
| K01 | `%` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | José Ángel García Márquez <jgarcia@santander.es>; Percy Cent <percy@100percent.io> | [req] metacharacters, quotes, SQL-looking input |
| K02 | `100%` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | José Ángel García Márquez <jgarcia@santander.es>; Percy Cent <percy@100percent.io> | [req] metacharacters, quotes, SQL-looking input |
| K03 | `100% equ` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | José Ángel García Márquez <jgarcia@santander.es>; Percy Cent <percy@100percent.io> | [req] metacharacters, quotes, SQL-looking input |
| K04 | `_` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | Percy Cent <percy@100percent.io>; Zoë Smith-Jones <zoe_sj@outlook.com> | [req] metacharacters, quotes, SQL-looking input |
| K05 | `0_bonds` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | Percy Cent <percy@100percent.io> | [req] metacharacters, quotes, SQL-looking input |
| K06 | `0xbonds` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [req] _ must not be a wildcard |
| K07 | `zoe.sj` | желательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [debatable] wrong separator |
| K08 | `\` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | Percy Cent <percy@100percent.io> | [req] metacharacters, quotes, SQL-looking input |
| K09 | `C:\Users` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | Percy Cent <percy@100percent.io> | [req] metacharacters, quotes, SQL-looking input |
| K10 | `\\` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [req] two backslashes; stored text has single ones |
| K11 | `c:\users\percy` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | Percy Cent <percy@100percent.io> | [req] metacharacters, quotes, SQL-looking input |
| K12 | `%%` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [req] metacharacters, quotes, SQL-looking input |
| K13 | `_%` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [req] metacharacters, quotes, SQL-looking input |
| K14 | `%_` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [req] metacharacters, quotes, SQL-looking input |
| K15 | `'` | ожидаемо | metacharacters, quotes, SQL-looking input (только клиенты) | Robert Tables <bobby@xkcd.com>; D’Angelo McDonald <dm@mcd-holdings.com>; ÉMILE ZOLA <EMILE.ZOLA@EXAMPLE.FR>; Mehmet Yıldırım <mehmet.y@turkcell.com.tr>; Séverine O'Brien-Müller <severine.obrien@example.co.uk>; Siobhán O’Connor <siobhan@greenfield.ie> | [norm] metacharacters, quotes, SQL-looking input |
| K16 | `"` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [req] metacharacters, quotes, SQL-looking input |
| K17 | `'; DROP TABLE clients;--` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | Robert Tables <bobby@xkcd.com> | [req] metacharacters, quotes, SQL-looking input |
| K18 | `Robert'); DROP TABLE clients;--` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | Robert Tables <bobby@xkcd.com> | [req] metacharacters, quotes, SQL-looking input |
| K19 | `' OR '1'='1` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [req] injection probe must not return unrelated clients |
| K20 | `1; SELECT pg_sleep(10)` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [req] metacharacters, quotes, SQL-looking input |
| K21 | `john%` | желательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [debatable] user expects a wildcard; literal says nothing |
| K22 | `j_hn` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [req] metacharacters, quotes, SQL-looking input |
| K23 | `joh*` | желательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [debatable] metacharacters, quotes, SQL-looking input |
| K24 | `.*` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [req] metacharacters, quotes, SQL-looking input |
| K25 | `[a-z]+` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [req] metacharacters, quotes, SQL-looking input |
| K26 | `(john\|jane)` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [req] metacharacters, quotes, SQL-looking input |
| K27 | `john' --` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [req] metacharacters, quotes, SQL-looking input |
| K28 | `\%` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [req] metacharacters, quotes, SQL-looking input |
| K29 | `%' OR 1=1 --` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [req] metacharacters, quotes, SQL-looking input |
| K30 | `<script>alert(1)</script>` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [req] metacharacters, quotes, SQL-looking input |
| K31 | `NULL` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | Null None <null@example.com> | [req] SQL NULL descriptions must not match the word |
| K32 | `null none` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | Null None <null@example.com> | [req] metacharacters, quotes, SQL-looking input |
| K33 | `--` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | Robert Tables <bobby@xkcd.com> | [req] metacharacters, quotes, SQL-looking input |
| K34 | `;` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [req] separator only |
| K35 | `,;, ;` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [req] separators only |
| K36 | `{{7*7}} ${jndi:ldap://x}` | обязательно | metacharacters, quotes, SQL-looking input (только клиенты) | пустой список | [req] metacharacters, quotes, SQL-looking input |
| L03 | `John\r\nDoe` | обязательно | control and invisible characters (только клиенты) | John Doe <john.doe@neviswealth.com><br>первым: John Doe <john.doe@neviswealth.com><br>не должно быть: Jane Doe <jane@doe-family.org><br>прочие результаты не оцениваются | [req] control and invisible characters |
| L04 | `john\x0bdoe\x0c` | обязательно | control and invisible characters (только клиенты) | John Doe <john.doe@neviswealth.com><br>первым: John Doe <john.doe@neviswealth.com><br>не должно быть: Jane Doe <jane@doe-family.org><br>прочие результаты не оцениваются | [req] VT and FF |
| L05 | `john\x07doe` | желательно | control and invisible characters (только клиенты) | пустой список | [debatable] BEL glued between the words |
| L06 | `NevisWealth\u200b` | желательно | control and invisible characters (только клиенты) | John Doe <john.doe@neviswealth.com>; Mary Major <M.Major@NEVISWEALTH.COM>; Peter Parker <pparker@dailybugle.com> | [nice] trailing zero-width space from copy-paste |
| L07 | `\ufeffNevisWealth` | желательно | control and invisible characters (только клиенты) | John Doe <john.doe@neviswealth.com>; Mary Major <M.Major@NEVISWEALTH.COM>; Peter Parker <pparker@dailybugle.com> | [nice] leading BOM |
| L08 | `Nevis\xadWealth` | желательно | control and invisible characters (только клиенты) | John Doe <john.doe@neviswealth.com>; Mary Major <M.Major@NEVISWEALTH.COM>; Peter Parker <pparker@dailybugle.com> | [nice] soft hyphen inside |
| L09 | `zerowidth` | желательно | control and invisible characters (только клиенты) | Zero​Width Joiner <zw@invisible.dev> | [nice] stored name contains U+200B |
| L10 | `softhyphen` | желательно | control and invisible characters (только клиенты) | Zero​Width Joiner <zw@invisible.dev> | [nice] stored text contains U+00AD |
| L11 | `‮NevisWealth‬` | желательно | control and invisible characters (только клиенты) | John Doe <john.doe@neviswealth.com>; Mary Major <M.Major@NEVISWEALTH.COM>; Peter Parker <pparker@dailybugle.com> | [nice] bidi override characters |
| L12 | `john doe` | желательно | control and invisible characters (только клиенты) | John Doe <john.doe@neviswealth.com><br>первым: John Doe <john.doe@neviswealth.com><br>прочие результаты не оцениваются | [nice] LINE SEPARATOR |
| L13 | `john　doe` | ожидаемо | control and invisible characters (только клиенты) | John Doe <john.doe@neviswealth.com><br>первым: John Doe <john.doe@neviswealth.com><br>не должно быть: Jane Doe <jane@doe-family.org><br>прочие результаты не оцениваются | [norm] ideographic space |
| L14 | `\x1f` | обязательно | control and invisible characters (только клиенты) | пустой список | [req] control and invisible characters |
| L15 | `` | обязательно | control and invisible characters (только клиенты) | пустой список | [req] control and invisible characters |
| M01 | `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa…` | ожидаемо | long queries (только клиенты) | пустой список | [robust] long queries |
| M02 | `john doe john doe john doe john doe john doe john doe john doe john doe john …` | ожидаемо | long queries (только клиенты) | John Doe <john.doe@neviswealth.com><br>первым: John Doe <john.doe@neviswealth.com><br>прочие результаты не оцениваются | [robust] long queries |
| M03 | `x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x…` | ожидаемо | long queries (только клиенты) | пустой список | [robust] no client contains both 'x' and 'neviswealth'; left($1,100) drops the real token |
| M04 | `neviswealthxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx…` | ожидаемо | long queries (только клиенты) | пустой список | [robust] long queries |
| M05 | `john doe john doe john doe john doe john doe john doe john doe john doe john …` | обязательно | long queries (только клиенты) | пустой список | [req] 106 characters (inside D8's 200 limit): the token after position 100 matches nothing |
| M06 | `w000qx w001qx w002qx w003qx w004qx w005qx w006qx w007qx w008qx w009qx w010qx …` | ожидаемо | long queries (только клиенты) | пустой список | [robust] 5,000 chars, 700 distinct tokens |
| N01 | `jane doe` | обязательно | NULL / empty description (только клиенты) | Jane Doe <jane@doe-family.org><br>первым: Jane Doe <jane@doe-family.org><br>Jane Doe <jane@doe-family.org> выше, чем John Smith <john.smith@acme.com><br>прочие результаты не оцениваются | [req] NULL / empty description |
| N02 | `marie dupont` | обязательно | NULL / empty description (только клиенты) | Marie Claire Dupont <mc.dupont@orange.fr> | [req] empty-string description |
| N03 | `li.ng` | обязательно | NULL / empty description (только клиенты) | Li Ng <li.ng@hk-capital.hk> | [req] NULL / empty description |
| O01 | `qwertyuiop` | обязательно | must return nothing (только клиенты) | пустой список | [req] must return nothing |
| O02 | `xyzzy plugh` | обязательно | must return nothing (только клиенты) | пустой список | [req] must return nothing |
| O03 | `john xyzzy` | обязательно | must return nothing (только клиенты) | пустой список | [req] must return nothing |
| O04 | `neviswealth.org` | желательно | must return nothing (только клиенты) | пустой список | [debatable] wrong TLD |
| O05 | `john.doe@gmail.com` | обязательно | must return nothing (только клиенты) | пустой список | [req] no such address: identifier lookups must be precise |
| O06 | `12345` | обязательно | must return nothing (только клиенты) | пустой список | [req] must return nothing |
| O07 | `maria gonzalez` | обязательно | must return nothing (только клиенты) | пустой список | [req] must return nothing |
| O08 | `peter smith` | обязательно | must return nothing (только клиенты) | пустой список | [req] must return nothing |
| O09 | `jane@doe-family.com` | обязательно | must return nothing (только клиенты) | пустой список | [req] stored address ends in .org |
| O10 | `doejohn` | желательно | must return nothing (только клиенты) | пустой список | [debatable] must return nothing |
| O11 | `zzzzzzzz` | обязательно | must return nothing (только клиенты) | пустой список | [req] must return nothing |
| O12 | `!!!!!!` | обязательно | must return nothing (только клиенты) | пустой список | [req] must return nothing |
| O13 | `-----` | обязательно | must return nothing (только клиенты) | пустой список | [req] must return nothing |
| O14 | `quantolivia` | желательно | must return nothing (только клиенты) | пустой список | [design] appears only in social_links |
| O15 | `linkedin` | желательно | must return nothing (только клиенты) | пустой список | [design] appears only in social_links |
| O16 | `wealthy nevis doe` | желательно | must return nothing (только клиенты) | пустой список | [debatable] no client has all three |
| O17 | `james brown` | обязательно | must return nothing (только клиенты) | пустой список | [req] must return nothing |
| O18 | `wealth management firm` | обязательно | must return nothing (только клиенты) | пустой список | [req] must return nothing |
| O19 | `barack obama` | обязательно | must return nothing (только клиенты) | пустой список | [req] must return nothing |
| O20 | `john.smith@gmail.com` | обязательно | must return nothing (только клиенты) | пустой список | [req] john.smith@acme.com exists, this one does not |
| O21 | `sustainable investing` | обязательно | must return nothing (только клиенты) | пустой список | [req] must return nothing |
| O22 | `asdfghjkl` | обязательно | must return nothing (только клиенты) | пустой список | [req] must return nothing |
| O23 | `neviswealth llc` | желательно | must return nothing (только клиенты) | пустой список | [debatable] must return nothing |
| O24 | `wealthnevis` | обязательно | must return nothing (только клиенты) | пустой список | [req] must return nothing |
| O25 | `doe.john` | желательно | must return nothing (только клиенты) | пустой список | [debatable] must return nothing |
| O26 | `investment portfolio review` | обязательно | must return nothing (только клиенты) | пустой список | [req] must return nothing |
| O27 | `2024-01-15` | обязательно | must return nothing (только клиенты) | пустой список | [req] must return nothing |
| O28 | `+1 555 0100` | обязательно | must return nothing (только клиенты) | пустой список | [req] must return nothing |
| P01 | `jhon doe` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: John Doe <john.doe@neviswealth.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P02 | `neviswelth` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: John Doe <john.doe@neviswealth.com>; Mary Major <M.Major@NEVISWEALTH.COM>; Peter Parker <pparker@dailybugle.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P03 | `nevisweath` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: John Doe <john.doe@neviswealth.com>; Mary Major <M.Major@NEVISWEALTH.COM>; Peter Parker <pparker@dailybugle.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P04 | `newiswealth` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: John Doe <john.doe@neviswealth.com>; Mary Major <M.Major@NEVISWEALTH.COM>; Peter Parker <pparker@dailybugle.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P05 | `neviswaelth` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: John Doe <john.doe@neviswealth.com>; Mary Major <M.Major@NEVISWEALTH.COM>; Peter Parker <pparker@dailybugle.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P06 | `nevis welth` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: John Doe <john.doe@neviswealth.com>; Mary Major <M.Major@NEVISWEALTH.COM>; Peter Parker <pparker@dailybugle.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P07 | `severine obrian` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Séverine O'Brien-Müller <severine.obrien@example.co.uk><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P08 | `picrad` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Jean-Luc Picard <jl.picard@starfleet.org><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P09 | `pickard` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Jean-Luc Picard <jl.picard@starfleet.org><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P10 | `jean-luc piccard` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Jean-Luc Picard <jl.picard@starfleet.org><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P11 | `gracia` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: José Ángel García Márquez <jgarcia@santander.es><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P12 | `marques` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: José Ángel García Márquez <jgarcia@santander.es><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P13 | `smiht` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: John Smith <john.smith@acme.com>; John Smith <jsmith1975@yahoo.com>; Zoë Smith-Jones <zoe_sj@outlook.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P14 | `smyth` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: John Smith <john.smith@acme.com>; John Smith <jsmith1975@yahoo.com>; Zoë Smith-Jones <zoe_sj@outlook.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P15 | `jonh smith` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: John Smith <john.smith@acme.com>; John Smith <jsmith1975@yahoo.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P16 | `papadopulos` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Παναγιώτης Παπαδόπουλος <p.papadopoulos@otenet.gr><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P17 | `smirnof` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Алексей Смирнов <a.smirnov@yandex.ru><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P18 | `смирнв` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Алексей Смирнов <a.smirnov@yandex.ru><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P19 | `смернов` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Алексей Смирнов <a.smirnov@yandex.ru><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P20 | `yildrim` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Mehmet Yıldırım <mehmet.y@turkcell.com.tr><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P21 | `wojcick` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Łukasz Wójcik <lukasz.w@wp.pl><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P22 | `odegaard` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Bjørn Ødegård <bjorn@fjordinvest.no><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P23 | `tanka kenji` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Ｋｅｎｊｉ Tanaka <kenji.tanaka@example.jp><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P24 | `kenij tanaka` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Ｋｅｎｊｉ Tanaka <kenji.tanaka@example.jp><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P25 | `jonathn doering` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Jonathan Doering <jon.doering@gmail.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P26 | `jonathan doring` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Jonathan Doering <jon.doering@gmail.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P27 | `doreing` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Jonathan Doering <jon.doering@gmail.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P28 | `quaterly reviews` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: John Doe <john.doe@neviswealth.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P29 | `retired enginer` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Jonathan Doering <jon.doering@gmail.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P30 | `complience` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Mary Major <M.Major@NEVISWEALTH.COM><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P31 | `john.doe@neviswealth.con` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: John Doe <john.doe@neviswealth.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P32 | `jon.doering@gmial.com` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Jonathan Doering <jon.doering@gmail.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P33 | `zoe-sj` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Zoë Smith-Jones <zoe_sj@outlook.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P34 | `jhon` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: John Doe <john.doe@neviswealth.com>; John Smith <john.smith@acme.com>; John Smith <jsmith1975@yahoo.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P35 | `doee` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Jane Doe <jane@doe-family.org>; John Doe <john.doe@neviswealth.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P36 | `mery major` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Mary Major <M.Major@NEVISWEALTH.COM><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P37 | `marry major` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Mary Major <M.Major@NEVISWEALTH.COM><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P38 | `leclerk` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Renée Leclerc <renee@leclerc.fr><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P39 | `tailor` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Sam Taylor <sam+wealth@proton.me><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P40 | `mcdonnald` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: D’Angelo McDonald <dm@mcd-holdings.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P41 | `lefebvre` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Anne–Sophie Lefèvre <as.lefevre@laposte.net><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P42 | `anna-maria von der hiede` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Anna-Maria von der Heide <am.vdheide@t-online.de><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P43 | `dupond` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Marie Claire Dupont <mc.dupont@orange.fr>; Séverine O'Brien-Müller <severine.obrien@example.co.uk><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P44 | `olivia stoun` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Olivia Stone <olivia@stonecap.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P45 | `starfleat` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Jean-Luc Picard <jl.picard@starfleet.org><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| P46 | `micheal johnson` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Mike Johnson <mike.j@acme.com><br>прочие результаты не оцениваются | [nice] wrong first name variant; stored Mike |
| P47 | `jane do` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Jane Doe <jane@doe-family.org><br>прочие результаты не оцениваются | [nice] truncated word: actually a substring -> strict tier |
| P48 | `bobby tabels` | желательно | typos (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Robert Tables <bobby@xkcd.com><br>прочие результаты не оцениваются | [nice] typos (target within the first 5 rows) |
| R01 | `Dr John Doe` | желательно | extra words (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: John Doe <john.doe@neviswealth.com><br>прочие результаты не оцениваются | [nice] extra words (target within the first 5 rows) |
| R02 | `Mr. John Doe` | желательно | extra words (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: John Doe <john.doe@neviswealth.com><br>прочие результаты не оцениваются | [nice] extra words (target within the first 5 rows) |
| R03 | `john doe london` | желательно | extra words (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: John Doe <john.doe@neviswealth.com><br>прочие результаты не оцениваются | [nice] extra words (target within the first 5 rows) |
| R04 | `john doe neviswealth ltd` | желательно | extra words (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: John Doe <john.doe@neviswealth.com><br>прочие результаты не оцениваются | [nice] extra words (target within the first 5 rows) |
| R05 | `who is interested in ESG` | желательно | extra words (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Jonathan Doering <jon.doering@gmail.com><br>прочие результаты не оцениваются | [nice] extra words (target within the first 5 rows) |
| R06 | `find jane doe` | желательно | extra words (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Jane Doe <jane@doe-family.org><br>прочие результаты не оцениваются | [nice] extra words (target within the first 5 rows) |
| R07 | `john michael doe` | желательно | extra words (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: John Doe <john.doe@neviswealth.com><br>прочие результаты не оцениваются | [nice] extra words (target within the first 5 rows) |
| R08 | `mary major from nevis wealth` | желательно | extra words (target within the first 5 rows) (только клиенты) | хотя бы один в первых 5: Mary Major <M.Major@NEVISWEALTH.COM><br>прочие результаты не оцениваются | [nice] extra words (target within the first 5 rows) |
| S01 | `smith` | ожидаемо | ranking and ties (только клиенты) | Bob Jones <bob@smithfield.com>; Mike Johnson <mike.j@acme.com>; John Smith <john.smith@acme.com>; John Smith <jsmith1975@yahoo.com>; Zoë Smith-Jones <zoe_sj@outlook.com><br>John Smith <john.smith@acme.com> выше, чем Bob Jones <bob@smithfield.com><br>John Smith <jsmith1975@yahoo.com> выше, чем Bob Jones <bob@smithfield.com><br>Zoë Smith-Jones <zoe_sj@outlook.com> выше, чем Bob Jones <bob@smithfield.com><br>John Smith <john.smith@acme.com> выше, чем Mike Johnson <mike.j@acme.com><br>Bob Jones <bob@smithfield.com> выше, чем Mike Johnson <mike.j@acme.com><br>прочие результаты не оцениваются | [rank] name, then e-mail, then description |
| S02 | `doe` | ожидаемо | ranking and ties (только клиенты) | John Doe <john.doe@neviswealth.com> выше, чем Jonathan Doering <jon.doering@gmail.com><br>Jane Doe <jane@doe-family.org> выше, чем Jonathan Doering <jon.doering@gmail.com><br>John Doe <john.doe@neviswealth.com> выше, чем John Smith <john.smith@acme.com><br>Jane Doe <jane@doe-family.org> выше, чем John Smith <john.smith@acme.com><br>прочие результаты не оцениваются | [rank] ranking and ties |
| S03 | `john smith` | ожидаемо | ranking and ties (только клиенты) | John Smith <john.smith@acme.com>; John Smith <jsmith1975@yahoo.com><br>первым: John Smith <john.smith@acme.com> или John Smith <jsmith1975@yahoo.com><br>прочие результаты не оцениваются | [rank] two identical names: tie must be stable |
| S04 | `nevis` | ожидаемо | ranking and ties (только клиенты) | John Doe <john.doe@neviswealth.com>; Mary Major <M.Major@NEVISWEALTH.COM>; Nevis Wealthy <nevis.w@gmail.com>; Peter Parker <pparker@dailybugle.com><br>первым: Nevis Wealthy <nevis.w@gmail.com><br>прочие результаты не оцениваются | [rank] whole word in the name first |
| S05 | `jones` | ожидаемо | ranking and ties (только клиенты) | Bob Jones <bob@smithfield.com>; Zoë Smith-Jones <zoe_sj@outlook.com><br>первым: Bob Jones <bob@smithfield.com> или Zoë Smith-Jones <zoe_sj@outlook.com><br>прочие результаты не оцениваются | [rank] ranking and ties |
| S06 | `wealth` | ожидаемо | ranking and ties (только клиенты) | Nevis Wealthy <nevis.w@gmail.com><br>первым: Nevis Wealthy <nevis.w@gmail.com><br>прочие результаты не оцениваются | [rank] only name hit is the prefix of Wealthy |
| S07 | `com` | ожидаемо | ranking and ties (только клиенты) | John Doe <john.doe@neviswealth.com>; Mary Major <M.Major@NEVISWEALTH.COM>; Peter Parker <pparker@dailybugle.com><br>прочие результаты не оцениваются | [rank] common substring |

## Проверки HTTP-контракта

| id | Запрос | Ожидаемый код | Почему |
|---|---|---|---|
| h-L01 | `GET /search ?q=john\x00doe` | 400 или 422 | NUL inside: must be rejected cleanly, not crash with 500 |
| h-L02 | `GET /search ?q=\x00` | 400 или 422 | NUL only: must be rejected cleanly, not crash with 500 |
| h-L16 | `GET /search ?q=\ud83d` | 400 или 422 | lone surrogate: must be rejected cleanly, not crash with 500 |
