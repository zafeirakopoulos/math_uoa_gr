# To do

Regular updates to the site content, and open questions.
Paths are relative to the repository root. Building and deploying are explained in `README.md`.

## Every semester

### February: spring semester begins
- [ ] In `_config.yml`, set `current_semester: spring`.
  The undergraduate page will then list the spring courses and show the winter assignments in the folded section.
- [ ] In `_data/academic_years/<year>.yml`, under `spring:`:
  - [ ] Add `timetable:` (the spring weekly timetable), with the same layout as `winter.timetable`.
  - [ ] Check the `assignments:` against the final version and update `updated:`.
- [ ] In `collections/_courses/`, check the `offered:` mark of each course. A course appears in the spring list only if it has `spring`.
- [ ] Graduate studies, MSc: in `collections/_msc_courses/`, update `semester:` and `instructors:` for the spring courses.

### September: winter semester begins (new academic year)
- [ ] Create `_data/academic_years/<new year>.yml`, e.g. `2027-28.yml`, using the previous year's file as a template:
  - [ ] `dates:`: the year's key dates (semester start and end, exam periods, holidays).
  - [ ] `first_year:`: the first-year timetable (groups, courses, slots).
  - [ ] `winter:` and `spring:`: teaching and exam periods (`teaching`, `exams`), `assignments`, `timetable` and `updated`.
- [ ] In `_config.yml`, set `academic_year: <new year>` and `current_semester: winter`.
- [ ] In `collections/_courses/`, update `offered:` for all courses for the new year.
- [ ] If the study guide changed, update the courses: new or removed courses, `semester`, `order`, `tags`, `required`, and descriptions.
- [ ] In `collections/_programs/proptychiakes.md`, update the year-specific links and labels, e.g. "Ακαδημαϊκό έτος …", the study guide, academic advisors and the September exam schedule.
- [ ] In `collections/_programs/metaptychiakes.md`, update the admission links for the new year and the teaching assignments and timetables.
- [ ] In `collections/_msc_courses/`, update `semester:` and `instructors:`, and add the year's special-topics courses (see below).

### After each exam period
- [ ] Add the new master's theses to `collections/_msc_theses/` and the new PhDs to `collections/_theses/`.
  Supervisors go in `supervisors:` as the person's file name in `collections/_people/`.

## When something happens
- [ ] **News:** each news item in `collections/_news/` gets `audience:`, set to `undergrad`, `grad` and/or `research`. Without it, the item appears only in the general news, and in the left-hand news box only on general pages.
- [ ] **Staff changes:** when someone is promoted, update `rank:` in `collections/_people/<name>.md`. The title comes from `_data/ranks.yml`, and `gender: f` gives the feminine form. When someone retires, set `group: retired` and `rank: Ομότιμος Καθηγητής` if applicable.
- [ ] **Seminars and conferences:** add them to `collections/_seminars/` and `collections/_events/`.

## Open questions

### Content
- [ ] On the Erasmus+/CIVIS page (`pages/spoudes/erasmus-civis.md`), add the department's academic Erasmus coordinator. A placeholder is there now.
- [ ] Four undergraduate courses have no description in the study guide: 463, 563, 595 and 864.
- [ ] Some course codes appear in the assignments but not in the courses: 697 (Αξιοποίηση των Πανεπιστημιακών Μαθηματικών, which has no code in the guide), 873, 874 and 875.
- [ ] Courses 109 and 120 are only for first-year entrants, and 151 only for 1st/2nd-year students. There is no field for this yet.
- [ ] The "(ε)" next to some titles in the assignments (121, 302, 421, 634, 221, 241): what does it mean, and should it be shown?
- [ ] Spring 491, 492 and 493 have no instructor in the source.

### Timetable
- [ ] The year of each course in the winter timetable was inferred from the text colour of the old PDF (blue 1st year, green 2nd, brown 3rd, red 4th). Check `year:` in `winter.timetable.slots`.
- [ ] The Πληροφορική Ι lab on Thursday 13:00–15:00 has a room in the full timetable ("Αίθ. Α") but none in the first-year timetable.

### MSc
- [ ] The MSc course catalogues are older than the 2024 regulation, so they disagree:
  - [ ] Θ34 (Απειροδιάστατες Αναπαραστάσεις) and Ε28 = ΣΕΠ33 (Αριθμητική Βελτιστοποίηση) have no course page.
  - [ ] In the catalogue, ΣΕΠ33–35 are "Ειδικά θέματα". In the regulation they are ΣΕΠ34–36, and ΣΕΠ33 is Αριθμητική Βελτιστοποίηση.
  - [ ] The regulation merges Ε1 and Ε2 into "Ε1-2"; the site still shows two courses.
  - [ ] Ε8 is listed as a core course (as in the catalogue), but the regulation's core is Ε1–Ε7.
- [ ] Special-topics courses (e.g. Θ26.α/β, Θ25.β, ΣΕΠ36 Μηχανική Μάθηση) change every year. Decide whether each gets a course page or is only listed.
- [ ] Some formulas in the Applied and Statistics catalogues were images and are missing from some descriptions.

### Site
- [ ] Course titles and descriptions exist only in Greek. The English pages show them in Greek.
- [ ] Decide on the final address: GitHub Pages under `/math_uoa_gr` for now, or its own domain. For a domain, set `baseurl: ""`.
- [ ] The import scripts in `_migration/tools/` write the old fields (`rank_display`, a single `supervisor`). If they are run again, update them first.
