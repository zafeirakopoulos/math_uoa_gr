# frozen_string_literal: true

# site.data["course_by_code"]: undergraduate course documents by code (as a string), for quick links.
# Per-specialisation course lists for the graduate hub: site.data["msc_lists"][spec][group] is the
# list of msc_courses documents of that specialisation and group (core/elective), in catalogue order.
# A shared course has its own code, group and position per specialisation (codes/groups/orders maps).
module MscLists
  class Generator < Jekyll::Generator
    safe true
    priority :low

    def generate(site)
      courses = site.collections["courses"]
      site.data["course_by_code"] = courses.docs.to_h { |d| [d.data["code"].to_s, d] } if courses
      coll = site.collections["msc_courses"] or return
      lists = Hash.new { |h, k| h[k] = Hash.new { |g, j| g[j] = [] } }
      coll.docs.each do |doc|
        Array(doc.data["programs"]).each do |spec|
          group = doc.data.dig("groups", spec) || doc.data["group"]
          order = doc.data.dig("orders", spec) || doc.data["order"] || 999
          lists[spec][group] << [order, doc]
        end
      end
      site.data["msc_lists"] = lists.transform_values { |g| g.transform_values { |a| a.sort_by(&:first).map(&:last) } }
    end
  end
end
