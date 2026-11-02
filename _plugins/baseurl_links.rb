# frozen_string_literal: true

# Content links are written root-relative (`/spoudes/...`). When the site is served
# under a sub-path (`baseurl`), prefix it to every root-relative href/src/action in
# the rendered HTML, so content files never need to know where the site lives.
module BaseurlLinks
  ATTR = %r{\b(href|src|action|srcset)=(["'])/(?!/)}.freeze

  def self.rewrite(item)
    base = item.site.config["baseurl"].to_s.chomp("/")
    return if base.empty? || item.output.nil?
    return unless item.output_ext == ".html"

    item.output = item.output.gsub(ATTR) do
      attr, quote = Regexp.last_match(1), Regexp.last_match(2)
      rest = Regexp.last_match.post_match
      rest.start_with?(base[1..] + "/") || rest.start_with?(base[1..] + quote) ? Regexp.last_match(0) : "#{attr}=#{quote}#{base}/"
    end
  end
end

Jekyll::Hooks.register [:pages, :documents], :post_render do |item|
  BaseurlLinks.rewrite(item)
end
