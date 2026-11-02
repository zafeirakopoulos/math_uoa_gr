# frozen_string_literal: true

# Weekly timetable grids (hours x rooms, one table per day), as on di.uoa.gr.
# For every academic-year file in _data/academic_years/ and every semester with a
# `timetable.slots` list, builds `<semester>.timetable.grid`:
#   { "views" => { "pps" | "pms" | "full" => [ { "day", "rooms", "rows" => [ { "hour", "cells" } ] } ] } }
# A cell is nil (empty), "skip" (covered by a class that started earlier) or
# { "slot" => <slot>, "span" => <hours> }. pps = undergraduate, pms = graduate, full = everything.
module TimetableGrid
  DAYS = %w(Δευτέρα Τρίτη Τετάρτη Πέμπτη Παρασκευή).freeze
  VIEWS = {
    "pps"  => ->(s) { s["level"].to_s.include?("undergraduate") },
    "pms"  => ->(s) { s["level"].to_s.include?("postgraduate") },
    "full" => ->(_) { true },
  }.freeze

  def self.hour(t) = t.to_s.split(":").first.to_i

  # Amphitheatres first, then rooms in natural order, labs last
  def self.room_key(r)
    group = r.start_with?("ΑΜΦ") ? 0 : r.start_with?("Εργαστ") ? 2 : 1
    [group, r]
  end

  def self.build(slots)
    VIEWS.transform_values do |keep|
      chosen = slots.select(&keep)
      DAYS.filter_map do |day|
        ds = chosen.select { |s| s["day"] == day }
        next if ds.empty?

        rooms = ds.map { |s| s["room"].to_s }.uniq.sort_by { |r| room_key(r) }
        first = ds.map { |s| hour(s["start"]) }.min
        last = ds.map { |s| hour(s["end"]) }.max
        covered = {}
        rows = (first...last).map do |h|
          cells = rooms.map do |room|
            if covered[[room, h]]
              "skip"
            elsif (s = ds.find { |x| x["room"].to_s == room && hour(x["start"]) == h })
              span = hour(s["end"]) - h
              (h + 1...h + span).each { |k| covered[[room, k]] = true }
              { "slot" => s, "span" => span }
            end
          end
          { "hour" => format("%02d:00–%02d:00", h, h + 1), "cells" => cells }
        end
        { "day" => day, "rooms" => rooms, "rows" => rows }
      end
    end
  end

  class Generator < Jekyll::Generator
    safe true
    priority :high

    def generate(site)
      (site.data["academic_years"] || {}).each_value do |year|
        %w(winter spring).each do |sem|
          tt = year.dig(sem, "timetable") or next
          slots = tt["slots"] or next
          tt["grid"] = { "views" => TimetableGrid.build(slots) }
        end
      end
    end
  end
end
