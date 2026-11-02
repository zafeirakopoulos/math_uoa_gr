# frozen_string_literal: true

# Bilingual content: one file per item, with shared fields at the top level and
# per-language blocks:
#
#   ---
#   key: analysi            # shared
#   order: 2                # shared
#   el:
#     title: Τομέας Μαθηματικής Ανάλυσης
#     lede: …
#     body: |               # optional Markdown body for this language
#       …
#   en:
#     title: Sector of Mathematical Analysis
#     permalink: /en/…/     # optional; otherwise the collection's `permalink_en`
#   ---
#
# For every collection document and page that has language blocks this generator
#   * turns the file itself into the page of its primary language (Greek if present),
#   * creates one extra page per other language (e.g. the English version),
#   * merges the language block into the top-level data of each version,
#   * sets `lang`, `langs` and `urls` ({ "el" => …, "en" => … }) on every version.
# A collection with `always_en: true` (in _config.yml) gets English pages for every item,
# using the Greek fields where no en: block exists (e.g. people, events).
#
# Every version also gets `i18n`: { "el" => {...}, "en" => {...} } — the full localised
# view of the item per language (shared fields + that language's block, falling back to
# the primary language, plus its `url`). Listings iterate the collection documents
# (one per item) and read `item.i18n[lang].title`, `item.i18n[lang].url`, …
module Bilingual
  LANGS = %w(el en).freeze
  NOT_IN_VIEW = (LANGS + %w(body excerpt i18n urls)).freeze

  class Variant < Jekyll::PageWithoutAFile
    def initialize(site, data, content)
      super(site, site.source, "", "index.html")
      @data = data
      self.content = content
    end
  end

  class Generator < Jekyll::Generator
    safe true
    priority :highest

    def generate(site)
      @site = site
      @default = site.config.dig("bilingual", "default") || "el"
      extra = []
      site.collections.each_value do |coll|
        next if coll.label == "languages"

        coll.docs.each { |doc| extra.concat(process_doc(coll, doc)) }
      end
      site.pages.dup.each { |page| extra.concat(process_page(page)) }
      site.pages.concat(extra)
      build_nav(site)
    end

    private

    NAV_COLLECTIONS = %w(staff_groups news_categories programs).freeze
    NAV_FIELDS = %w(title nav_title section section_root nav_order nav_key key).freeze

    # Menu entries per language, computed once: site.nav.el / site.nav.en
    # (pages and listing documents that have `nav_order` or `section_root`).
    def build_nav(site)
      items = site.pages + NAV_COLLECTIONS.flat_map { |c| site.collections[c]&.docs || [] }
      site.config["nav"] = LANGS.to_h do |lang|
        entries = items.filter_map do |it|
          d = it.data
          next unless (d["lang"] || @default) == lang && (d["nav_order"] || d["section_root"])

          d.slice(*NAV_FIELDS).merge("url" => it.url)
        end
        [lang, entries]
      end
    end

    def langs_of(data)
      LANGS.select { |l| data[l].is_a?(Hash) }
    end

    def body_for(data, lang, file_body, primary)
      data.dig(lang, "body") || (file_body.to_s.strip.empty? ? nil : file_body) || data.dig(primary, "body") || ""
    end

    def localised(original, langs, primary, urls)
      LANGS.each_with_object({}) do |l, h|
        src = langs.include?(l) ? l : primary
        view = original.reject { |k, _| NOT_IN_VIEW.include?(k) }
        view = view.merge(original[primary].reject { |k, _| k == "body" }) if src != primary
        view = view.merge(original[src].reject { |k, _| k == "body" })
        h[l] = view.merge("lang" => src, "url" => urls[src] || urls[primary])
      end
    end

    def merged(data, lang, langs)
      block = data[lang].reject { |k, _| k == "body" }
      data.reject { |k, _| k == "excerpt" }.merge(block).merge("lang" => lang, "langs" => langs)
    end

    # --- collection documents -------------------------------------------------
    def process_doc(coll, doc)
      langs = langs_of(doc.data)
      return [] if langs.empty?

      # collections with `always_en: true` get an English page even without an en: block
      if coll.metadata["always_en"] && !langs.include?("en")
        doc.data["en"] = {}
        langs = langs_of(doc.data)
      end

      primary = langs.include?(@default) ? @default : langs.first
      file_body = doc.content
      original = doc.data.dup
      urls = {}
      variants = []

      (langs - [primary]).each do |lang|
        url = doc_url(coll, doc, lang)
        next unless url && coll.write?

        urls[lang] = url
        data = merged(original, lang, langs).merge("permalink" => url, "collection" => coll.label,
                                                   "slug" => doc.data["slug"], "variant_of" => doc.relative_path)
        data["date"] ||= doc.date if doc.respond_to?(:date)
        variants << Variant.new(@site, data, body_for(original, lang, file_body, primary))
      end

      doc.data.merge!(merged(original, primary, langs))
      own = original.dig(primary, "permalink") || (primary == @default ? nil : doc_url(coll, doc, primary))
      doc.data["permalink"] = own if own
      doc.content = body_for(original, primary, file_body, primary)
      doc.instance_variable_set(:@url, nil)
      doc.data["excerpt"] = Jekyll::Excerpt.new(doc) if doc.data.key?("excerpt")
      urls[primary] = doc.url if coll.write?

      i18n = localised(original, langs, primary, urls)
      ([doc] + variants).each { |d| d.data["urls"] = urls; d.data["i18n"] = i18n }
      variants
    end

    def doc_url(coll, doc, lang)
      explicit = doc.data.dig(lang, "permalink")
      return explicit if explicit
      return doc.url if lang == @default

      template = coll.metadata["permalink_#{lang}"]
      return nil unless template

      Jekyll::URL.new(:template => template, :placeholders => doc.url_placeholders, :permalink => nil).to_s
    end

    # --- pages ------------------------------------------------------------------
    def process_page(page)
      langs = langs_of(page.data)
      return [] if langs.empty?

      primary = langs.include?(@default) ? @default : langs.first
      defaults = @site.frontmatter_defaults.all(page.relative_path, :pages)
      original = Jekyll::Utils.deep_merge_hashes(defaults, page.data)
      file_body = page.content
      urls = {}
      variants = []

      (langs - [primary]).each do |lang|
        url = original.dig(lang, "permalink")
        unless url
          Jekyll.logger.warn "Bilingual:", "#{page.relative_path}: no #{lang}.permalink, #{lang} version skipped"
          next
        end
        urls[lang] = url
        data = merged(original, lang, langs).merge("permalink" => url, "variant_of" => page.relative_path)
        variants << Variant.new(@site, data, body_for(original, lang, file_body, primary))
      end

      page.data.merge!(merged(original, primary, langs))
      page.data["permalink"] = original.dig(primary, "permalink") if original.dig(primary, "permalink")
      page.content = body_for(original, primary, file_body, primary)
      page.instance_variable_set(:@url, nil)
      urls[primary] = page.url

      i18n = localised(original, langs, primary, urls)
      ([page] + variants).each { |d| d.data["urls"] = urls; d.data["i18n"] = i18n }
      variants
    end
  end
end
