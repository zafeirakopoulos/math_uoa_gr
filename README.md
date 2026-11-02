# math.uoa.gr — Jekyll site

New website for the Department of Mathematics, National and Kapodistrian University of Athens (ΕΚΠΑ). Its content was migrated from the TYPO3 site at www.math.uoa.gr.

## Build & preview

```sh
bundle install                 # needs ruby-dev / build tools for native gems
bundle exec jekyll serve       # http://localhost:4000
```

If `bundle install` is not possible (e.g. no Ruby headers), use the wrapper. It runs the system Jekyll with a project-local Dart Sass converter from `vendor/gems`:

```sh
bin/jekyll serve
```

Sass is compiled with **Dart Sass** (`jekyll-sass-converter` 3.x), not the deprecated LibSass.

Deployment: `.github/workflows/pages.yml` builds and publishes to GitHub Pages on every push to `main`. For any other host, serve the `_site/` folder.

## Languages (Greek / English): one file per item

Greek is the default language; English lives under `/en/`. **Every item has a single file.** Shared facts sit at the top level, and the text that differs per language goes in an `el:` and an `en:` block:

```yaml
---
key: analysi                 # shared
order: 2
el:
  title: Τομέας Μαθηματικής Ανάλυσης
  lede: Μαθηματική Ανάλυση, Εφαρμοσμένη Ανάλυση, Διαφορικές Εξισώσεις.
en:
  title: Sector of Mathematical Analysis
  lede: Mathematical Analysis, Applied Analysis, Differential Equations.
---
```

- **Body text**: long text goes in `body: |` inside the language block. A body written below the front matter is shared by both languages (used by listing pages that only contain an `{% include %}`).
- **URLs**: a collection's English URL comes from `permalink_en` in `_config.yml`, or from `en.permalink` in the file. Pages set `el.permalink` and `en.permalink`.
- **Missing translations**: with no `en:` block there is no English page, and English listings show the Greek item. Collections marked `always_en: true` (people, events) always get an English page, falling back to the Greek text.
- **How it works**: `_plugins/bilingual.rb` creates the second-language page for each file and gives every item `urls` (for the language switch) and `i18n.el` / `i18n.en` (the localised view used by listings: `item.i18n[lang].title`). It also precomputes the menus (`site.nav.el`, `site.nav.en`).
  Because of this custom plugin, deploy with the included GitHub Actions workflow (or any `jekyll build`). GitHub's "classic" Pages builder does not run custom plugins.
- **Interface text**: UI strings, logo and per-language URLs live in `collections/_languages/` (`el.md`, `en.md`). These define the languages themselves, so they are one file per language rather than per item.
- **Ranks**: academic rank labels (by language and `gender: m|f`) come from `_data/ranks.yml`; each person file stores only the canonical Greek `rank`.
- **Supervisors** (`theses`, `msc_theses`): `supervisors:` is a list of people ids — the file name in `_people/` without `.md` (e.g. `bournetas-apostolos`) — which become links to the person in the current language and take the Επιβλέπων/Επιβλέπουσα form from the person's `gender`. Someone not in `_people/` is written as a plain name; then set `supervisor_gender: f` on the thesis if needed.
- **Academic year** (`_data/academic_years/<year>.yml`, one file per year): key dates, first-year timetable, and per semester the teaching/exam periods, weekly timetable and teaching assignments. The undergraduate hub shows the year `academic_year` and semester `current_semester` set in `_config.yml`; switch `current_semester` to `spring` in February and add the next year's file in September. Courses taught in a semester are marked with `offered:` in `collections/_courses/`.
- **News**: most announcements exist only in Greek. English news listings show both languages and mark Greek titles with `lang="el"`.

## Content model: everything listable is a collection

Every item lives in its own file under `collections/`. Edit or add a file there; listings, menus and the search index update on the next build.

| Collection | Folder | One file per… | Key front matter |
|---|---|---|---|
| `people` | `_people/` | staff member | `title`, `group` (dep/edip/etep/admin/teaching/retired), `rank` (key into `_data/ranks.yml`), `gender` (`f` for feminine rank titles), `sector`, `office`, `phone`, `email`, `website`, `interests`, `duties`, `sort_name` |
| `staff_groups` | `_staff_groups/` | staff category (generates its listing page) | `key`, `title`, `nav_order`, `ranks`, `rank_titles` |
| `sectors` | `_sectors/` | Τομέας | `key`, `title`, `order`, `lede` |
| `news` | `_news/` | announcement (`YYYY-MM-DD-slug.md`) | `title`, `date`, `categories`, `summary`, `attachments` |
| `news_categories` | `_news_categories/` | news category (generates its listing page) | `key`, `title`, `nav_order` |
| `events` | `_events/` | conference / talk / event | `title`, `date`, `dates_text`, `type`, `seminar`, `speaker`, `location`, `website` |
| `seminars` | `_seminars/` | seminar series | `key`, `title`, `order`, `sector`, `website`, `organizers` |
| `programs` | `_programs/` | study programme | `key`, `title`, `nav_order`, `parent_program` |
| `theses` | `_theses/` | PhD thesis (completed or in progress) | `author`, `title`, `year`, `status`, `supervisors`, `supervisor_gender`, `sector`, `link` |
| `msc_theses` | `_msc_theses/` | master's thesis (listed per programme on `/spoudes/metaptychiakes/diplomatikes/<program>/`) | `program` (theoritika/efarmosmena/statistiki), `number`, `year`, `date`, `supervisors`, `supervisor_gender`, `link`, `el.author`, `el.title` |
| `chairs` | `_chairs/` | term of a Chair / Vice-chair | `term_start`, `term_end`, `chair`, `vice_chairs`, `notes` |
| `forms` | `_forms/` | form/application | `title`, `audience`, `order`, `files` |
| `links` | `_links/` | external link | `title`, `url_external`, `placement` (utility/home/footer/useful), `order` |
| `awards` | `_awards/` | award page | `title`, `order` |
| `labs` | `_labs/` | lab | `title`, `summary` |
| `languages` | `_languages/` | site language | `key`, `home`, `search_url`, `logo`, `t` (UI strings) |

Collection items link to each other by key: `person.sector` → `sector.key`, `event.seminar` → `seminar.key`, `news.categories[]` → `news_category.key`.

Free-standing pages live in `pages/`. The main menu is built from front matter, not from a data file:

- `section_root: true` + `nav_order` → top-level menu entry
- `section: <key>` + `nav_order` → dropdown/sidebar entry in that section
- no `nav_order` → page exists but is not listed in menus

Section keys: `to-tmima`, `spoudes`, `ereuna`, `anthropoi`, `nea`, `epikoinonia`. Menus show only items in the page's language.

Listing pages are thin wrappers around shared includes in `_includes/listings/`, so the Greek and English versions of a listing cannot drift apart.

## Brand and style

The visual style follows **www.uoa.gr** (e.g. the School of Science page): dark top bar, white header with the logo and a blue **MENU** button that opens a full menu panel, a page banner, small uppercase breadcrumbs, uppercase GFS Didot Bold titles with the emblem, a right-hand sidebar of uppercase links, and a dark footer. Values come from uoa.gr's stylesheet: blue `#0075CB`, `#1C1C1C`, greys `#F4F4F4`/`#E5E5E5`. Tokens are in `_sass/_tokens.scss`.

- **Logo**: the official vector artwork from the UoA identity guide (share.uoa.gr/public/Documents/new-logo). It is the blue Pantone 279 version (`LOGO_UOA COL2`), as used on uoa.gr, cropped losslessly into `assets/brand/` in Greek, English, emblem-only and white versions. Do not redraw or recolour it.
- **Fonts** (all OFL, self-hosted, no requests to Google): GFS Didot Bold for titles (from the Greek Font Society, licence in `assets/fonts/OFL-GFS-Didot.txt`), Open Sans for body text, Roboto for labels. The identity typeface *Katsoulidis* is commercial (Cannibal Fonts EULA forbids web distribution), so it is used only if installed on the visitor's machine.
- **Banner**: `assets/img/banner.jpg` is the photo of the Mathematics building from the current department site. Set `banner:` in a page's front matter to override it.

## Migration

The importer lives in `_migration/tools/`. Jekyll excludes that folder.

```sh
# Greek site
python3 -I _migration/tools/crawl.py _migration/crawl 6
python3 -I _migration/tools/import_site.py _migration/crawl .
# English site (run after the Greek import: it matches people/theses against the Greek files)
CRAWL_BASE=https://en.math.uoa.gr CRAWL_NEWS_LIST=/news_and_events/news \
CRAWL_NEWS_MARK=/view_announcement/,/view_event/ python3 -I _migration/tools/crawl.py _migration/crawl_en 3
python3 -I _migration/tools/import_en.py _migration/crawl_en .
```

`_migration/tools/merge_bilingual.py` is the one-off script that merged the earlier separate English files into the single-file format.

English staff entries are matched to Greek ones by e-mail and otherwise by transliterated name. Unmatched entries are listed in `_migration/import-report-en.txt`. Most of them are people the English site still lists but the Greek site no longer does.

Imported files carry `generated: true`. **The importers are safe by default**: they only create missing files and never modify existing ones. Pass `--overwrite` to regenerate files marked `generated: true`. That discards hand edits in those files, so remove `generated: true` from any file you edit by hand. Problems found during import are listed in `_migration/import-report*.txt`.

Still to do:

- Files under `/fileadmin/...` (PDFs, forms, images) are still linked on the old host (`site.legacy_url`). Mirror them before the old server is retired.
- Only the 6 most recent pages of announcements were imported (95 items). Older ones stay on the old site.
- Text was copied as-is from the old pages. Some news titles are in ALL CAPS and some old texts have hard line breaks. Fix these by hand where it matters.
- The sector descriptions use the department's official English area lists, which I translated back into Greek. The Greek wording needs the department's approval.
- Set `show_legacy_note: false` in `_config.yml` once the migration is reviewed.
- Accessibility statement and privacy/cookie pages need official text from the University.
- English content is as current as en.math.uoa.gr, which is behind the Greek site. Some faculty pages, some English names and the PhD-candidate list need updating by hand.
