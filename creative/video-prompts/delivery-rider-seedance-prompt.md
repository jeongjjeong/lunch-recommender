# Urban Delivery Rider — Seedance-Style Generation Prompt

Formatted per the Seedance prompt skeleton (Style Prefix → Asset Registry → SUBJECT/LOCATION/ACTION → CAMERA → STYLE → CONSTRAINTS). The whole piece is one continuous 12-second take with 12 hard-cut shots inside it (MULTISHOT), not 12 separate clips — reference `delivery-rider-animation.md` for the full prose shot list this was compiled from.

If your tool caps clip length below 12s, split at the `SHOT` boundaries into Shots 1–6 / 7–12 (two ~6s generations) rather than regenerating each shot alone — several beats (the catch, the portal delivery) depend on momentum carried from the previous shot.

---

## Style Prefix (prepend verbatim — do not use a photorealistic default)

```
Style: Bold graphic illustration — angular cel-shaded planes, subtle paper grain,
dramatic foreshortening. NOT photorealistic. NOT a glossy plastic-look 3D render.
NOT a game-engine/game-cutscene aesthetic.
Cinematography: Fast, dynamic action-sports tracking cinematography.
Lighting: Saturated flat graphic lighting — cobalt-blue sky ambient, hard-edged
graphic shadow shapes, no realistic global illumination.
Color: 60:30:10 — dominant cobalt-blue sky / deep-navy buildings & structural
road sides, secondary cream road & surfaces, accent bright-orange windbreaker
and lime-green cap/wheels/pins.
Camera: Rear and rear-three-quarter tracking angles predominate; occasional
low ground-level and high overhead. Physical cine-lens feel, controlled motion
blur on background and passing foreground only.
Motion: Wheel rotation, strong skating pushes, low aerodynamic posture,
carving, acceleration and momentum. No jumps. No aerial spins. No frictionless
drifting.
Physics: Road, boxes, and skate boots/frames are rigid. Only fabric (jacket,
bag strap), loose box flaps/tape ends, and elastic graphic objects (location
pins, delivery portal, chat-bubble UI) deform, and only at the point of
contact or force.
Composition: Rule of thirds, dramatic foreshortening. Character shown from
behind/rear-three-quarter; no unnecessary frontal facial close-ups.
Continuity: Character design, crossbody bag position/orientation, and skate
toe-forward/heel-back orientation identical across every cut. No identity
drift, no duplicated character, no duplicated or missing skate wheels.
Technical: 24fps smooth continuous motion, no jitter, no split-screen between
shots — every cut is a direct hard cut in the same continuous forward motion.
Audio: Environmental SFX only — rolling wheels, wheel-joint vibration, wind
rush, jacket flutter, mechanical road-unfolding sounds, package-catch and
package-placement sounds, elastic rebound effects. No music, no dialogue, no
narration, no singing, no lip-sync, no subtitles.
```

---

## Asset Registry

| Tag | Description |
|---|---|
| `@rider` | The single delivery rider — lime-green cap, bright orange windbreaker, deep navy wide pants, white socks with black stripes, blue-and-white inline skate boots, lime-green wheels, black gloves, cream/black/lime crossbody delivery bag. Strap position and bag orientation fixed across every shot. Matches input reference 100%. |
| `@skates` | `@rider`'s inline skates — single straight row of wheels per boot, boot+frame as one rigid structure, foot never rotates independently below the ankle. |
| `@bag` | The crossbody delivery bag on `@rider`; reacts to inertia (lag on acceleration, outward swing on curves) but strap position/orientation never changes. |
| `@giant-package` | Building-sized parcel — cream cardboard, black tape seams, lime shipping label — travels along its own cyan logistics route, suspended above the road. |
| `@small-package` | A smaller delivery box that travels beside `@rider` at a slightly slower speed before being caught. |
| `@portal` | Giant lime-green location-pin-shaped delivery portal moving along the roadside, with a small cream receiving platform inside its circular opening; elastic rim. |
| `@pin` | Lime-green location-pin graphic object beside the road; elastic, compresses/rebounds only on contact. |
| `@road` | Cream road surface with deep navy structural sides, including foldable panels that unfold and lock at hinge points ahead of `@rider`. |
| `@city` | Deep navy buildings, saturated cobalt-blue sky, cyan logistics route lines, three-dot chat-bubble graphics as background/midground elements. |

---

## Prompt

```
[STYLE PREFIX — paste verbatim from above]

SUBJECT — @rider (matches input 100%), skating at full speed on @skates with
@bag worn crossbody, never stopping. Goal: activate a route, pass beneath
@giant-package, catch @small-package mid-skate, deliver it into @portal
without breaking stride, then push into open sky. Emotional beat: focused,
propulsive momentum, no hesitation. WB 6500K. MULTISHOT — 12 hard-cut shots
inside one continuous 12-second forward run.

LOCATION — @road and @city are STYLE REFERENCE ONLY, not a fixed keyframe.
Route: narrow delivery alley → unfolding elevated roadway → low tunnel beneath
@giant-package → building-side delivery section → broad open boulevard under
the cobalt sky. The model may freely extend @city; @rider is never pinned to
the input frame, and the road must always be fully connected/locked before
@rider reaches it — never remove it beneath him.

ACTION — @rider skates continuously forward for 12 seconds, activating the
world around him without ever stopping or reversing.

SHOT 1 (0:00–0:01) — Extreme low rear three-quarter close-up on @skates.
Lime-green wheels roll rapidly across the cream @road; heel, rear wheels and
outside boot edge dominate frame, toe pointing into the frame toward travel
direction. Wheels cross a seam, compress slightly, recover. Hard cut.

SHOT 2 (0:01–0:02) — Camera pulls back to full-body rear view. Right skate is
the rolling support leg; left skate pushes strongly back and out, then lifts
and returns beside the right. @rider lowers his torso; @bag lags backward
from inertia; sleeves inflate briefly in the airflow then settle. Hard cut.

SHOT 3 (0:02–0:03) — Rear-right waist-height tracking shot. Without stopping,
@rider presses @pin floating beside the road with his right hand; @pin tilts
in the travel direction, compresses at the contact point, springs back. A
cyan route line shoots forward from @pin. Both knees stay bent, both skates
keep rolling — the reach never rotates hips or skates. Hard cut.

SHOT 4 (0:03–0:04) — High rear overhead angle. Following the cyan route line,
folded @road segments open one after another, each rigid panel rotating on a
visible hinge and locking into place with a small vibration, forming a
descending curve between buildings. @rider enters only once the road ahead
has fully settled, both skates in a stable parallel glide, body lowered
further for speed. Hard cut.

SHOT 5 (0:04–0:05) — Low side-tracking camera outside a banked curve. @rider
carves through at speed, one skate slightly ahead of the other, no crossed
feet, whole body leaning into the arc — hips, knees, boots and wheels all
following the same line. @bag swings outward from centrifugal inertia,
strap taut. Foreground barriers sweep past fast; distant buildings move
slower for parallax. Hard cut.

SHOT 6 (0:05–0:06) — Rear tracking camera lowers with @rider as @giant-package
moves across the road ahead, a narrow clearance beneath it. @rider bends his
knees deeply and folds his torso forward, both skates aligned and still
rolling, and passes beneath @giant-package at speed — never jumping, knees
never touching the ground. Loose flaps and lime tape ends on @giant-package
flutter after he passes; its shadow briefly darkens the frame like a moving
tunnel ceiling. Hard cut.

SHOT 7 (0:06–0:07) — Rear-side skate close-up near the tunnel exit; right
skate rolls into the light first, then left, both toes still pointing the
same forward direction. Camera rises quickly from wheel height to waist
level, revealing the open @city and cobalt sky. @rider raises his torso
slightly, knees still flexed; @bag and jacket keep moving for a beat after
his body straightens (secondary inertia only — no anatomy stretching).
Hard cut.

SHOT 8 (0:07–0:08) — Rear-right medium tracking shot. @small-package travels
beside @rider, slightly slower. He closes the distance and slides his right
hand underneath it — hand touches first, elbow bends slightly to absorb the
relative motion, and only once speeds match does he pull it to his body
(never teleporting into his hand). His right shoulder dips slightly under
the added weight; left arm balances. Skates hold a short stable parallel
glide throughout. Hard cut.

SHOT 9 (0:08–0:09) — Wide side-tracking shot parallel to a building facade.
@portal moves along the roadside ahead, its cream receiving platform visible
inside the circular opening. @rider approaches holding @small-package
forward at waist level, its orientation and tape direction unchanged; his
torso leans only as much as needed toward @portal while hips and skates stay
aligned with the road. For a moment @rider, @small-package and @portal
travel at nearly the same speed side by side. Hard cut.

SHOT 10 (0:09–0:10) — Close-up on @rider's hand, @small-package and @portal.
He pushes the box onto the receiving platform; the portal's elastic rim
stretches slightly around the box's corners then springs back, and the
platform compresses downward under the weight and rebounds once. Only once
the box is securely supported does he release it — his orange sleeve sweeps
forward out of frame as he keeps skating, never stopping, turning, or
reversing his feet. Hard cut.

SHOT 11 (0:10–0:11) — Camera drops extremely low near @rider's left heel.
Right skate is the support leg rolling forward; left skate pushes strongly
back and out once more, passing very close to the lens and reading
dramatically oversized — mostly heel, rear wheels and outside boot visible,
toe still pointed forward away from the camera. The push visibly accelerates
@rider; @bag and sleeves lag half a beat behind. This is wheel-propelled
acceleration only — never a jump. Hard cut.

SHOT 12 (0:11–0:12) — Camera pulls slightly back into an extreme rear
low-angle hero composition matching the reference image. Left skate heel and
lime wheels dominate lower-left foreground; right skate rolls farther ahead.
@rider's orange jacket and navy pants form the central silhouette against
converging navy skyscrapers; a huge cream circular light sits in the cobalt
sky above him, with floating packages, @pin instances, three-dot chat
bubbles and cyan route lines at different depth layers. In the final 0.4s
the camera matches @rider's speed and holds — wheels still rotating, road
still flowing backward, jacket/bag/tape ends carrying residual motion. Ends
on @rider still genuinely skating forward — never a frozen airborne pose.

CAMERA — SHOT 1: extreme low rear three-quarter macro, matched to wheel
speed. SHOT 2: rear full-body, pulling back at push cadence. SHOT 3: rear-
right waist-height tracking, arm-reach motivated. SHOT 4: high rear overhead,
revealing road unfolding. SHOT 5: low side-tracking, outside the curve.
SHOT 6: rear tracking, lowering with the crouch. SHOT 7: rear-side skate
macro rising to waist height. SHOT 8: rear-right medium tracking, catch-
motivated. SHOT 9: wide side-tracking parallel to facade. SHOT 10: hand-
level close-up. SHOT 11: extreme low camera near the pushing heel. SHOT 12:
extreme rear low-angle pulling back to hero framing, then holding.

STYLE — Dominant cobalt-blue sky & deep-navy buildings/road-sides 60% /
Secondary cream road & surfaces 30% / Accent bright-orange jacket, lime cap,
lime wheels, lime pins/portal, cyan route lines 10%. WB 6500K. Reinforce flat
saturated graphic lighting throughout — no photorealistic global illumination.

CONSTRAINTS — 16:9 (or 9:16 if vertical delivery is required — do not crop
the hero composition in Shot 12). NO slow-motion; speed is built by wheel
rotation, posture, parallax and selective motion blur only. NO jumps, aerial
spins, cross-step cornering, backward skating, or foot-tip spinning. Toe
always leads, heel always trails, in every shot including rear angles — never
reverse the skate so the toe faces camera while moving forward. Left skate
stays on the left leg, right on the right; foot never rotates independently
below the ankle; wheels stay a single straight row (no quad skates, no
sideways spread, no missing/duplicated/extra wheels). @bag strap
position/orientation identical in all 12 shots. Road/boxes/skate boots+frames
stay rigid; only fabric, straps, flaps, tape ends, and elastic graphic
objects (pins/portal/chat bubbles) deform, only at contact. Road is always
fully connected and locked before @rider reaches it — never remove it under
him, never let him skate through empty space. No character duplication. No
readable written sentences on chat-bubble graphics. NO subtitles, NO titles,
NO logos, NO watermarks. NO eye glow. Audio is environmental SFX only — no
music, no dialogue.
```
