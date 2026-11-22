// The project's own icons for plants and device classes (work order 074),
// drawn on the frame SvgGlyph. The .svg files next to this module are the
// approved drawings, kept byte for byte; each component below repeats the
// shapes of one file, and glyphs.test.tsx checks that both stay the same.
// IDs refer to docs/design/icon-bedarfsanalyse.md, part H2.
import type { ReactElement } from "react";

import { type GlyphProps, SvgGlyph } from "../glyph.tsx";

/** OBJ-03, plant: work pieces on a conveyor (obj-03-anlage.svg). */
export function PlantGlyph(props: GlyphProps): ReactElement {
  return (
    <SvgGlyph {...props}>
      <rect x="3" y="6" width="7" height="6" rx="1.5" />
      <rect x="14" y="6" width="7" height="6" rx="1.5" />
      <rect x="2" y="15" width="20" height="6" rx="3" />
      <path d="M6 18h0" />
      <path d="M18 18h0" />
    </SvgGlyph>
  );
}

/** OBJ-04, generic device: housing with a type plate (obj-04-geraet.svg). */
export function DeviceGlyph(props: GlyphProps): ReactElement {
  return (
    <SvgGlyph {...props}>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M7 15h5" />
    </SvgGlyph>
  );
}

/** DEV-01, PLC: compact CPU with terminal strips at top and bottom (dev-01-sps.svg). */
export function PlcGlyph(props: GlyphProps): ReactElement {
  return (
    <SvgGlyph {...props}>
      <rect x="2" y="3" width="20" height="18" rx="1.5" />
      <path d="M2 8h20M2 16h20" />
      <path d="M11 12h7" />
      <path d="M6 12h0" />
      <path d="M6 5.5h0" />
      <path d="M10 5.5h0" />
      <path d="M14 5.5h0" />
      <path d="M18 5.5h0" />
      <path d="M6 18.5h0" />
      <path d="M10 18.5h0" />
      <path d="M14 18.5h0" />
      <path d="M18 18.5h0" />
    </SvgGlyph>
  );
}

/** DEV-02, controller / embedded: housing with display and a row of sockets (dev-02-controller.svg). */
export function ControllerGlyph(props: GlyphProps): ReactElement {
  return (
    <SvgGlyph {...props}>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <rect x="7" y="6" width="10" height="7" rx="1" />
      <path d="M7 17h0" />
      <path d="M10 17h0" />
      <path d="M14 17h0" />
      <path d="M17 17h0" />
    </SvgGlyph>
  );
}

/** DEV-03, computer / edge: single-board computer with pin header and sockets (dev-03-rechner.svg). */
export function ComputerGlyph(props: GlyphProps): ReactElement {
  return (
    <SvgGlyph {...props}>
      <rect x="2" y="5" width="17" height="15" rx="1.5" />
      <rect x="15" y="10" width="7" height="3.5" rx="0.5" />
      <rect x="15" y="16" width="7" height="2" rx="0.5" />
      <path d="M5 8h0" />
      <path d="M8 8h0" />
      <path d="M11 8h0" />
      <path d="M14 8h0" />
    </SvgGlyph>
  );
}

/** DEV-04, router: the network-diagram symbol, a circle with four arrows (dev-04-router.svg). */
export function RouterGlyph(props: GlyphProps): ReactElement {
  return (
    <SvgGlyph {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M5 12h4.5M7.5 10l2 2-2 2M19 12h-4.5M16.5 10l-2 2 2 2M12 10V5.5M10 7.5l2-2 2 2M12 14v4.5M10 16.5l2 2 2-2" />
    </SvgGlyph>
  );
}

/** DEV-05, industrial robot: six-axis arm with base, joints and tool flange (dev-05-roboter.svg). */
export function RobotGlyph(props: GlyphProps): ReactElement {
  return (
    <SvgGlyph {...props}>
      <rect x="5" y="18" width="8" height="3" rx="1" />
      <path d="M9 18v-3" />
      <circle cx="9" cy="13" r="2" />
      <path d="m10.6 11.8 4.8-3.6" />
      <circle cx="17" cy="7" r="2" />
      <path d="M17 9v5M15 15h4" />
    </SvgGlyph>
  );
}

/** DEV-06, firewall: the network-diagram symbol, a brick wall in three rows (dev-06-firewall.svg). */
export function FirewallGlyph(props: GlyphProps): ReactElement {
  return (
    <SvgGlyph {...props}>
      <rect x="3" y="4" width="18" height="16" rx="1.5" />
      <path d="M3 9h18M3 15h18M12 4v5M8 9v6M16 9v6M12 15v5" />
    </SvgGlyph>
  );
}
