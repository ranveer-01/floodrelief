# Photography credits

Three photographs carry the visual weight of this site. All three are real
disaster-response photography from Wikimedia Commons — chosen over stock or
illustration because the project is about actual flood relief, and because
their licences are unambiguous enough to sit in a coursework repository.

Each is loaded from `static/css/base.css` via a custom property
(`--img-hero`, `--img-lifecycle`, `--img-closing`) and sits under a duotone
gradient scrim. Every gradient has a colour fallback beneath it, so the pages
still read deliberately if an image fails to load.

---

## `hero-flood.jpg` — landing hero

Residents being evacuated by boat in Dutchtown, Missouri, 20 March 2008.
Many stayed because their houses remained underwater.

- **Photographer:** Jocelyn Augustino / FEMA
- **Licence:** Public domain (work of a US federal government employee)
- **Source:** <https://commons.wikimedia.org/wiki/File:FEMA_-_34479_-_Residents_being_evacuated_in_a_small_boat_in_Missouri.jpg>

## `lifecycle-band.jpg` — lifecycle section band

Aerial view of flooding at Downton, Wiltshire, United Kingdom.

- **Photographer:** Sergeant Mitch Moore, UK Ministry of Defence
- **Licence:** Open Government Licence v1.0 —
  <http://nationalarchives.gov.uk/doc/open-government-licence/version/1/>
- **Required notice:** Contains public sector information licensed under the
  Open Government Licence v1.0.
- **Source:** <https://commons.wikimedia.org/wiki/File:Downton,_Wiltshire_MOD_45158455.jpg>

## `closing-relief.jpg` — closing call-to-action band

Relief supplies being distributed among flood- and river-erosion-affected
people in Rowmari, Kurigram district, Bangladesh, 3 August 2016.

- **Photographer:** Press Information Department, Government of Bangladesh
- **Licence:** Public domain
- **Source:** <https://commons.wikimedia.org/wiki/File:Relief_distribution_Rowmari_Kurigram_Bangladesh_2016-08-03.jpg>

---

## Processing applied

Nothing was added to or removed from any frame. The originals were 1.2–7.2 MB;
serving those on a hero would be indefensible, so each was resized and
recompressed, and two were desaturated so the CSS scrim — not a hot pink
tarpaulin — decides the page's colour.

| File | Delivered | Original | Treatment |
| --- | --- | --- | --- |
| `hero-flood.jpg` | 1900×1121, 363 KB | 3648×2152 | resize, q76 progressive, EXIF stripped |
| `lifecycle-band.jpg` | 1800×1206, 356 KB | 3000×2010 | resize, saturation ×0.62, q74–76 |
| `closing-relief.jpg` | 1800×1193, 279 KB | 3216×2131 | resize, saturation ×0.40, q76 |

## Replacing an image

Drop a new file in at the same name and the site picks it up — no template or
stylesheet edit needed. Keep the crop in mind: text sits over the **left** of
the hero and closing bands, so put your subject right of centre, or adjust
`background-position` in `static/css/landing.css`. Record the new licence here.

`static/images/favicon.svg` is original to this project, not sourced.
