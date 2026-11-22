// The one place that names the drawing behind every icon of the interface
// (work order 071, E-51). Lucide is imported here and nowhere else; code uses
// icons only by their IconName through Icon.tsx. Own drawings (work order 074,
// industrial/) are in the same table, as components built on SvgGlyph (glyph.tsx).
//
// Only named imports: the bundler keeps just these icons (tree shaking).
// Lucide's own names follow its current version (1.77.0); older aliases such
// as History or AlertTriangle are avoided.
// IDs in the comments refer to docs/design/icon-bedarfsanalyse.md, part H2.
import {
  Activity,
  Check,
  ChevronLeft,
  ChevronRight,
  CircleCheck,
  CircleDashed,
  CircleMinus,
  CircleUser,
  CircleX,
  Clock,
  Download,
  FileText,
  Funnel,
  FunnelX,
  GitCommitVertical,
  Import,
  Info,
  LayoutGrid,
  ListTree,
  LoaderCircle,
  Lock,
  LogOut,
  Map as MapGlyph,
  MapPin,
  Network,
  Pencil,
  Plus,
  RefreshCw,
  RotateCcwClock,
  Scan,
  ScanText,
  Search,
  Settings,
  TriangleExclamationPoint,
  Upload,
} from "lucide-react";

import type { Glyph } from "./glyph.tsx";
import {
  ComputerGlyph,
  ControllerGlyph,
  DeviceGlyph,
  FirewallGlyph,
  PlantGlyph,
  PlcGlyph,
  RobotGlyph,
  RouterGlyph,
} from "./industrial/glyphs.tsx";

// `satisfies` checks that every entry is a drawing Icon.tsx can render,
// while IconName stays the exact list of keys.
const glyphs = {
  // Navigation (NAV)
  structure: ListTree, // NAV-01
  map: MapGlyph, // NAV-09 (library icon until an own one is drawn)
  ingest: ScanText, // NAV-07, ingest overview (work order 055)
  import: Import, // NAV-02
  audit: RotateCcwClock, // NAV-03
  selftest: Activity, // NAV-04
  settings: Settings, // NAV-15
  user: CircleUser, // OBJ-08

  // Objects and hierarchy (OBJ)
  site: MapPin, // OBJ-01
  area: LayoutGrid, // OBJ-02
  plant: PlantGlyph, // OBJ-03, own drawing
  device: DeviceGlyph, // OBJ-04, own drawing: generic device and fallback of the device classes
  network: Network, // OBJ-11
  document: FileText, // OBJ-05
  version: GitCommitVertical, // OBJ-07

  // Device classes (DEV, E-53), own drawings; chosen by deviceClassIcon()
  // in pages/structure/deviceClass.ts, the class "other" shows `device`.
  devicePlc: PlcGlyph, // DEV-01
  deviceController: ControllerGlyph, // DEV-02
  deviceComputer: ComputerGlyph, // DEV-03
  deviceRouter: RouterGlyph, // DEV-04
  deviceRobot: RobotGlyph, // DEV-05
  deviceFirewall: FirewallGlyph, // DEV-06

  // Actions (ACT)
  create: Plus, // ACT-01
  edit: Pencil, // ACT-02
  upload: Upload, // ACT-03
  download: Download, // ACT-04
  retry: RefreshCw, // ACT-05
  apply: Check, // ACT-09
  filter: Funnel, // ACT-06
  resetFilter: FunnelX, // ACT-06
  search: Search, // NAV-05
  fitView: Scan, // map: fit the view
  previous: ChevronLeft, // ACT-10
  next: ChevronRight, // ACT-10
  signOut: LogOut, // ACT-08

  // Status (STA), always next to a text
  success: CircleCheck, // STA-01
  error: CircleX, // STA-02
  warning: TriangleExclamationPoint, // STA-03
  loading: LoaderCircle, // STA-04
  noPermission: Lock, // STA-05
  info: Info, // STA-07
  queued: Clock, // STA-08, ingest job waiting in the queue
  skipped: CircleMinus, // ingest job skipped (format not ingested); no ID in H2
  notIngested: CircleDashed, // version without any ingest job; no ID in H2
} as const satisfies Record<string, Glyph>;

/** Name of an icon of the interface. */
export type IconName = keyof typeof glyphs;

/** Every icon name, in the order of the table above. */
export const iconNames = Object.keys(glyphs) as readonly IconName[];

/** The drawing behind an icon name. */
export function glyphOf(name: IconName): Glyph {
  return glyphs[name];
}
